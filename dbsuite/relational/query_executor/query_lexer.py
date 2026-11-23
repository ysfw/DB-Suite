import json

import ply.lex as lex

keywords = {
    "SELECT", "WHERE", "PROJECT", "FROM", "JOIN", "ON", "RENAME", "TO",
    "UNION", "INTERSECT", "DIFFERENCE", "AGGREGATE", "BY",
    "SUM", "AVG", "MAX", "MIN", "COUNT", "AND", "OR", "NOT",
}

tokens = tuple(keywords) + (
    "NAME", "NUMBER", "STRING", "COMPARE",
    "LPAREN", "RPAREN", "COMMA", "STAR",
)

t_LPAREN = r"\("
t_RPAREN = r"\)"
t_COMMA = r","
t_STAR = r"\*"
t_COMPARE = r">=|<=|!=|=|>|<"

t_ignore = " \t\r"

def t_NUMBER(t):
    r"""[+-]?\d+(\.\d+)?"""
    if "." in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_STRING(t):
    """\"([^\"\\\\\\r\\n]|\\\\.)*\""""
    try:
        t.value = json.loads(t.value)
    except json.JSONDecodeError:
        raise SyntaxError(f"Invalid string on line {t.lineno}.") from None
    return t

def t_NAME(t):
    r"""[a-zA-Z_][a-zA-Z_0-9]*"""
    word = t.value.upper()
    t.type = word if word in keywords else "NAME"
    return t

def t_newline(t):
    r"""\n+"""
    t.lexer.lineno += len(t.value)

def t_error(t):
    raise SyntaxError(
        f"Unexpected character {t.value[0]!r} on line {t.lineno}."
    )

lexer = lex.lex()