from .models.ER import Attribute, Entity, ERSchema, Relationship
from .models.relational import ForeignKey, RelationalSchema, Table

def map_to_relational(schema: ERSchema) -> RelationalSchema:
    """Map an ER schema to a relational schema."""
    result = RelationalSchema()
    tables = _map_entities(schema, result)
    entities = {entity.name: entity for entity in schema.entities}

    # sorting by identifying relations so that weak entities
    # get their keys before ordinary relationships reference them
    # because a weak entity’s full primary key is built when its identifying relationship is processed.
    for relationship in sorted(schema.relationships, key=lambda rel: not rel.isIdentifying):
        if relationship.isIdentifying:
            extra_tables = _map_identifying_relationship(relationship, entities, tables)

        else:
            extra_tables = _map_regular_relationship(relationship, tables)

        result.tables.extend(extra_tables)

    return result

def _map_entities(schema: ERSchema, result: RelationalSchema) -> dict[str, Table]:
    """Add entity tables and their extra attribute tables to result.
    Return a dictionary mapping entity names to their tables.
    """
    tables = {}

    for entity in schema.entities:
        entity_table = Table(name=entity.name, attributes=[])

        if not entity.isWeak:
            # Build the complete primary key before multivalued tables reference it.
            for attribute in entity.attributes:

                if attribute.isPrimaryKey:
                    result.tables.extend(_map_attribute(attribute, entity_table))

            for attribute in entity.attributes:
                if not attribute.isPrimaryKey:
                    result.tables.extend(_map_attribute(attribute, entity_table))

        tables[entity.name] = entity_table
        result.tables.append(entity_table)

    return tables

def _map_identifying_relationship(relationship: Relationship, entities: dict[str, Entity],
                                  tables: dict[str, Table]) -> list[Table]:
    """Complete the weak entity's table and key using its owner.
    Return extra tables created by multivalued entity or relationship attributes.
    """
    weak_participant = next(
        participant for participant in relationship.participantEntities
        if entities[participant.entityName].isWeak
    )
    owner_participant = next(
        participant for participant in relationship.participantEntities
        if not entities[participant.entityName].isWeak
    )

    weak_entity = entities[weak_participant.entityName]
    weak_table = tables[weak_participant.entityName]

    owner_table = tables[owner_participant.entityName]

    foreign_key = copy_key(owner_table, owner_table.name)
    weak_table.foreign_keys.append(foreign_key)

    # flatten the partial key before mapping any multivalued attributes.
    partial_names = set(weak_entity.partialKey or [])

    # this is just a temporary table to map these partial keys
    partial_table = Table(name=weak_table.name, attributes=[])

    for attribute in weak_entity.attributes:
        if attribute.name in partial_names:
            extra_tables = _map_attribute(attribute, partial_table, inherited_key=True)
            if extra_tables:
                raise ValueError("A weak entity's partial key can't be multivalued.")

    weak_table.attributes = foreign_key.columns + partial_table.attributes
    weak_table.primary_key = foreign_key.columns + partial_table.primary_key

    extra_tables = []

    for attribute in weak_entity.attributes:
        if attribute.name not in partial_names:
            extra_tables.extend(_map_attribute(attribute, weak_table))

    for attribute in relationship.attributes:
        extra_tables.extend(_map_attribute(attribute, weak_table, relationship.name + "_"))

    return extra_tables

def _map_regular_relationship(relationship: Relationship, tables: dict[str, Table]) -> list[Table]:
    """Map a non-identifying relationship, delegating M:N and n-ary cases.
    Return any tables created while mapping the relationship.
    """
    participants = relationship.participantEntities

    # if it's an n-ary relationship it gets delegated
    if len(participants) != 2:
        return _map_relationship_table(relationship, tables, relationship.name + "_")

    first, second = participants
    first_table = tables[first.entityName]
    second_table = tables[second.entityName]

    if first.cardinality != "1" and second.cardinality != "1":
        # same here with n:m, it gets delegated
        return _map_relationship_table(relationship, tables, "")

    if first.cardinality == "1" and second.cardinality == "1":
        # in 1:1 mapping, prefer the total participation side when only one side is total.
        # if both sides have the same participation, either side can receive the foreign key.
        receive_on_second: bool = (first.participation == "partial")
    else:
        # in 1:N mapping it's a must to put them on the n side
        receive_on_second:bool = (first.cardinality == "1")

    if receive_on_second:
        return _attach_relationship(relationship, second_table, first_table)

    return _attach_relationship(relationship, first_table, second_table)


