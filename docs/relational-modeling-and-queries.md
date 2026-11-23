# Relational mapping and dataset queries

This guide explains how to convert an ER schema into relational tables and how to query JSON datasets in DB Suite. For installation and startup, see the [main README](../README.md).

## Convert an ER schema

Open **ER Mapper**, paste or load an ER schema, and select **Convert to relational model**. The result includes a diagram and JSON representation. The diagram shows tables, primary keys, foreign keys, and references between tables.

The mapper reads entity attributes and relationship participants from the ER schema. It supports simple, composite, multivalued, derived, and key attributes. Weak entities use `isWeak` and `partialKey`; identifying relationships use `isIdentifying`.

The mapper applies these rules:

- Composite attributes become prefixed columns in the owning table.
- Multivalued attributes get separate tables linked to their owner. This also applies to nested multivalued attributes.
- A weak entity's key combines its owner's key with its partial key.
- Binary 1:1 and 1:N relationships add foreign keys. M:N and n-ary relationships become separate tables.
- Relationship attributes are mapped to columns. Derived attributes are omitted.

## Query JSON datasets

Open **Dataset Queries** and provide a JSON object whose keys are table names and whose values are arrays of row objects. Enter a query expression and select **Execute query**. DB Suite displays the result rows and row count.

For example, a dataset can contain an `Employee` table with rows represented as JSON objects. Use `SELECT` to filter rows and `PROJECT` to choose columns:

```text
SELECT WHERE Salary > 5000 FROM Employee
PROJECT Name, Salary FROM Employee
```

### Operations

| Operation | Example |
| --- | --- |
| SELECT | `SELECT WHERE Salary > 5000 FROM Employee` |
| PROJECT | `PROJECT Name, Salary FROM Employee` |
| RENAME | `RENAME Name TO EmployeeName FROM Employee` |
| JOIN | `JOIN A, B ON EmployeeDeptID = DepartmentID` |
| UNION | `A UNION B` |
| INTERSECT | `A INTERSECT B` |
| DIFFERENCE | `A DIFFERENCE B` |
| AGGREGATE | `AGGREGATE DeptID FROM Employee BY SUM(Salary)` |

The query language is case-insensitive for keywords. Column and table names keep their spelling. Write string values in double quotes. Comparisons support `=`, `!=`, `>`, `<`, `>=`, and `<=`. Conditions support `NOT`, `AND`, and `OR`, in that precedence order. Parentheses can override condition precedence or contain a nested query:

```text
PROJECT Name FROM (SELECT WHERE Salary > 5000 FROM Employee)
```

See the [full query grammar](query-language-grammar.md) for the language syntax.

### Joins and renaming columns

JOIN returns all columns from both inputs. The inputs must have distinct column names, so rename collisions before joining. In each `ON` comparison, the left column belongs to the left input and the right column belongs to the right input.

This example renames the overlapping `Name` and `DeptID` columns before joining:

```text
JOIN Employee,
     (RENAME DeptID TO DepartmentID FROM
         (RENAME Name TO DepartmentName FROM Department))
ON DeptID = DepartmentID
```

RENAME changes one column at a time and keeps its values and position. It reports an error if the source column is missing or the new name already exists. Nested joins use the output column names produced by their inner queries.

### Aggregation

Supported functions are `SUM`, `AVG`, `MIN`, `MAX`, and `COUNT`. Put grouping columns before `FROM` and the function after `BY`:

```text
AGGREGATE DeptID FROM Employee BY SUM(Salary)
```

This returns `DeptID` and `SUM_Salary`. To aggregate the whole table without grouping, use `*`:

```text
AGGREGATE * FROM Employee BY AVG(Salary)
```

An aggregate query accepts one function. Results contain the grouping columns and one calculated column named for the function and target. If that name conflicts with a grouping column, the result adds a suffix.

Aggregates skip null values. With no grouping columns, empty input returns one row: `COUNT` is zero and other functions return null. Grouped empty input returns no rows. `SUM` and `AVG` require numeric values. The grammar does not support `COUNT(*)`.

## Data requirements

- Each dataset cell must be a scalar JSON value: a string, number, boolean, or null. Nested arrays and objects are unsupported.
- Set operations require both inputs to have the same column names in the same order. Use PROJECT and RENAME to align them.
- JOIN inputs must have distinct column names. Rename collisions explicitly, including when joining a table to itself.
- In a JOIN comparison, the left operand refers to a column from the left input and the right operand to a column from the right input.
