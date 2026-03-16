```
modelo_dimensional_consorcio.md
```

---

# Modelo Dimensional – Consórcio

Baseado na análise das tabelas **Silver** do consórcio e seguindo os princípios de dimensional modeling do livro ***Star Schema: The Complete Reference*** de **Christopher Adamson**, é proposta uma arquitetura dimensional composta por:

* **3 fact tables**
* **6 dimension tables (conformed dimensions)**

O objetivo é suportar análise histórica e permitir **drill-across entre processos de negócio**.

---

# Arquitetura Dimensional Proposta

## Fact Tables

### 1. FACT_CONTEMPLACAO

**Grain**

Uma contemplação **por assembleia por cota**

**Processo de negócio**

Processo de contemplação em assembleias.

---

### 2. FACT_PAGAMENTOS

**Grain**

Um pagamento **por parcela por cota**

**Processo de negócio**

Processo de pagamento das parcelas.

---

### 3. FACT_LANCES

**Grain**

Um lance **por assembleia por cota**

**Processo de negócio**

Processo de lances em assembleias.

---

# Shared Dimension Tables (Conformed Dimensions)

As dimensões são **compartilhadas entre diferentes processos de negócio**, permitindo análise integrada.

| Dimensão       | Descrição                   |
| -------------- | --------------------------- |
| DIM_CLIENTE    | Dados do cliente            |
| DIM_GRUPO      | Dados do grupo de consórcio |
| DIM_COTA       | Dados da cota               |
| DIM_ASSEMBLEIA | Informações das assembleias |
| DIM_DATA       | Dimensão calendário         |
| DIM_CANAL      | Canal de aquisição do lead  |

---

# DDL – Camada Gold

## Dimension Tables

```sql
-- =============================================
-- DIMENSION TABLES
-- =============================================

-- Cliente dimension (SCD Type 2 for tracking changes)

CREATE TABLE gold.dim_cliente (
    cliente_key BIGINT AUTO_INCREMENT,     -- Surrogate key
    cliente_id STRING NOT NULL,            -- Natural key (CPF)

    nome STRING,
    email STRING,
    telefone STRING,

    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT TRUE,

    CONSTRAINT pk_dim_cliente PRIMARY KEY (cliente_key)
)
COMMENT 'Dimensão de clientes com histórico (SCD Type 2)'
TBLPROPERTIES ('table_type'='ICEBERG');


-- Grupo dimension

CREATE TABLE gold.dim_grupo (
    grupo_key BIGINT AUTO_INCREMENT,
    grupo_id STRING NOT NULL,

    produto STRING,
    prazo_meses INT,
    valor_credito DECIMAL(15,2),
    taxa_adm DECIMAL(5,4),

    CONSTRAINT pk_dim_grupo PRIMARY KEY (grupo_key)
)
COMMENT 'Dimensão de grupos de consórcio'
TBLPROPERTIES ('table_type'='ICEBERG');


-- Cota dimension (SCD Type 2)

CREATE TABLE gold.dim_cota (
    cota_key BIGINT AUTO_INCREMENT,
    cota_id STRING NOT NULL,

    proposta_id STRING,
    grupo_id STRING NOT NULL,
    status STRING,
    data_ativacao DATE,

    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT TRUE,

    CONSTRAINT pk_dim_cota PRIMARY KEY (cota_key)
)
COMMENT 'Dimensão de cotas com histórico de status (SCD Type 2)'
TBLPROPERTIES ('table_type'='ICEBERG');


-- Assembleia dimension

CREATE TABLE gold.dim_assembleia (
    assembleia_key BIGINT AUTO_INCREMENT,
    assembleia_id STRING NOT NULL,

    grupo_id STRING NOT NULL,
    data_assembleia DATE,

    CONSTRAINT pk_dim_assembleia PRIMARY KEY (assembleia_key)
)
COMMENT 'Dimensão de assembleias'
TBLPROPERTIES ('table_type'='ICEBERG');


-- Date dimension

CREATE TABLE gold.dim_data (
    data_key BIGINT AUTO_INCREMENT,

    full_date DATE NOT NULL,
    day_of_week INT,
    day_name STRING,
    day_of_month INT,
    day_of_year INT,
    week_of_year INT,

    month_num INT,
    month_name STRING,
    month_abbr STRING,

    quarter INT,
    quarter_name STRING,

    year INT,
    fiscal_year INT,

    is_weekend BOOLEAN,
    is_holiday BOOLEAN,

    CONSTRAINT pk_dim_data PRIMARY KEY (data_key)
)
COMMENT 'Dimensão de datas conformed'
TBLPROPERTIES ('table_type'='ICEBERG');


-- Canal dimension

CREATE TABLE gold.dim_canal (
    canal_key BIGINT AUTO_INCREMENT,
    canal STRING NOT NULL,

    CONSTRAINT pk_dim_canal PRIMARY KEY (canal_key)
)
COMMENT 'Dimensão de canais de aquisição'
TBLPROPERTIES ('table_type'='ICEBERG');
```

