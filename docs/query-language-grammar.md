# Grammar

- Q → SELECT WHERE B FROM A
    | PROJECT C FROM A
    | RENAME attribute TO attribute FROM A
    | JOIN A, A ON B
    | A UNION A
    | A INTERSECT A
    | A DIFFERENCE A
    | AGGREGATE C FROM A BY Func

- A → relation | "(" Q ")"
- B → B OR T | T
- T → T AND P | P
- P → NOT P | "(" B ")" | operand E operand
- operand → attribute | val
- C → D | "*"
- D → attribute | attribute "," D
- Func → f "(" attribute ")"
- f → SUM | AVG | MAX | MIN | COUNT
- E → "=" | "!=" | ">" | "<" | ">=" | "<="
- val → STRING | NUMBER