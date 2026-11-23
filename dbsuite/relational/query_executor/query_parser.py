import ply.yacc as yacc

from .query_lexer import lexer, tokens

def parse_query(expression: str) -> dict:
    query_lexer = lexer.clone()
    query_lexer.lineno = 1
    return parser.parse(expression, lexer=query_lexer)

start = "query"

def p_query_select(p):
    """query : SELECT WHERE condition FROM relation"""
    p[0] = {
        "operation": "select",
        "condition": p[3],
        "source": p[5],
    }

def p_query_project(p):
    """query : PROJECT columns FROM relation"""
    p[0] = {
        "operation": "project",
        "columns": p[2],
        "source": p[4],
    }

def p_query_rename(p):
    """query : RENAME NAME TO NAME FROM relation"""
    p[0] = {
        "operation": "rename",
        "old_name": p[2],
        "new_name": p[4],
        "source": p[6],
    }

def p_query_join(p):
    """query : JOIN relation COMMA relation ON condition"""
    p[0] = {
        "operation": "join",
        "left": p[2],
        "right": p[4],
        "condition": p[6],
    }

def p_query_set(p):
    """query : relation UNION relation
             | relation INTERSECT relation
             | relation DIFFERENCE relation"""
    p[0] = {
        "operation": p.slice[2].type.lower(),
        "left": p[1],
        "right": p[3],
    }

def p_query_aggregate(p):
    """query : AGGREGATE columns FROM relation BY aggregate_function"""
    p[0] = {
        "operation": "aggregate",
        "columns": p[2],
        "source": p[4],
        "function": p[6],
    }

def p_relation_name(p):
    """relation : NAME"""
    p[0] = {"operation": "table", "name": p[1]}

def p_relation_nested(p):
    """relation : LPAREN query RPAREN"""
    p[0] = p[2]

def p_condition_or(p):
    """condition : condition OR term"""
    p[0] = {"operation": "or", "left": p[1], "right": p[3]}

def p_condition_term(p):
    """condition : term"""
    p[0] = p[1]

def p_term_and(p):
    """term : term AND predicate"""
    p[0] = {"operation": "and", "left": p[1], "right": p[3]}

def p_term_predicate(p):
    """term : predicate"""
    p[0] = p[1]

def p_predicate_not(p):
    """predicate : NOT predicate"""
    p[0] = {"operation": "not", "condition": p[2]}

def p_predicate_nested(p):
    """predicate : LPAREN condition RPAREN"""
    p[0] = p[2]

def p_predicate_comparison(p):
    """predicate : operand COMPARE operand"""
    p[0] = {
        "operation": "compare",
        "left": p[1],
        "operator": p[2],
        "right": p[3],
    }

def p_operand_column(p):
    """operand : NAME"""
    p[0] = {"kind": "column", "value": p[1]}

def p_operand_literal(p):
    """operand : NUMBER
               | STRING"""
    p[0] = {"kind": "literal", "value": p[1]}

def p_columns_all(p):
    """columns : STAR"""
    p[0] = "*"

def p_columns_list(p):
    """columns : column_list"""
    p[0] = p[1]

def p_column_list_one(p):
    """column_list : NAME"""
    p[0] = [p[1]]

def p_column_list_more(p):
    """column_list : NAME COMMA column_list"""
    p[0] = [p[1]] + p[3]

def p_aggregate_function(p):
    """aggregate_function : function_name LPAREN NAME RPAREN"""
    p[0] = {"name": p[1], "column": p[3]}

def p_function_name(p):
    """function_name : SUM
                     | AVG
                     | MAX
                     | MIN
                     | COUNT"""
    p[0] = p.slice[1].type.lower()

def p_error(p):
    if p is None:
        raise SyntaxError("Unexpected end of query.")
    raise SyntaxError(f"Unexpected token {p.value!r} on line {p.lineno}.")

parser = yacc.yacc(write_tables=False, debug=False)