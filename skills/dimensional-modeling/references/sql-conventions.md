# SQL Conventions for Gold-Layer Dimensional Models

Load this reference when generating DDL or SQL SELECT statements.

## DDL Conventions

1. **Grain declaration**: Always declare the grain of each fact table in a comment block
2. **Apache Iceberg format**: `TBLPROPERTIES ('table_type'='ICEBERG')`
3. **Surrogate keys**: `BIGINT AUTO_INCREMENT` for all dimension tables
4. **SCD Type 2 columns**: `effective_date DATE`, `expiry_date DATE`, `is_current BOOLEAN`
5. **Column comments**: Every column must have a comment explaining its business meaning
6. **Indicator traceability**: Include a comment block at top of each DDL:
   ```sql
   -- Supports indicators: <comma-separated list of KPI names>
   ```
7. **Dimension justification**: Each dimension must be justified by columns found in the silver layer
8. **ETL description**: Include a brief description of the ETL flow from silver to gold

## SQL SELECT Conventions

1. **Verified sources only**: Reference ONLY tables and columns confirmed via `get_table_schema` — never invent column names
2. **Match DDL exactly**: Column aliases in SELECT must correspond exactly to column names in DDL
3. **Document transformations**: Add inline SQL comments (`-- explanation`) for complex JOINs, business logic, and non-obvious transformations
4. **NULL handling**: Use `COALESCE` with sensible defaults where NULL values from silver could break model integrity
5. **Surrogate key generation**: Use `ROW_NUMBER() OVER (...)` or equivalent window functions for dimension surrogate keys
6. **SCD Type 2 logic**: When DDL includes SCD Type 2 columns, include change detection logic that sets `effective_date`, `expiry_date`, and `is_current`
7. **Grain enforcement**: Include `GROUP BY` when the declared grain requires aggregation from a finer-grained source
8. **Aggregate fact population**: SELECT for aggregate fact tables must source from the **base fact table** in gold (NOT from silver directly), with `GROUP BY` at the aggregate grain and appropriate aggregate functions (`SUM`, `COUNT`, `AVG`, etc.)
9. **ANSI SQL**: Write standard ANSI SQL — no vendor-specific syntax
