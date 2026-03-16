import random
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("pt_BR")

# -----------------------------
# CONFIG
# -----------------------------

NUM_LEADS = 2000
NUM_GRUPOS = 20
MESES_ASSEMBLEIA = 36

# -----------------------------
# LEADS
# -----------------------------

leads = []

for i in range(NUM_LEADS):

    data = fake.date_between("-3y", "today")

    leads.append({
        "lead_id": i+1,
        "nome": fake.name(),
        "cpf": fake.cpf(),
        "email": fake.email(),
        "telefone": fake.phone_number(),
        "data_lead": data,
        "canal": random.choice([
            "google ads",
            "facebook",
            "indicacao",
            "organico",
            "parceiro"
        ])
    })

df_leads = pd.DataFrame(leads)

# -----------------------------
# GRUPOS
# -----------------------------

grupos = []

for i in range(NUM_GRUPOS):

    prazo = random.choice([120, 150, 180])

    grupos.append({
        "grupo_id": i+1,
        "produto": random.choice(["imovel", "auto"]),
        "prazo_meses": prazo,
        "valor_credito": random.choice([
            80000,
            120000,
            200000,
            300000
        ]),
        "taxa_adm": random.choice([0.12,0.15,0.18])
    })

df_grupos = pd.DataFrame(grupos)

# -----------------------------
# PROPOSTAS
# -----------------------------

propostas = []

prop_id = 1

for _, lead in df_leads.iterrows():

    if random.random() < 0.65:

        paga = random.random() < 0.7

        propostas.append({
            "proposta_id": prop_id,
            "lead_id": lead["lead_id"],
            "grupo_id": random.randint(1, NUM_GRUPOS),
            "valor_credito": random.choice([
                80000,
                120000,
                200000,
                300000
            ]),
            "data_proposta": lead["data_lead"],
            "proposta_paga": paga,
            "data_pagamento": fake.date_between(lead["data_lead"], "today") if paga else None
        })

        prop_id += 1

df_propostas = pd.DataFrame(propostas)

# -----------------------------
# COTAS (somente propostas pagas)
# -----------------------------

cotas = []

cota_id = 1

for _, prop in df_propostas[df_propostas.proposta_paga == True].iterrows():

    cotas.append({
        "cota_id": cota_id,
        "proposta_id": prop["proposta_id"],
        "grupo_id": prop["grupo_id"],
        "data_ativacao": prop["data_pagamento"],
        "status": random.choices(
            ["ativa","cancelada","contemplada"],
            weights=[0.7,0.15,0.15]
        )[0]
    })

    cota_id += 1

df_cotas = pd.DataFrame(cotas)

# -----------------------------
# ASSEMBLEIAS
# -----------------------------

assembleias = []

ass_id = 1

for grupo in df_grupos.itertuples():

    data = datetime.now() - timedelta(days=MESES_ASSEMBLEIA*30)

    for m in range(MESES_ASSEMBLEIA):

        assembleias.append({
            "assembleia_id": ass_id,
            "grupo_id": grupo.grupo_id,
            "data_assembleia": data + timedelta(days=m*30)
        })

        ass_id += 1

df_assembleias = pd.DataFrame(assembleias)

# -----------------------------
# PAGAMENTOS
# -----------------------------

pagamentos = []

pag_id = 1

for cota in df_cotas.itertuples():

    parcelas = random.randint(3, 36)

    for p in range(parcelas):

        pagamentos.append({
            "pagamento_id": pag_id,
            "cota_id": cota.cota_id,
            "parcela": p+1,
            "valor_pago": random.randint(500,2000),
            "data_pagamento": fake.date_between(cota.data_ativacao,"today")
        })

        pag_id += 1

df_pagamentos = pd.DataFrame(pagamentos)

# -----------------------------
# LANCES
# -----------------------------

lances = []

lance_id = 1

for cota in df_cotas.sample(frac=0.35).itertuples():

    lances.append({
        "lance_id": lance_id,
        "cota_id": cota.cota_id,
        "assembleia_id": random.choice(df_assembleias.assembleia_id),
        "tipo_lance": random.choice(["fixo","livre"]),
        "valor_lance": random.randint(5000,50000)
    })

    lance_id += 1

df_lances = pd.DataFrame(lances)

# -----------------------------
# CONTEMPLAÇÕES
# -----------------------------

contemplacoes = []

cont_id = 1

for cota in df_cotas.sample(frac=0.2).itertuples():

    contemplacoes.append({
        "contemplacao_id": cont_id,
        "cota_id": cota.cota_id,
        "assembleia_id": random.choice(df_assembleias.assembleia_id),
        "tipo": random.choice(["sorteio","lance"]),
        "data_contemplacao": fake.date_between("-2y","today")
    })

    cont_id += 1

df_contemplacoes = pd.DataFrame(contemplacoes)

# -----------------------------
# EXPORT
# -----------------------------

df_leads.to_csv("leads.csv", index=False)
df_propostas.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/propostas.csv", index=False)
df_cotas.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/cotas.csv", index=False)
df_pagamentos.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/pagamentos.csv", index=False)
df_grupos.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/grupos.csv", index=False)
df_assembleias.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/assembleias.csv", index=False)
df_lances.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/lances.csv", index=False)
df_contemplacoes.to_csv(r"C:/Users/lucas/OneDrive/projetos/aws/data/contemplacoes.csv", index=False)

print("Dados mockados gerados!")