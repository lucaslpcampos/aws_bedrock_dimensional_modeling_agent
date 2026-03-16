# Dimensional Modeling RAG Agent

Agente de IA especializado em modelagem dimensional e design de data warehouse, alimentado por RAG (Retrieval-Augmented Generation) com o livro *"Star Schema: The Complete Reference"* de Christopher Adamson.

O agente inspeciona schemas do AWS Glue Data Catalog (camada silver) e propoe modelos dimensionais para a camada gold (DDL + ETL SQL), utilizando uma abordagem orientada a KPIs.

## Arquitetura

```
                    ┌─────────────────────────────────┐
                    │         Bedrock Agent            │
                    │   (Claude Sonnet 4 - cross-region)│
                    └────────┬──────────┬──────────────┘
                             │          │
                    ┌────────▼──┐  ┌────▼─────────────┐
                    │ Knowledge │  │   Action Group    │
                    │   Base    │  │  (Lambda + Glue)  │
                    └────┬──────┘  └────┬──────────────┘
                         │              │
               ┌─────────▼──┐    ┌──────▼──────────┐
               │  S3 Vectors │    │  Glue Data      │
               │ (embeddings)│    │  Catalog         │
               └─────────────┘    └─────────────────┘
                         │
               ┌─────────▼──────┐
               │  S3 Documents  │
               │  (PDF + docs)  │
               └────────────────┘
```

A infraestrutura e composta por tres stacks CDK implantados em ordem de dependencia:

| Stack | Recursos | Descricao |
|-------|----------|-----------|
| **DimModelingStorage** | S3 Buckets + S3 Vectors | Armazena documentos fonte, scripts SQL gerados e indice vetorial (1024 dimensoes, cosine) |
| **DimModelingKB** | Bedrock Knowledge Base | KB com Titan Embeddings V2, chunking FIXED_SIZE (300 tokens, 30 overlap) |
| **DimModelingAgent** | Bedrock Agent + Lambda | Agente com Claude Sonnet 4 (cross-region), Lambda para acesso ao Glue Catalog e associacao a KB |

Os outputs do CloudFormation sao consumidos entre stacks: `source_bucket` -> KB, `knowledge_base_id` -> Agent.

## Funcionalidades do Agente

O agente opera com um workflow orientado a KPIs:

1. **Coleta de indicadores** - Solicita os KPIs/indicadores de negocio que o modelo dimensional deve suportar
2. **Clarificacao** - Valida definicao, formula de calculo, granularidade e necessidade de tendencias historicas
3. **Inspecao do catalogo** - Consulta o Glue Data Catalog para descobrir databases e schemas da camada silver
4. **Mapeamento** - Mapeia indicadores para elementos do modelo (fatos, dimensoes, granularidade)
5. **Proposta de modelo** - Gera DDL completo (tabelas fato base, agregadas e dimensoes) com SQL de carga
6. **Persistencia** - Salva scripts SQL no S3

### Action Group - Glue Catalog

O agente possui acesso read-only ao AWS Glue Data Catalog via Lambda:

| Funcao | Descricao |
|--------|-----------|
| `list_databases` | Lista todos os databases do Glue Data Catalog |
| `list_tables` | Lista tabelas de um database com nome, tipo e contagem de colunas |
| `get_table_schema` | Retorna schema completo (colunas, tipos, particoes, formato, SerDe) |
| `get_table_statistics` | Retorna estatisticas (row count, tamanho, estatisticas por coluna) |
| `save_sql_script` | Salva script SQL no S3 e retorna a URI |

## Pre-requisitos

- Python 3.11+
- AWS CLI configurado com credenciais validas
- AWS CDK CLI (`npm install -g aws-cdk`)
- Conta AWS com acesso ao Amazon Bedrock (regiao `us-east-1`)
- Acesso habilitado aos modelos:
  - **Amazon Titan Embeddings V2** (`amazon.titan-embed-text-v2:0`)
  - **Claude Sonnet 4** via cross-region inference profile

## Instalacao

1. Clone o repositorio:

```bash
git clone <repo-url>
cd aws
```

