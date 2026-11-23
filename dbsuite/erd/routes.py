from flask import jsonify, request
if __package__:
    from .erd_drawer import draw_erd
    from .erd_generator import generate_erd
    from .models.ER import ERSchema
else:
    from erd_drawer import draw_erd
    from erd_generator import generate_erd
    from models.ER import ERSchema

def api_generate():
    data = request.get_json() or {}
    description = data.get("description", "").strip()
    if not description:
        return jsonify({"error": "Please provide a database description."}), 400

    try:
        raw_json = generate_erd(description)
        schema = ERSchema.model_validate_json(raw_json)
        dot = draw_erd(schema)
        return jsonify({"json": schema.model_dump_json(indent=2), "dot": dot.source})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def api_render():
    data = request.get_json() or {}
    raw_json = data.get("json", "").strip()
    if not raw_json:
        return jsonify({"error": "Please provide valid ERD JSON."}), 400

    try:
        schema = ERSchema.model_validate_json(raw_json)
        dot = draw_erd(schema)
        return jsonify({"json": schema.model_dump_json(indent=2), "dot": dot.source})
    except Exception as exc:
        return jsonify({"error": f"Invalid ERSchema JSON: {exc}"}), 400
