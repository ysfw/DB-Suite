# ERD Generator

The ERD Generator creates a structured entity relationship schema from a written database description. You can also paste ER schema JSON directly, edit it, and render its diagram without using AI.

For installation and startup instructions, see the [main README](../README.md).

## Generate or render a diagram

1. Open **ERD Generator** in DB Suite.
2. Enter a database description and select **Generate ERD**, or paste schema JSON into the editor.
3. Review or edit the JSON, then select **Render diagram**.
4. Choose a layout in the preview and use the zoom controls to inspect the diagram.

AI generation requires `GEMINI_API_KEY` in `.env`. Editing schema JSON and rendering it do not require an API key.

## Supported schema elements

Schemas contain entities, attributes, relationships, and relationship participants. Attributes can be primary keys, partial keys, derived, multivalued, or composite. Composite attributes can contain nested components. The generator follows standard ER notation and does not model inheritance or specialization.

| Element | Diagram notation |
| --- | --- |
| Strong entity | Rectangle |
| Weak entity | Double rectangle |
| Attribute | Ellipse |
| Primary key | Solid underline |
| Partial key on a weak entity | Dashed underline |
| Multivalued attribute | Double ellipse |
| Derived attribute | Dashed ellipse |
| Composite attribute | Connected component ellipses |
| Relationship attribute | Attribute connected to a relationship diamond |
| Relationship | Diamond |
| Identifying relationship | Double diamond |
| Partial participation | Single line |
| Total participation | Double line |
| Cardinality | Labels such as `1`, `N`, or `M` |

## Rendering requirements

The browser preview uses Viz.js from a CDN, so it needs internet access. The Python Graphviz package builds diagram source. Saving a local PNG also requires the Graphviz `dot` executable. Graphviz writes local output files in the working directory; the extensionless source file is ignored by Git.
