# Estimativa de Custo — RAG Bedrock Agent (Dimensional Modeling)

**Data:** 23/03/2026
**Projeto:** Agente de Modelagem Dimensional com Amazon Bedrock
**Região AWS:** us-east-1

---

## 1. Visao Geral da Arquitetura

| Componente | Servico AWS | Funcao |
|------------|-------------|--------|
| LLM (Agente) | Amazon Bedrock — Claude Sonnet 4 | Raciocinio, geracao de DDL/ETL SQL |
| Embeddings | Amazon Bedrock — Titan Embeddings V2 | Vetorizacao de documentos e queries |
| Base de Conhecimento | Amazon Bedrock Knowledge Bases | Orquestracao RAG |
| Armazenamento Vetorial | Amazon S3 Vectors | Indice de embeddings (1024 dims, cosine) |
| Action Group | AWS Lambda (256 MB, Python 3.12) | Acesso ao Glue Data Catalog |
| Catalogo de Dados | AWS Glue Data Catalog | Metadados das tabelas silver |
| Armazenamento | Amazon S3 Standard | Documentos fonte, scripts SQL gerados |

---

## 2. Precos Unitarios (us-east-1, marco/2026)

| Servico | Metrica | Preco Unitario | Fonte |
|---------|---------|----------------|-------|
| Claude Sonnet 4 (cross-region) | Input tokens | $3,00 / 1M tokens | aws.amazon.com/bedrock/pricing |
| Claude Sonnet 4 (cross-region) | Output tokens | $15,00 / 1M tokens | aws.amazon.com/bedrock/pricing |
| Titan Embeddings V2 | Input tokens | $0,11 / 1M tokens | aws.amazon.com/bedrock/pricing |
| S3 Vectors | Armazenamento | $0,06 / GB / mes | aws.amazon.com/s3/pricing |
| S3 Vectors | Queries | $2,50 / 1M chamadas | aws.amazon.com/s3/pricing |
| Lambda | Requisicoes | $0,20 / 1M requests | aws.amazon.com/lambda/pricing |
| Lambda | Compute (x86) | $0,0000166667 / GB-s | aws.amazon.com/lambda/pricing |
| Glue Data Catalog | Metadata access | Gratis (1M acessos/mes free tier) | aws.amazon.com/glue/pricing |
| S3 Standard | Armazenamento | $0,023 / GB / mes | aws.amazon.com/s3/pricing |

---

## 3. Premissas por Sessao

Uma sessao tipica de consultoria dimensional (usuario solicita modelo dimensional para um processo de negocio):

| Item | Valor Estimado |
|------|---------------|
| Turnos de conversa (user - agent) | 5-8 (media: 7) |
| System prompt (enviado a cada turno pelo agente) | ~4.000 tokens |
| KB retrievals por sessao | 3-5 (media: 4), retornando 5 chunks x 300 tokens = 1.500 tokens cada |
| Invocacoes Lambda por sessao | 5-8 (list_databases, list_tables, get_table_schema, get_table_statistics, save_sql_script) |
| Tokens de saida por turno | ~1.500-3.000 (raciocinio + DDL/ETL SQL) |

### 3.1 Calculo de Tokens por Sessao

**Input tokens:**

| Componente | Calculo | Tokens |
|------------|---------|--------|
| System prompt x turnos | 4.000 x 7 | 28.000 |
| Contexto do KB (retrievals) | 4 x 1.500 | 6.000 |
| Resultados Lambda (tool results) | 7 x 500 | 3.500 |
| Mensagens do usuario | 7 x 200 | 1.400 |
| Historico acumulado da conversa | crescimento progressivo | ~20.000 |
| **Total input** | | **~60.000-80.000** |

**Output tokens:**

| Componente | Calculo | Tokens |
|------------|---------|--------|
| Respostas + raciocinio do agente | 7 x 2.000 | 14.000 |
| SQL DDL/ETL gerado | - | ~3.000 |
| **Total output** | | **~17.000** |