2. Crie e ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows
```

3. Instale as dependencias:

```bash
pip install -r rag-agent/requirements.txt
```

4. Coloque o PDF do livro *"Star Schema: The Complete Reference"* no diretorio `book/`.

5. (Opcional) Adicione documentos de contexto de negocio em `rag-agent/business_docs/`.

## Deploy

O deploy utiliza AWS CDK e implanta as tres stacks em ordem:

```bash
cd rag-agent
cdk bootstrap   # apenas na primeira vez
cdk deploy --all
```

Para implantar uma stack especifica:

```bash
cdk deploy DimModelingStorage
cdk deploy DimModelingKB
cdk deploy DimModelingAgent
```

Apos o deploy, inicie a ingestao dos documentos na Knowledge Base:

```bash
python scripts/start_ingestion_job.py [--profile PROFILE]
```

Acompanhe o status da ingestao:

```bash
python scripts/check_ingestion_status.py [--profile PROFILE]
```

## Uso

### Chat interativo com o agente

```bash
python rag-agent/scripts/demo_chat.py [--profile PROFILE] [--trace]
```

Opcoes:
- `--profile PROFILE` - Perfil AWS a utilizar
- `--trace` - Exibe os chunks recuperados da Knowledge Base

Comandos durante o chat:
- `/quit` - Encerra a sessao
- `/new` - Inicia uma nova sessao (limpa historico)
- `/kb <query>` - Consulta a Knowledge Base diretamente (sem passar pelo agente)

### Geracao de dados mock

O script `mock_data.py` gera dados ficticios de um sistema de consorcios para testes:

```bash
python mock_data.py
```

Gera CSVs com as seguintes entidades: leads, propostas, cotas, grupos, assembleias, pagamentos, lances e contemplacoes.

## Estrutura do Projeto

```
.
├── book/                          # PDF do livro (nao versionado)
├── data/                          # CSVs gerados pelo mock_data.py (nao versionado)
├── mock_data.py                   # Gerador de dados ficticios de consorcios
├── notebook_to_create_iceberg_table.ipynb  # Notebook para criar tabelas Iceberg
├── rag-agent/
│   ├── app.py                     # Entry point do CDK
│   ├── cdk.json                   # Configuracao do CDK
│   ├── requirements.txt           # Dependencias Python
│   ├── business_docs/             # Documentos de contexto de negocio
│   │   └── consorcio.txt          # Glossario do dominio de consorcios
│   ├── config/
│   │   └── settings.py            # Constantes centralizadas (modelos, nomes, chunking)
│   ├── lambda/
│   │   └── glue_catalog/
│   │       └── handler.py         # Lambda do Action Group (Glue Catalog + S3)
│   ├── prompts/
│   │   └── agent_instruction.txt  # System prompt do agente (workflow KPI-driven)
│   ├── scripts/
│   │   ├── demo_chat.py           # CLI interativo para testar o agente
│   │   ├── start_ingestion_job.py # Dispara ingestao de documentos na KB
│   │   └── check_ingestion_status.py  # Verifica status da ingestao
│   └── stacks/
│       ├── storage_stack.py       # S3 buckets + S3 Vectors
│       ├── knowledge_base_stack.py # Bedrock Knowledge Base
│       └── agent_stack.py         # Bedrock Agent + Lambda + Action Group
├── skills/                        # Skills do Claude Code
└── CLAUDE.md                      # Instrucoes para Claude Code
```

## Convencoes Tecnicas

- **SQL**: ANSI SQL, formato Apache Iceberg (`TBLPROPERTIES ('table_type'='ICEBERG')`)
- **Surrogate keys**: `BIGINT AUTO_INCREMENT` para dimensoes
- **SCD Type 2**: Colunas `effective_date`, `expiry_date`, `is_current`
- **Tabelas fato agregadas**: Nomeadas como `fact_<processo>_<granularidade>`, alimentadas a partir da tabela fato base (nao da camada silver)
- **IAM**: Privilegio minimo por componente; role do agente usa condicoes `SourceAccount`
- **Regiao**: `us-east-1` (requisito do Bedrock Agents)

## Dominio de Negocio

O projeto utiliza como caso de uso o dominio de **consorcios**, uma modalidade brasileira de aquisicao colaborativa de bens. As entidades principais sao:

| Entidade | Descricao |
|----------|-----------|
| **Leads** | Potenciais clientes captados por diferentes canais |
| **Grupos** | Grupos de consorcio com produto, prazo e valor de credito definidos |
| **Propostas** | Propostas comerciais vinculadas a leads e grupos |
| **Cotas** | Participacoes ativas no consorcio (originadas de propostas pagas) |
| **Assembleias** | Reunioes mensais onde ocorrem contemplacoes |
| **Pagamentos** | Parcelas pagas pelos cotistas |
| **Lances** | Ofertas para antecipar contemplacao (fixo ou livre) |
| **Contemplacoes** | Eventos de contemplacao por sorteio ou lance |

## Tecnologias

- **IaC**: AWS CDK (Python)
- **LLM**: Claude Sonnet 4 (cross-region inference)
- **Embeddings**: Amazon Titan Embeddings V2 (1024 dimensoes)
- **Vector Store**: Amazon S3 Vectors
- **Knowledge Base**: Amazon Bedrock Knowledge Bases
- **Agent**: Amazon Bedrock Agents
- **Data Catalog**: AWS Glue Data Catalog
- **Compute**: AWS Lambda (Python 3.12)
- **Storage**: Amazon S3

## Licenca

Projeto privado. Todos os direitos reservados.