---

# Fact Tables

```sql
-- =============================================
-- FACT TABLES
-- =============================================

-- FACT_CONTEMPLACAO

CREATE TABLE gold.fact_contemplacao (
    contemplacao_key BIGINT AUTO_INCREMENT,
    contemplacao_id STRING NOT NULL,

    cota_key BIGINT NOT NULL,
    assembleia_key BIGINT NOT NULL,
    data_key BIGINT NOT NULL,

    tipo_contemplacao STRING,

    qtd_contemplacoes INT DEFAULT 1,

    CONSTRAINT pk_fact_contemplacao PRIMARY KEY (contemplacao_key),
    CONSTRAINT fk_contemplacao_cota FOREIGN KEY (cota_key)
        REFERENCES dim_cota(cota_key),
    CONSTRAINT fk_contemplacao_assembleia FOREIGN KEY (assembleia_key)
        REFERENCES dim_assembleia(assembleia_key),
    CONSTRAINT fk_contemplacao_data FOREIGN KEY (data_key)
        REFERENCES dim_data(data_key)
)
COMMENT 'Grain: uma contemplação por assembleia por cota'
TBLPROPERTIES ('table_type'='ICEBERG');


-- FACT_PAGAMENTOS

CREATE TABLE gold.fact_pagamentos (
    pagamento_key BIGINT AUTO_INCREMENT,
    pagamento_id STRING NOT NULL,

    cota_key BIGINT NOT NULL,
    data_key BIGINT NOT NULL,
    parcela INT NOT NULL,

    valor_pago DECIMAL(15,2),
    qtd_pagamentos INT DEFAULT 1,

    CONSTRAINT pk_fact_pagamentos PRIMARY KEY (pagamento_key),
    CONSTRAINT fk_pagamento_cota FOREIGN KEY (cota_key)
        REFERENCES dim_cota(cota_key),
    CONSTRAINT fk_pagamento_data FOREIGN KEY (data_key)
        REFERENCES dim_data(data_key)
)
COMMENT 'Grain: um pagamento por cota por parcela'
TBLPROPERTIES ('table_type'='ICEBERG');


-- FACT_LANCES

CREATE TABLE gold.fact_lances (
    lance_key BIGINT AUTO_INCREMENT,
    lance_id STRING NOT NULL,

    cota_key BIGINT NOT NULL,
    assembleia_key BIGINT NOT NULL,
    data_key BIGINT NOT NULL,

    tipo_lance STRING,

    valor_lance DECIMAL(15,2),
    qtd_lances INT DEFAULT 1,

    CONSTRAINT pk_fact_lances PRIMARY KEY (lance_key),
    CONSTRAINT fk_lance_cota FOREIGN KEY (cota_key)
        REFERENCES dim_cota(cota_key),
    CONSTRAINT fk_lance_assembleia FOREIGN KEY (assembleia_key)
        REFERENCES dim_assembleia(assembleia_key),
    CONSTRAINT fk_lance_data FOREIGN KEY (data_key)
        REFERENCES dim_data(data_key)
)
COMMENT 'Grain: um lance por cota por assembleia'
TBLPROPERTIES ('table_type'='ICEBERG');
```

---

# ETL – Silver → Gold

## Populando Dimension Tables