def _attach_relationship(relationship: Relationship, receiving_table: Table, referenced_table: Table) -> list[Table]:
    """Store a 1:1 or 1:N relationship on the chosen receiving table.
    Return extra tables created by multivalued relationship attributes.
    """
    role = relationship.name + "_" + referenced_table.name
    foreign_key = copy_key(referenced_table, role)

    receiving_table.foreign_keys.append(foreign_key)
    receiving_table.attributes.extend(foreign_key.columns)

    extra_tables = []

    for attribute in relationship.attributes:
        extra_tables.extend(_map_attribute(attribute, receiving_table, relationship.name + "_"))

    return extra_tables


def _map_relationship_table(relationship: Relationship, tables: dict[str, Table], attribute_prefix: str) -> list[Table]:
    """Create a separate table for an M:N or n-ary relationship.
    Return any extra attribute tables, followed by the relationship table.
    """
    relationship_table = Table(name=relationship.name, attributes=[])

    participants = relationship.participantEntities

    for index, participant in enumerate(participants):
        role = participant.entityName

        # if the same entity participates more than once in the relationship
        # use its position in the participant list to distinguish each reference
        # for example Mentors(Employee, Employee),
        # then we need Employee_1_ID and Employee_2_ID
        if sum(item.entityName == role for item in participants) > 1:
            role += f"_{index + 1}"

        foreign_key = copy_key(tables[participant.entityName], role)

        relationship_table.foreign_keys.append(foreign_key)

        relationship_table.primary_key.extend(foreign_key.columns)

    extra_tables = []

    for attribute in relationship.attributes:
        extra_tables.extend(_map_attribute(attribute, relationship_table, attribute_prefix))

    relationship_table.attributes = (relationship_table.primary_key + relationship_table.attributes)

    extra_tables.append(relationship_table)

    return extra_tables


def _map_attribute(attr: Attribute, owner: Table, prefix: str = "", inherited_key: bool = False) -> list[Table]:
    """Add columns to the owner table.
    Return any extra tables created by multivalued attributes.
    """
    # derived attributes can be calculated, so we leave them out :)
    if attr.isDerived:
        return []

    # delegate multivalued attributes
    if attr.isMultiValued:
        return _map_multivalued_attribute(attr, owner, prefix)

    # passes the status of being a primary key to the composite attribute's children
    is_key = inherited_key or bool(attr.isPrimaryKey)

    if attr.composite is not None:
        extra_tables = []

        # goes over all children and recursively map each attribute,
        # while passing a prefix to identify who belongs to which composite attribute
        for component in attribute_components(attr):
            extra_tables.extend(_map_attribute(component, owner, prefix + attr.name + "_", is_key))

        return extra_tables

    # the base case where it's neither multivalued nor composite
    column = prefix + attr.name
    owner.attributes.append(column)

    if is_key:
        owner.primary_key.append(column)

    return []


def _map_multivalued_attribute(attribute: Attribute, owner: Table, prefix: str) -> list[Table]:
    """Create a table for the attribute's values, linked to the owner.
    Return it along with any tables created for nested multivalued attributes.
    """
    foreign_key = ForeignKey(
        columns=owner.primary_key,
        referenced_table=owner.name,
        referenced_columns=owner.primary_key,
    )
    value_table = Table(
        name=owner.name + "_" + prefix + attribute.name,
        attributes=foreign_key.columns,
        foreign_keys=[foreign_key],
    )
    pending: list[tuple[Attribute, str]] = []

    def collect(component: Attribute, path: str) -> None:
        if component.isDerived:
            return
        if component.isMultiValued:
            pending.append((component, path))
        elif component.composite is not None:
            for child in attribute_components(component):
                collect(child, path + component.name + "_")
        else:
            _map_attribute(component, value_table, path)

    if attribute.composite is not None:
        for component in attribute_components(attribute):
            collect(component, prefix + attribute.name + "_")
    else:
        value_table.attributes.append(prefix + attribute.name)

    # A nested multivalued attribute must reference its parent's completed key.
    value_table.primary_key = value_table.attributes.copy()

    extra_tables = [value_table]

    for child, child_prefix in pending:
        extra_tables.extend(_map_attribute(child, value_table, child_prefix))

    return extra_tables


def attribute_components(attribute: Attribute) -> list[Attribute]:
    """Convert string component names to Attribute objects."""
    return [
        item if isinstance(item, Attribute) else Attribute(name=item)
        for item in (attribute.composite or [])
    ]


def copy_key(source: Table, role: str) -> ForeignKey:
    """Build a foreign key from the source table's primary key.
    Prefix the local column names with the role to distinguish references.
    """
    return ForeignKey(
        columns=[f"{role}_{column}" for column in source.primary_key],
        referenced_table=source.name,
        referenced_columns=source.primary_key.copy(),
    )
