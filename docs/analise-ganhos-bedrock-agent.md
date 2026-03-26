# Análise de Ganhos — RAG Bedrock Agent (Modelagem Dimensional)

**Data:** 26/03/2026
**Projeto:** Agente de Modelagem Dimensional com Amazon Bedrock
**Público-alvo:** Gestão / Diretoria

---

## 1. Resumo Executivo

| Métrica | Valor |
|---------|-------|
| **Tempo médio por modelo (manual)** | **~16h (2 dias úteis)** |
| **Tempo médio por modelo (com agente)** | **~3h** |
| **Redução de tempo** | **~81%** |
| **Custo/hora engenheiro de dados (Brasil)** | **R$ 102/h** |
| **Economia por modelo dimensional** | **R$ 1.326** |
| **Custo do agente por sessão** | **R$ 2,70 (~$0,47)** |
| **ROI por modelo** | **491:1** |
| **Payback do investimento inicial** | **< 1 dia útil** |

> O agente reduz em **81% o tempo** de criação de modelos dimensionais, gerando uma economia de **R$ 1.326 por modelo**. Para cada R$ 1 investido no agente, o retorno é de **R$ 491** em produtividade.

---

## 2. Baseline: Processo Manual de Modelagem Dimensional

Tempo estimado para um engenheiro de dados criar um modelo dimensional de complexidade média (3-5 tabelas fato, 5-8 dimensões) **sem o agente**:

| # | Etapa | Descrição | Tempo Estimado |
|---|-------|-----------|----------------|
| 1 | Levantamento de KPIs | Reuniões com stakeholders para definir indicadores, fórmulas de cálculo, granularidade e requisitos históricos | 2-4h |
| 2 | Pesquisa de melhores práticas | Consultar literatura sobre modelagem dimensional (SCD, aggregates, conformed dimensions, Kimball vs. Inmon) | 1-2h |
| 3 | Inspeção de schemas silver | Explorar catálogo de dados, entender colunas, tipos, relações entre tabelas, volumes | 2-3h |
| 4 | Design do modelo dimensional | Definir grain, identificar fatos e dimensões, decidir tipos de SCD, planejar tabelas agregadas | 3-4h |
| 5 | Escrita de DDL | Criar SQL DDL para todas as tabelas com constraints, comentários, convenções de nomenclatura | 2-3h |
| 6 | Escrita de ETL SQL | Criar queries de carga silver → gold para cada tabela, com JOINs, tratamento de NULLs, surrogate keys | 2-3h |
| 7 | Revisão e ajustes | Code review com pares, validação de aderência a convenções, correções | 2-3h |
| | **Total** | | **14-22h (média ~16h)** |

---

## 3. Com o Agente: Processo Acelerado

| # | Etapa | Manual | Com Agente | Redução | Como o Agente Acelera |
|---|-------|--------|------------|---------|----------------------|
| 1 | Levantamento de KPIs | 2-4h | 1-2h | 50% | Conduz entrevista estruturada, sugere indicadores relevantes ao domínio |
| 2 | Pesquisa de práticas | 1-2h | ~0h | ~100% | Conhecimento do livro-referência integrado via RAG, com citações automáticas |
| 3 | Inspeção de schemas | 2-3h | ~5min | ~97% | Consulta automática ao Glue Data Catalog (list_databases, list_tables, get_table_schema) |
| 4 | Design do modelo | 3-4h | ~10min | ~95% | Aplica princípios de grain, conformed dimensions, SCD e aggregates automaticamente |
| 5 | Escrita de DDL | 2-3h | ~5min | ~97% | Geração automática com convenções (Iceberg, surrogate keys, SCD Type 2, comments) |
| 6 | Escrita de ETL SQL | 2-3h | ~5min | ~97% | Geração automática com JOINs, tratamento de NULLs, persistência no S3 |
| 7 | Revisão e ajustes | 2-3h | 1-2h | ~40% | Modelo já segue best practices; revisão humana ainda necessária, porém mais rápida |
| | **Total** | **~16h** | **~3h** | **~81%** | |

> **Destaque:** As etapas 3 a 6 (inspeção, design, DDL e ETL) passam de **~10h manuais para ~25 minutos** com o agente. Esse é o núcleo da aceleração.

---

## 4. Ganhos Quantificados

### 4.1 Economia de Tempo

| Métrica | Valor |
|---------|-------|
| Tempo poupado por modelo | ~13h |
| Modelos por mês (equipe média, 3 engenheiros) | 8-12 |
| **Horas poupadas por mês** | **104-156h** |

### 4.2 Economia Financeira por Modelo

| Item | Cálculo | Valor |
|------|---------|-------|
| Custo do engenheiro (tempo poupado) | 13h × R$ 102/h | R$ 1.326 |
| Custo do agente (1 sessão) | $0,47 × R$ 5,75 | R$ 2,70 |
| **Economia líquida por modelo** | R$ 1.326 − R$ 2,70 | **R$ 1.323** |

### 4.3 Aumento de Throughput

| Cenário | Sem Agente | Com Agente | Multiplicador |
|---------|------------|------------|---------------|
| Modelos/semana (1 engenheiro) | 2 | 8-10 | **4-5×** |
| Modelos/mês (equipe de 3) | 24 | 96-120 | **4-5×** |

### 4.4 Ganhos de Qualidade