```sql
-- DIM_CLIENTE (SCD Type 2)

INSERT INTO gold.dim_cliente
(
    cliente_id,
    nome,
    email,
    telefone,
    effective_date,
    expiry_date,
    is_current
)
SELECT
    l.cpf,
    l.nome,
    l.email,
    l.telefone,
    CAST(l.data_lead AS DATE),
    DATE '9999-12-31',
    TRUE
FROM silver.consorcio_leads l
WHERE l.cpf IS NOT NULL;
```

---

```sql
-- DIM_GRUPO

INSERT INTO gold.dim_grupo
SELECT DISTINCT
    g.grupo_id,
    g.produto,
    CAST(g.prazo_meses AS INT),
    CAST(g.valor_credito AS DECIMAL(15,2)),
    CAST(g.taxa_adm AS DECIMAL(5,4))
FROM silver.consorcio_grupos g;
```

---

```sql
-- DIM_COTA

INSERT INTO gold.dim_cota
SELECT
    c.cota_id,
    c.proposta_id,
    c.grupo_id,
    c.status,
    CAST(c.data_ativacao AS DATE),

    COALESCE(CAST(c.data_ativacao AS DATE), CURRENT_DATE),
    DATE '9999-12-31',
    TRUE
FROM silver.consorcio_cotas c;
```

---

```sql
-- DIM_ASSEMBLEIA

INSERT INTO gold.dim_assembleia
SELECT DISTINCT
    a.assembleia_id,
    a.grupo_id,
    CAST(a.data_assembleia AS DATE)
FROM silver.consorcio_assembleias a;
```

---

```sql
-- DIM_CANAL

INSERT INTO gold.dim_canal
SELECT DISTINCT canal
FROM silver.consorcio_leads
WHERE canal IS NOT NULL;
```

---

# Populando Fact Tables

```sql
-- FACT_CONTEMPLACAO

INSERT INTO gold.fact_contemplacao
SELECT
    c.contemplacao_id,
    dc.cota_key,
    da.assembleia_key,
    dd.data_key,
    c.tipo,
    1
FROM silver.consorcio_contemplacoes c
JOIN gold.dim_cota dc
    ON c.cota_id = dc.cota_id
    AND dc.is_current = TRUE
JOIN gold.dim_assembleia da
    ON c.assembleia_id = da.assembleia_id
JOIN gold.dim_data dd
    ON CAST(c.data_contemplacao AS DATE) = dd.full_date;
```

---

```sql
-- FACT_PAGAMENTOS

INSERT INTO gold.fact_pagamentos
SELECT
    p.pagamento_id,
    dc.cota_key,
    dd.data_key,
    CAST(p.parcela AS INT),
    CAST(p.valor_pago AS DECIMAL(15,2)),
    1
FROM silver.consorcio_pagamentos p
JOIN gold.dim_cota dc
    ON p.cota_id = dc.cota_id
    AND dc.is_current = TRUE
JOIN gold.dim_data dd
    ON CAST(p.data_pagamento AS DATE) = dd.full_date;
```

---

```sql
-- FACT_LANCES

INSERT INTO gold.fact_lances
SELECT
    l.lance_id,
    dc.cota_key,
    da.assembleia_key,
    dd.data_key,
    l.tipo_lance,
    CAST(l.valor_lance AS DECIMAL(15,2)),
    1
FROM silver.consorcio_lances l
JOIN gold.dim_cota dc
    ON l.cota_id = dc.cota_id
    AND dc.is_current = TRUE
JOIN gold.dim_assembleia da
    ON l.assembleia_id = da.assembleia_id
JOIN gold.dim_data dd
    ON da.data_assembleia = dd.full_date;
```

---

# Princípios de Dimensional Modeling Aplicados

Este modelo segue os princípios fundamentais do **dimensional modeling**:

### Conformed Dimensions

Permitem **drill-across entre processos de negócio**.

Exemplo:

* pagamentos por cliente
* contemplações por cliente
* lances por cliente

Tudo usando **as mesmas dimensões**.

---

### Surrogate Keys

Uso de **surrogate keys** (`*_key`) para:

* independência da origem
* melhor performance de join
* controle de histórico

---

### Slowly Changing Dimensions (SCD Type 2)

Utilizado em:

* **dim_cliente**
* **dim_cota**

Permite rastrear mudanças históricas como:

* mudança de telefone/email
* mudança de status da cota

