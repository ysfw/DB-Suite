from html import escape
from graphviz import Digraph, escape as escape_dot

from .models.relational import RelationalSchema, Table

def draw_relational(schema: RelationalSchema) -> Digraph:
    dot = Digraph(format="svg")
    dot.attr(rankdir="TB", splines="spline", ranksep="2.7", nodesep="0.6")
    dot.attr("node", shape="plain", fontname="Arial", fontsize="11")
    dot.attr("edge", arrowsize="0.6", color="#444444")

    table_ids = {table.name: f"t{i}" for i, table in enumerate(schema.tables)}
    ports = {}

    for table in schema.tables:
        for index, column in enumerate(table.attributes):
            ports[table.name, column] = f"c{index}"

        dot.node(table_ids[table.name], label=f"<{table_label(table)}>", xlabel=escape_dot(table.name))

    for first, second in zip(schema.tables, schema.tables[1:]):
        dot.edge(table_ids[first.name], table_ids[second.name], style="invis", weight="10")

    for table in schema.tables:
        for foreign_key in table.foreign_keys:
            if len(foreign_key.columns) != len(foreign_key.referenced_columns):
                raise ValueError(f"Foreign key in {table.name} has mismatched column counts.")

            for column, target_column in zip(foreign_key.columns, foreign_key.referenced_columns):
                source = (table.name, column)
                target = (foreign_key.referenced_table, target_column)

                if source not in ports or target not in ports:
                    raise ValueError(
                        f"Cannot draw foreign key {table.name}.{column} -> "
                        f"{foreign_key.referenced_table}.{target_column}: column not found."
                    )

                dot.edge(
                    f"{table_ids[table.name]}:{ports[source]}",
                    f"{table_ids[foreign_key.referenced_table]}:{ports[target]}",
                    constraint="false",
                )

    return dot

def table_label(table: Table) -> str:
    foreign_columns = {column for key in table.foreign_keys for column in key.columns}
    cells = []

    for index, column in enumerate(table.attributes):
        label = escape(column)

        if column in table.primary_key:
            label = f"<U>{label}</U>"
        if column in foreign_columns:
            label += " (FK)"
        cells.append(f'<TD PORT="c{index}">{label}</TD>')

    return (
        '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" '
        'CELLPADDING="6" BGCOLOR="#eeeeee"><TR>'
        + "".join(cells or ["<TD> </TD>"])
        + "</TR></TABLE>"
    )
