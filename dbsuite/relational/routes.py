import json
from dataclasses import asdict

from flask import jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

if __package__:
    from .relational_mapper.models.ER import ERSchema
    from .relational_mapper.relational_drawer import draw_relational
    from .relational_mapper.relational_mapper import map_to_relational
    from .query_executor import execute_query
else:
    from relational_mapper.models.ER import ERSchema
    from relational_mapper.relational_drawer import draw_relational
    from relational_mapper.relational_mapper import map_to_relational
    from query_executor import execute_query

def read_payload():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    return data


def read_json_field(data, name):
    raw = data.get(name)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Please provide {name} as JSON text.")
    return json.loads(raw)


def api_convert():
    try:
        data = read_payload()
        raw = read_json_field(data, "json")
        schema = ERSchema.model_validate(raw)
        relational = map_to_relational(schema)
        dot = draw_relational(relational)
        return jsonify({"dot": dot.source, "schema": relational.model_dump()})
    except NotImplementedError as exc:
        return jsonify({"error": str(exc)}), 501
    except (ValueError, ValidationError, BadRequest) as exc:
        return jsonify({"error": str(exc)}), 400


def api_query():
    try:
        data = read_payload()
        datasets = read_json_field(data, "datasets")
        if not isinstance(datasets, dict) or any(
            not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            for rows in datasets.values()
        ):
            raise ValueError("Datasets must map table names to lists of row objects.")
        expression = data.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("Please provide a query expression.")
        return jsonify(asdict(execute_query(expression, datasets)))
    except NotImplementedError as exc:
        return jsonify({"error": str(exc)}), 501
    except (ValueError, KeyError, SyntaxError, TypeError, BadRequest) as exc:
        return jsonify({"error": str(exc)}), 400
