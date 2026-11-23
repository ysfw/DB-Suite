from dataclasses import dataclass
from typing import Any

from .query_parser import parse_query

Datasets = dict[str, list[dict[str, Any]]]

@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]


def execute_query(expression: str, datasets: Datasets) -> QueryResult:
    tree = parse_query(expression)
    return _evaluate(tree, datasets)


def _evaluate(node: dict, datasets: Datasets) -> QueryResult:
    operation = node["operation"]

    match operation:
        case "table":
            rows = datasets[node["name"]]
            columns = list(rows[0]) if rows else []
            return QueryResult(columns, rows)

        case "select":
            source = _evaluate(node["source"], datasets)
            return _select(source, node["condition"])

        case "project":
            source = _evaluate(node["source"], datasets)
            return _project(source, node["columns"])

        case "rename":
            source = _evaluate(node["source"], datasets)
            return _rename(source, node["old_name"], node["new_name"])

        case "aggregate":
            source = _evaluate(node["source"], datasets)
            return _aggregate(source, node["columns"], node["function"])

        case "join":
            left = _evaluate(node["left"], datasets)
            right = _evaluate(node["right"], datasets)
            return _join(left, right, node["condition"])

        case "union":
            left = _evaluate(node["left"], datasets)
            right = _evaluate(node["right"], datasets)
            return _union(left, right)

        case "intersect":
            left = _evaluate(node["left"], datasets)
            right = _evaluate(node["right"], datasets)
            return _intersect(left, right)

        case "difference":
            left = _evaluate(node["left"], datasets)
            right = _evaluate(node["right"], datasets)
            return _difference(left, right)

        case _:
            raise ValueError(f"Unknown operation: {operation}")


def _select(source: QueryResult, condition: dict) -> QueryResult:
    _validate_condition(condition, source.columns)

    res: QueryResult = QueryResult(
        columns=source.columns,
        rows=[],
    )
    for row in source.rows:
        if _resolve_condition(condition, row):
            res.rows.append(row)

    return res


def _project(source: QueryResult, columns: list[str] | str) -> QueryResult:
    if columns == "*":
        return _remove_duplicates(source)

    if isinstance(columns, str):
        column_list = [columns]
    else:
        column_list = columns

    seen = set()
    for column in column_list:
        if column not in source.columns:
            raise ValueError(f"Unknown column: {column}")
        if column in seen:
            raise ValueError(f"Duplicate PROJECT column: {column}")
        seen.add(column)

    res = QueryResult(columns=column_list, rows=[])

    for row in source.rows:
        projected_row = {}

        for column in column_list:
            projected_row[column] = row[column]

        res.rows.append(projected_row)

    return _remove_duplicates(res)


def _rename(source: QueryResult, old_name: str, new_name: str) -> QueryResult:
    if old_name not in source.columns:
        raise ValueError(f"Unknown column: {old_name}")
    if new_name in source.columns:
        raise ValueError(f"Column already exists: {new_name}")

    columns = []
    for column in source.columns:
        if column == old_name:
            columns.append(new_name)
        else:
            columns.append(column)

    rows = []
    for row in source.rows:
        renamed_row = {}
        for column, value in row.items():
            if column == old_name:
                renamed_row[new_name] = value
            else:
                renamed_row[column] = value
        rows.append(renamed_row)

    return QueryResult(columns=columns, rows=rows)


def _aggregate(source: QueryResult, columns: list[str] | str, function: dict) -> QueryResult:
    if columns == "*":
        group_columns = []
    elif isinstance(columns, str):
        group_columns = [columns]
    else:
        group_columns = columns

    name = function["name"].lower()
    target = function["column"]

    if name not in {"sum", "avg", "min", "max", "count"}:
        raise ValueError(f"Unknown aggregate function: {name}")

    for column in group_columns:
        if column not in source.columns:
            raise ValueError(f"Unknown column: {column}")
    if target not in source.columns:
        raise ValueError(f"Unknown column: {target}")

    result_column = f"{name.upper()}_{target}"
    suffix = 2

    while result_column in group_columns:
        result_column = f"{name.upper()}_{target}_{suffix}"
        suffix += 1

    groups = {}
    if not group_columns:
        groups[()] = []

    for row in source.rows:
        group_values = []
        for column in group_columns:
            group_values.append(row[column])
        key = tuple(group_values)

        if key not in groups:
            groups[key] = []

        if row[target] is not None:
            groups[key].append(row[target])

    res = QueryResult(columns=group_columns + [result_column], rows=[])
    for key, values in groups.items():
        if name in {"sum", "avg"}:
            for value in values:
                if type(value) not in (int, float):
                    raise ValueError(f"{name.upper()} requires numeric values in {target}.")

        if name == "count":
            value = len(values)

        elif not values:
            value = None

        else:
            match name:
                case "sum":
                    value = sum(values)
                case "avg":
                    value = sum(values) / len(values)
                case "min":
                    value = min(values)
                case "max":
                    value = max(values)

        result_row = {}
        for index in range(len(group_columns)):
            column = group_columns[index]
            result_row[column] = key[index]

        result_row[result_column] = value
        res.rows.append(result_row)

    return res


