from html import escape

from graphviz import Digraph

if __package__:
    from .models.ER import Attribute
else:
    from models.ER import Attribute

def draw_erd(schema, output_file="er_diagram"):
    dot = Digraph(format="png")
    dot.attr(
        rankdir="TB",
        splines="true",
        overlap="false",
        nodesep="0.6",
        ranksep="0.8",
        compound="true",
    )
    dot.attr("graph", bgcolor="white", fontname="Arial")
    dot.attr("node", fontname="Arial", fontsize="10")
    dot.attr("edge", fontname="Arial", fontsize="9", arrowhead="none")

    used_ids = {entity.name for entity in schema.entities}
    used_ids.update(rel.name for rel in schema.relationships)
    attribute_number = 0

    def draw_attribute(graph, parent_id, attr, is_partial_key=False):
        nonlocal attribute_number
        if isinstance(attr, str):
            attr = Attribute(name=attr)

        while True:
            attr_id = f"__attribute_{attribute_number}"
            attribute_number += 1
            if attr_id not in used_ids:
                used_ids.add(attr_id)
                break

        if is_partial_key:
            label = (
                '<<TABLE BORDER="0" CELLBORDER="0" '
                'CELLSPACING="0" CELLPADDING="0">'
                '<TR><TD BORDER="1" SIDES="B" STYLE="DASHED">'
                f'{escape(attr.name)}</TD></TR></TABLE>>'
            )
        elif attr.isPrimaryKey:
            label = f"<<u>{escape(attr.name)}</u>>"
        else:
            label = attr.name

        graph.node(
            attr_id,
            label=label,
            shape="ellipse",
            style="filled,dashed" if attr.isDerived else "filled",
            fillcolor="white",
            peripheries="2" if attr.isMultiValued else "1",
        )
        graph.edge(parent_id, attr_id, color="black", arrowhead="none")

        for component in attr.composite or []:
            draw_attribute(graph, attr_id, component)


    for entity in schema.entities:
        entity_peripheries = "2" if entity.isWeak else "1"

        with dot.subgraph(name=f"cluster_{entity.name}") as cluster:
            cluster.attr(color="transparent", bgcolor="transparent")

            cluster.node(
                entity.name,
                label=entity.name,
                shape="box",
                style="filled",
                fillcolor="lightblue",
                peripheries=entity_peripheries,
            )

            for attr in entity.attributes:
                draw_attribute(
                    cluster,
                    entity.name,
                    attr,
                    is_partial_key=bool(entity.isWeak and attr.name in (entity.partialKey or [])),
                )

    dot.attr("node", shape="diamond", fillcolor="lightyellow")
    for rel in schema.relationships:
        rel_peripheries = "2" if rel.isIdentifying else "1"
        dot.node(
            rel.name,
            label=rel.name,
            shape="diamond",
            style="filled",
            fillcolor="lightyellow",
            peripheries=rel_peripheries,
        )

        for attr in rel.attributes:
            draw_attribute(dot, rel.name, attr)

        for participant in rel.participantEntities:
            edge_color = "black:invis:black" if participant.participation == "total" else "black"

            dot.edge(
                participant.entityName,
                rel.name,
                label=participant.cardinality,
                color=edge_color,
                arrowhead="none",
            )

    try:
        dot.render(output_file, cleanup=True)
        print(f"ER Diagram saved as {output_file}.png")
    except Exception as exc:
        print(f"[Graphviz Render Note] Could not render file locally: {exc}")

    return dot