| Aspecto | Sem Agente | Com Agente |
|---------|------------|------------|
| Aderência a convenções (Iceberg, SCD, surrogate keys) | Varia por pessoa | 100% consistente |
| Fundamentação teórica | Depende da experiência individual | Automática (RAG sobre Adamson) |
| Completude (aggregates, conformed dims) | Frequentemente esquecido | Sistemático |
| Documentação inline (comments no DDL) | Opcional, frequentemente omitida | Sempre presente |
| Scripts SQL persistidos | Manual, muitas vezes perdidos | Automático no S3 |

---

## 5. Cálculo de ROI

### 5.1 ROI por Modelo Individual

| Item | Valor |
|------|-------|
| Investimento (custo do agente) | R$ 2,70 |
| Retorno (economia de tempo) | R$ 1.326 |
| **ROI** | **491:1 (~49.100%)** |

### 5.2 ROI Mensal por Cenário

| Cenário | Modelos/mês | Economia de tempo | Economia R$/mês | Custo agente/mês | **ROI** |
|---------|-------------|-------------------|-----------------|-------------------|---------|
| **Baixo** — 1 engenheiro, uso esporádico | 10 | 130h | R$ 13.260 | R$ 27 | 491:1 |
| **Médio** — equipe pequena, uso regular | 40 | 520h | R$ 53.040 | R$ 108 | 491:1 |
| **Alto** — múltiplas equipes | 100 | 1.300h | R$ 132.600 | R$ 270 | 491:1 |
| **Enterprise** — produção em escala | 200 | 2.600h | R$ 265.200 | R$ 540 | 491:1 |

### 5.3 Payback Period

| Item | Valor |
|------|-------|
| Investimento inicial (deploy + configuração + ingestão KB) | ~8h de engenheiro = R$ 816 |
| Economia do 1º modelo dimensional completo | R$ 1.323 |
| **Payback** | **< 1 dia útil** |

---

## 6. Benefícios Qualitativos

### 6.1 Democratização do conhecimento
Engenheiros juniores conseguem produzir modelos dimensionais com qualidade de nível senior. O agente funciona como um consultor especializado sempre disponível, com o conhecimento do livro-referência integrado.

### 6.2 Consistência entre projetos
Todos os modelos seguem as mesmas convenções (Apache Iceberg, SCD Type 2, surrogate keys, nomenclatura de aggregates). Elimina divergência entre equipes e projetos.

### 6.3 Redução de dependência de arquitetos senior
O gargalo em equipes de dados é frequentemente a disponibilidade do arquiteto. O agente reduz essa dependência: o arquiteto passa de **executor** para **revisor**, liberando capacidade para trabalho estratégico.

### 6.4 Aceleração de onboarding
Novos membros aprendem modelagem dimensional interagindo com o agente, que explica decisões de design com fundamentação teórica. Reduz o tempo de ramp-up de novos engenheiros.

### 6.5 Documentação automática
Todo modelo gerado inclui DDL comentado, mapeamento indicador → tabela, e scripts SQL persistidos no S3. Reduz a dívida técnica de documentação sem esforço adicional.

### 6.6 Rastreabilidade KPI → Modelo
O workflow orientado a KPIs garante que cada tabela tenha justificativa de negócio explícita. Elimina tabelas órfãs e facilita auditorias.

---

## 7. Cenários Comparativos — Visão Consolidada

| Cenário | Modelos/mês | Horas poupadas/mês | Economia bruta/mês | Custo agente/mês | Economia líquida/mês | ROI |
|---------|-------------|---------------------|---------------------|-------------------|-----------------------|-----|
| Baixo | 10 | 130h | R$ 13.260 | R$ 27 | R$ 13.233 | 491:1 |
| Médio | 40 | 520h | R$ 53.040 | R$ 108 | R$ 52.932 | 491:1 |
| Alto | 100 | 1.300h | R$ 132.600 | R$ 270 | R$ 132.330 | 491:1 |
| Enterprise | 200 | 2.600h | R$ 265.200 | R$ 540 | R$ 264.660 | 491:1 |

---

## 8. Premissas e Limitações

| Premissa | Valor / Descrição |
|----------|-------------------|
| Salário base engenheiro de dados (CLT) | R$ 10.000/mês |
| Custo empresa (encargos ~80%) | ~R$ 18.000/mês |
| Custo/hora efetivo | ~R$ 102/h (176h úteis/mês) |
| Câmbio USD/BRL | R$ 5,75 (referência março/2026) |
| Complexidade de referência | Modelo médio: 3-5 tabelas fato, 5-8 dimensões |
| Custo por sessão do agente | $0,47 (~R$ 2,70) — detalhado em `estimativa-custo-bedrock-agent.md` |

**Limitações:**
- O agente **não substitui** a revisão humana; os tempos de revisão (1-2h) são mantidos em todas as estimativas
- Modelos muito complexos (20+ tabelas, múltiplos star schemas interligados) podem exigir múltiplas sessões
- A qualidade do output depende da qualidade dos metadados no Glue Data Catalog
- Tempos manuais baseados em referências de mercado para complexidade média; projetos simples ou muito complexos podem divergir

---

## 9. Fontes

- Estimativa de custo do projeto: `estimativa-custo-bedrock-agent.md`
- Preços Amazon Bedrock: https://aws.amazon.com/bedrock/pricing/
- Referência salarial: Glassdoor / Robert Half Guia Salarial 2025-2026

---

*Documento gerado em 26/03/2026. Valores sujeitos a variação conforme câmbio, preços AWS e mercado de trabalho.*