def _join(left: QueryResult, right: QueryResult, condition: dict) -> QueryResult:
    collisions = set(left.columns) & set(right.columns)

    if collisions:
        raise ValueError(
            f"JOIN column names overlap: {', '.join(sorted(collisions))}. "
            "Use RENAME on an input before joining."
        )

    _validate_condition(condition, left.columns, right.columns)

    res = QueryResult(columns=left.columns + right.columns, rows=[])

    for left_row in left.rows:
        for right_row in right.rows:
            if _resolve_condition(condition, left_row, right_row):
                res.rows.append(left_row | right_row)

    return res


def _union(left: QueryResult, right: QueryResult) -> QueryResult:
    _validate_set_inputs(left, right)
    combined = QueryResult(columns=left.columns, rows=left.rows + right.rows)
    return _remove_duplicates(combined)


def _intersect(left: QueryResult, right: QueryResult) -> QueryResult:
    _validate_set_inputs(left, right)

    # making a set of keys to make avg O(1) lookup for a key
    right_keys = {
        tuple(row[column] for column in right.columns)
        for row in right.rows
    }

    # seen set is for handling duplicates
    seen = set()
    res = QueryResult(columns=left.columns, rows=[])

    for row in left.rows:
        key = tuple(row[column] for column in left.columns)

        if key in right_keys and key not in seen:
            res.rows.append(row)
            seen.add(key)

    return res


def _difference(left: QueryResult, right: QueryResult) -> QueryResult:
    _validate_set_inputs(left, right)

    # making a set of keys to make avg O(1) lookup for a key
    right_keys = {
        tuple(row[column] for column in right.columns)
        for row in right.rows
    }

    # seen set is for handling duplicates
    seen = set()
    res = QueryResult(columns=left.columns, rows=[])

    for row in left.rows:
        key = tuple(row[column] for column in left.columns)

        if key not in right_keys and key not in seen:
            res.rows.append(row)
            seen.add(key)

    return res


def _remove_duplicates(source: QueryResult) -> QueryResult:
    res = QueryResult(columns=source.columns, rows=[])

    seen = set()

    for row in source.rows:
        values = []

        for column in source.columns:
            values.append(row[column])

        key = tuple(values)

        if key not in seen:
            res.rows.append(row)
            seen.add(key)

    return res


def _validate_set_inputs(left: QueryResult, right: QueryResult) -> None:
    if left.columns != right.columns:
        raise TypeError(f"Columns mismatch: {left.columns} != {right.columns}")

    for column in left.columns:
        expected_type = None
        for relation in (left, right):
            for row in relation.rows:
                value = row[column]
                if value is None:
                    continue

                if type(value) in (int, float):
                    value_type = "number"
                elif type(value) is str:
                    value_type = "text"
                elif type(value) is bool:
                    value_type = "boolean"
                else:
                    raise TypeError(f"Column {column} must contain scalar values.")

                if expected_type is None:
                    expected_type = value_type
                elif value_type != expected_type:
                    raise TypeError(
                        f"Incompatible types in column {column}: "
                        f"{expected_type} and {value_type}."
                    )


def _validate_condition(condition: dict, left_columns: list[str],
                        right_columns: list[str] | None = None) -> None:
    if right_columns is None:
        right_columns = left_columns

    operation = condition["operation"]

    match operation:
        case "not":
            _validate_condition(condition["condition"], left_columns, right_columns)

        case "and" | "or":
            _validate_condition(condition["left"], left_columns, right_columns)
            _validate_condition(condition["right"], left_columns, right_columns)

        case "compare":
            left = condition["left"]
            right = condition["right"]

            if left["kind"] == "column" and left["value"] not in left_columns:
                raise ValueError(f"Unknown column on left input: {left['value']}")

            if right["kind"] == "column" and right["value"] not in right_columns:
                raise ValueError(f"Unknown column on right input: {right['value']}")
        case _:
            raise ValueError(f"Unknown condition operation: {operation}")


def _resolve_condition(condition: dict, left_row: dict[str, Any],
                       right_row: dict[str, Any] | None = None) -> bool:
    if right_row is None:
        right_row = left_row

    operation = condition["operation"]

    match operation:
        case "not":
            return not _resolve_condition(condition["condition"], left_row, right_row)
        case "and":
            left = _resolve_condition(condition["left"], left_row, right_row)
            right = _resolve_condition(condition["right"], left_row, right_row)
            return left & right
        case "or":
            left = _resolve_condition(condition["left"], left_row, right_row)
            right = _resolve_condition(condition["right"], left_row, right_row)
            return left | right
        case "compare":
            operator = condition["operator"]
            left = condition["left"]
            right = condition["right"]

            left_value = (left_row[left["value"]] if left["kind"] == "column" else left["value"])
            right_value = (right_row[right["value"]] if right["kind"] == "column" else right["value"])

            match operator:
                case "=":
                    return left_value == right_value
                case "!=":
                    return left_value != right_value
                case ">":
                    return left_value > right_value
                case "<":
                    return left_value < right_value
                case ">=":
                    return left_value >= right_value
                case "<=":
                    return left_value <= right_value

    raise TypeError(f"Unknown operation: {operation}")