---

## 4. Custo por Sessao

| Servico | Calculo | Custo |
|---------|---------|-------|
| **Claude Sonnet 4 - Input** | 70K tokens x $3/1M | **$0,21** |
| **Claude Sonnet 4 - Output** | 17K tokens x $15/1M | **$0,255** |
| Titan Embeddings V2 | 4 queries x 200 tokens x $0.11/1M | $0,0001 |
| S3 Vectors - Queries | 4 queries x $2.50/1M | $0,00001 |
| Lambda - Requests | 7 requests x $0.20/1M | $0,0000014 |
| Lambda - Compute | 7 x 0.25GB x 2s = 3.5 GB-s x $0.0000167 | $0,00006 |
| Glue Data Catalog | Free tier (< 1M acessos) | $0,00 |
| **TOTAL POR SESSAO** | | **~ $0,47** |

> **~95% do custo vem do Claude Sonnet 4 (inference).** Todos os demais servicos sao despreziveis.

---

## 5. Estimativa Mensal por Cenario de Uso

| Cenario | Sessoes/mes | Custo LLM | Outros servicos | **Total/mes** |
|---------|-------------|-----------|-----------------|---------------|
| **Baixo** - 1 analista, uso esporadico | 50 | $23,50 | < $1 | **~$25** |
| **Medio** - equipe pequena, uso regular | 200 | $94,00 | < $3 | **~$97** |
| **Alto** - multiplas equipes, uso intenso | 500 | $235,00 | < $5 | **~$240** |
| **Muito Alto** - producao enterprise | 1.000 | $470,00 | < $10 | **~$480** |

### 5.1 Custos Fixos Mensais (independente de uso)

| Item | Custo estimado |
|------|----------------|
| S3 Standard (documentos fonte, ~1 GB) | ~$0,02 |
| S3 Vectors (indice de embeddings, ~50 MB) | ~$0,003 |
| S3 (scripts SQL gerados, < 100 MB) | ~$0,002 |
| **Total fixo/mes** | **< $0,10** |

### 5.2 Custo de Ingestao (one-time ou re-ingestao)

| Item | Calculo | Custo |
|------|---------|-------|
| Embedding do corpus (ex: 100 paginas, ~50K tokens) | 50K x $0.11/1M | **< $0,01** |

---

## 6. Resumo Executivo

| Metrica | Valor |
|---------|-------|
| **Custo por sessao** | **~$0,47** |
| **Custo mensal (200 sessoes)** | **~$97** |
| **Custo fixo mensal (storage)** | **< $0,10** |
| **Principal driver de custo** | Claude Sonnet 4 inference (~95%) |
| **Free tiers aplicaveis** | Lambda (1M req + 400K GB-s/mes), Glue (1M acessos/mes), S3 Vectors (primeiros 12 meses) |

---

## 7. Oportunidades de Otimizacao

| Estrategia | Economia Estimada | Impacto |
|-----------|-------------------|---------|
| **Batch API** (processamento assincrono) | -50% no inference | Aplicavel para workflows nao-interativos |
| **Prompt Caching** (Bedrock) | -20-40% input tokens | Reduz custo em turnos repetidos dentro da sessao |
| **Modelo menor (Haiku 4.5)** | -90% no inference | Tradeoff significativo em qualidade de raciocinio |
| **Reduzir MAX_RESULTS (5 para 3)** | -10-15% input tokens | Menor contexto RAG, pode afetar precisao |

---

## 8. Fontes Oficiais

- Amazon Bedrock Pricing: https://aws.amazon.com/bedrock/pricing/
- AWS Lambda Pricing: https://aws.amazon.com/lambda/pricing/
- AWS Glue Pricing: https://aws.amazon.com/glue/pricing/
- Amazon S3 Pricing: https://aws.amazon.com/s3/pricing/

---

*Documento gerado em 23/03/2026. Precos sujeitos a alteracao pela AWS. Consulte as paginas oficiais para valores atualizados.*
