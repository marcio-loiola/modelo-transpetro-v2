# 🚢 Modelo de Predição de Biofouling - Transpetro v2

## 📋 Visão Geral

Este projeto implementa um **modelo de Machine Learning (XGBoost)** para predição do impacto de **biofouling** (incrustação biológica) no consumo de combustível de navios da frota Transpetro.

O biofouling é o acúmulo de organismos marinhos no casco dos navios, causando aumento da resistência ao avanço e, consequentemente, maior consumo de combustível e emissões de CO₂.

---

## 🔬 Detalhes Técnicos do Modelo

## 📁 Estrutura do Projeto

```
├── api/                          # Backend FastAPI
│   ├── main.py                   # Entrada ASGI
│   ├── config.py                 # Parâmetros e env vars
│   ├── database.py               # Helpers SQLite e persistência local
│   ├── schemas.py                # Modelos Pydantic usados nas rotas
│   ├── services.py               # Serviços ML, reports e integrações
│   ├── external_clients.py       # Clientes HTTP para terceiros
│   ├── integration_service.py    # Orquestração das APIs internas
│   └── routes/
│       ├── predictions.py        # Pré-existentes `/api/v1/...`
│       ├── ships.py              # Endpoints de navios e frota
│       ├── reports.py            # Relatórios compilados
│       ├── integrations.py       # Health checks e integrações
│       └── operational.py        # Novos endpoints de operação e cache
├── src/                          # Helpers de ciência de dados e clientes
│   ├── pipeline/                 # Cálculo de features, hidrodinâmica e predição
│   │   ├── baseline.py           # Consumo baseline (Admiralty)
│   │   ├── feature_engineering.py# Transforms de idle/risk
│   │   ├── hydrodynamics.py      # Reynolds, fricção e ΔR
│   │   ├── impact.py             # Custos adicionais e CO₂
│   │   └── prediction.py         # Orquestração final antes do modelo
│   ├── clients/                  # Clientes HTTP externos
│   │   └── ocean_api.py           # Cliente async para a Ocean API
│   ├── models/                   # Serialização de modelos de teste
│   │   └── stub.py                # Build / save / load de modelos stub
   │   ├── script.py                 # Treino principal (662 linhas)
   │   ├── analise_relatorio.py      # Análise auxiliar de relatórios
   │   └── validacao_cientifica.py   # Validação estatística
├── data/                         # Dados que alimentam o pipeline
│   ├── raw/                      # Dados brutos do Hackathon
│   ├── processed/                # Relatórios gerados (CSV/MD)
│   └── database/                 # Banco SQLite usado nos testes
│       └── biofouling.db
├── models/                       # Artefatos treinados
│   ├── modelo_final_v13.pkl
│   └── encoder_final_v13.pkl
├── config/                       # Arquivos de configuração (JSON/ambientes)
├── reports/                      # Resumos em Markdown ou TXT
├── docs/                         # Documentação (ex.: MICROSERVICES_ARCHITECTURE.md)
├── run_api.py                    # Executa o FastAPI localmente
├── init_database.py              # Inicializa o banco SQLite
├── run_tests.py                  # Roda `pytest` com convenções próprias
├── test_api.py                   # Testes rápidos da API
├── test_api_complete.py          # Suite completa de testes da API
├── README.md                     # Documentação principal
├── README_BACKEND.md             # Documentação específica do backend
├── requirements.txt              # Dependências Python
└── model_version.json            # Versão + hash do modelo em uso
```

+│ └── routes/
│ ├── predictions.py # Endpoints padrão de predição
│ ├── ships.py # Informações da frota
│ ├── reports.py # Relatórios compilados
│ ├── integrations.py # Heath checks e integrações
│ └── operational.py # Biofouling / vessel / ocean env
├── src/ # Cálculos de modelo, clientes e helpers
│ ├── pipeline/ # Pipeline physics + ML helpers
│ │ ├── baseline.py # Admiralty baseline e eficiência
+│ │ ├── feature_engineering.py# Idle-/risk-based feature transforms
│ │ ├── hydrodynamics.py # Reynolds e fricção
│ │ ├── impact.py # Custos e emissões adicionais
│ │ └── prediction.py # Orquestração final antes do modelo
│ ├── clients/ # Assistentes HTTP para serviços externos
│ │ └── ocean_api.py # Cliente assíncrono usado no cache
│ ├── models/ # Helpers de serialização de modelos
│ │ └── stub.py # Build / save / load de modelos de teste
│ ├── script.py # Script principal de treino (662 linhas)
+│ ├── analise_relatorio.py # Análise auxiliar dos relatórios
│ └── validacao_cientifica.py # Validação estatística
├── data/ # Dados de entrada e bancos
│ ├── raw/ # Dados brutos do Hackathon
│ ├── processed/ # Outputs e resumos (CSV/MD)
│ └── database/ # SQLite usado nos testes
│ └── biofouling.db
├── models/ # Modelos e encoders serializados
│ ├── modelo_final_v13.pkl
│ └── encoder_final_v13.pkl
├── config/ # Configurações de biofouling e ambientes
├── reports/ # Resumos em Markdown/TXT
├── docs/ # Documentação extra (ex.: MICROSERVICES_ARCHITECTURE.md)
├── run_api.py # Script para iniciar o FastAPI
├── init_database.py # Inicializa o banco SQLite local
├── run_tests.py # Execução rápida dos testes (pytest)
├── test_api.py # Smoke tests da API
├── test_api_complete.py # Testes end-to-end da API
├── README.md # Documentação principal
├── README_BACKEND.md # Documentação dedicada ao backend
├── requirements.txt # Lista de dependências Python
└── model_version.json # Metadata do modelo ativo

````

```python
# Merge assíncrono com tabela de docagens
days_since_cleaning = event_date - last_drydock_date
````

---

## ⚙️ Cálculo do Consumo Baseline (Física)

### Fórmula de Admiralty

```python
theoretical_power = (displacement^(2/3) × speed^3) / 10000
baseline_consumption = theoretical_power × duration × efficiency_factor
```

### Calibração do Fator de Eficiência

```python
# Usando dados de navios "limpos" (< 90 dias desde docagem)
if CALIBRATE_PER_SHIP:
    efficiency_factor = median(consumption / (power × duration)) per ship
else:
    efficiency_factor = global_median
```

| Configuração                 | Valor     |
| ---------------------------- | --------- |
| `ADMIRALTY_SCALE_FACTOR`     | 10,000    |
| `CALIBRATE_PER_SHIP`         | True      |
| Dias para considerar "limpo" | < 90 dias |

---

## 📊 Cálculo do Índice de Biofouling

### Função Sigmoid (Escala 0-1)

```python
bio_index = 1 / (1 + exp(-k × (excess_ratio - midpoint)))
```

| Parâmetro           | Valor    | Descrição                    |
| ------------------- | -------- | ---------------------------- |
| `SIGMOID_K`         | **10**   | Inclinação da curva          |
| `SIGMOID_MIDPOINT`  | **0.10** | Ponto em que bio_index = 0.5 |
| `USE_SIGMOID_SCALE` | True     | Usar sigmoid vs linear       |

### Escala Final (0-10)

```python
bio_index_0_10 = bio_index × 10  # Arredondado para 1 casa decimal
```

### Classificação Qualitativa

| Excess Ratio | Classificação |
| ------------ | ------------- |
| < 10%        | 🟢 Leve       |
| 10% - 20%    | 🟡 Moderada   |
| ≥ 20%        | 🔴 Severa     |

---

## 💰 Estimativas de Custo e Emissões

### Parâmetros de Custo

| Parâmetro                | Valor     | Unidade              |
| ------------------------ | --------- | -------------------- |
| `FUEL_PRICE_USD_PER_TON` | **500**   | USD/ton              |
| `CO2_TON_PER_FUEL_TON`   | **3.114** | tCO₂/ton combustível |

│ ├── models/ # Helpers de serialização de modelos stub
│ │ └── stub.py # Build / save / load
│ ├── script.py # Treino principal (662 linhas)
│ ├── analise_relatorio.py # Análises auxiliares de relatórios
│ └── validacao_cientifica.py # Validação científica e estatística
├── data/ # Dados que alimentam o pipeline
│ ├── raw/ # Dados brutos recebidos
│ ├── processed/ # Relatórios e outputs gerados
│ └── database/ # SQLite com corpus de teste
│ └── biofouling.db
├── models/ # Artefatos treinados
│ ├── modelo_final_v13.pkl
│ └── encoder_final_v13.pkl
├── config/ # Arquivos de configuração JSON e templates
├── reports/ # Resumos Markdown/TXT
├── docs/ # Documentação extra (ex.: MICROSERVICES_ARCHITECTURE.md)
├── run_api.py # Inicia o FastAPI localmente
├── init_database.py # Inicializa o banco SQLite
├── run_tests.py # Script auxiliar para rodar pytest
├── test_api.py # Smoke tests da API
├── test_api_complete.py # Suite completa de testes da API
├── README.md # Documentação principal do projeto
├── README_BACKEND.md # Documentação dedicada ao backend
├── requirements.txt # Lista de dependências Python
└── model_version.json # Versão e hash SHA do modelo em produção

````

| **RMSE** | √(Σ(real - pred)² / n) | Erro quadrático médio |
| **MAE** | Σ\|real - pred\| / n | Erro absoluto médio |
| **WMAPE** | Σ\|real - pred\| / Σreal | Erro percentual ponderado |
| **Accuracy** | 100 × (1 - WMAPE) | Acurácia geral |

### Sanity Check (Validação de Impacto)

```python
# Compara predição para navio limpo vs sujo
Cenário Limpo:  days_since_cleaning = 30
Cenário Sujo:   days_since_cleaning = 400

Biofouling Penalty = fuel_dirty - fuel_clean
````

---

## 📤 Saídas do Modelo

### 1. Relatório Detalhado (`biofouling_report.csv`)

| Coluna               | Descrição                            |
| -------------------- | ------------------------------------ |
| shipName             | Nome do navio                        |
| startGMTDate         | Data do evento                       |
| sessionId            | ID da sessão                         |
| CONSUMED_QUANTITY    | Consumo real (tons)                  |
| baseline_consumption | Consumo esperado (tons)              |
| target_excess_ratio  | Excesso percentual                   |
| bio_index_0_10       | Índice de biofouling (0-10)          |
| bio_class            | Classificação (Leve/Moderada/Severa) |
| additional_fuel_tons | Combustível adicional                |
| additional_cost_usd  | Custo adicional (USD)                |
| additional_co2_tons  | CO₂ adicional (tons)                 |

### 2. Resumo por Navio (`biofouling_summary_by_ship.csv`)

| Coluna                    | Descrição                  |
| ------------------------- | -------------------------- |
| shipName                  | Nome do navio              |
| avg_excess_ratio          | Média do excesso           |
| max_excess_ratio          | Máximo excesso             |
| num_events                | Número de eventos          |
| avg_bio_index             | Índice médio               |
| max_bio_index             | Índice máximo              |
| total_baseline_fuel       | Total combustível baseline |
| total_real_fuel           | Total combustível real     |
| total_additional_fuel     | Total combustível extra    |
| total_additional_cost_usd | Custo total extra          |
| total_additional_co2      | CO₂ total extra            |

### 3. Modelos Serializados

| Arquivo                 | Descrição                       |
| ----------------------- | ------------------------------- |
| `modelo_final_v13.pkl`  | Modelo XGBoost treinado         |
| `encoder_final_v13.pkl` | LabelEncoder para tipo de tinta |

---

## 🌐 Backend FastAPI (Microserviço)

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Biofouling Service    │ ← Este microserviço
              │       (FastAPI)         │
              └────────────┬────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
┌────▼────┐         ┌──────▼──────┐       ┌──────▼──────┐
│ Weather │         │   Vessel    │       │    Fuel     │
│   API   │         │  Tracking   │       │   Prices    │
└─────────┘         └─────────────┘       └─────────────┘
```

### Endpoints Principais

| Método | Endpoint                       | Descrição                |
| ------ | ------------------------------ | ------------------------ |
| POST   | `/api/v1/predictions/`         | Predição única           |
| POST   | `/api/v1/predictions/batch`    | Predições em lote        |
| POST   | `/api/v1/predictions/scenario` | Comparação limpo vs sujo |
| GET    | `/api/v1/ships/`               | Lista navios             |
| GET    | `/api/v1/ships/fleet/summary`  | Resumo da frota          |
| GET    | `/api/v1/reports/biofouling`   | Relatório completo       |
| GET    | `/api/v1/reports/high-risk`    | Navios alto risco        |
| GET    | `/api/v1/integrations/health`  | Status das integrações   |

### Integrações Externas (Configuráveis)

- **Weather API**: Condições marítimas em tempo real
- **Vessel Tracking**: Posições AIS
- **Fuel Prices**: Preços de bunker atualizados
- **Maintenance API**: Histórico de docagens
- **Emissions API**: Reporting IMO DCS/EU MRV

---

## 🧠 Hidrodinâmica embarcada

O pipeline agora amplia a engenharia de features com o módulo `src/hydrodynamics.py`, que calcula:

- **Reynolds number** a partir de densidade, velocidade e comprimento entregues pelo evento.
- **Coeficiente de fricção (CF)** usando a aproximação de Prandtl-Schlichting.
- **ΔR** como aumento de fricção comparado ao casco limpo (clean_friction) e **power penalty** proporcional a `ΔR × velocidade`.

Todas essas saídas entram como features adicionais no modelo XGBoost e são reportadas junto de `bio_index_0_10` no retorno da API, facilitando a interpretação técnica dos impactos hidrodinâmicos.

## 🔌 Superfície de API estendida

A FastAPI continua sendo o backend principal, as rotas seguem o novo contrato técnico e estão implementadas no serviço (`api/routes/operational.py`):

- `POST /prediction/biofouling` → predição individual com dados operacionais + ambientais.
- `POST /prediction/biofouling/batch` → inferência em lote sobre eventos sequenciais.
- `POST /vessel/data` → ingestão ou atualização de metadados do navio (draft, tipo de casco, paint type, docagem).
- `GET /ocean/env` → retorna o cache ambiental recente (temperatura, salinidade, densidade, correntes) usado no pipeline.

Esses endpoints coexistem com `/api/v1/predictions` e `/api/v1/ships`, porém os novos contratos colocam o foco em integração direta com sistemas operacionais e de monitoração. A documentação OpenAPI 3.0 do FastAPI expõe automaticamente os 4 novos caminhos.

## 🌊 Inferência contínua e cache ambiental

Uma tarefa executada em background (BackgroundTask ou scheduler) atualiza a cada 15 minutos o cache da Ocean API. O FastAPI inicializa o cache via `api/ocean_cache.py`, os dados são agregados em janelas de 24h/48h/7d antes de entrarem no pipeline e lat/lon são convertidos para zonas climáticas com representação `sin/cos` + one-hot. Os valores frescos são mantidos em memória (ou Redis em produção) e liberados via `/ocean/env`.

Essa rotina preenche gaps da API, garante latência constante (<220 ms) e dispara inferências com `model_version.json` (hash SHA-256) gravado no disco para rastreabilidade. Sempre que o modelo for retreinado (mensalmente), atualize o hash e registre o novo digest no JSON para que a API retorne `{ "model_version": "v1.0.0", "hash": "<sha>" }` em cada resposta.

## 📦 Versionamento e artefatos

- `model_version.json` descreve a versão, o caminho do artefato (`models/modelo_final_v13.pkl`) e o hash SHA-256.
- O cache ambiental respeita os env vars `OCEAN_CACHE_TTL_SECONDS` e `OCEAN_CACHE_MAX_STALE_SECONDS`, documentados abaixo.
- Use o hash SHA para decidir se há nova versão, mantendo o rollout simples em FastAPI/Flask/BentoML.

## 📁 Estrutura do Projeto

```
├── api/                          # Backend FastAPI
│   ├── main.py                   # Entrada ASGI
│   ├── config.py                 # Parâmetros e env vars
│   ├── database.py               # Helpers SQLite e persistência
│   ├── schemas.py                # Modelos Pydantic compartilhados
│   ├── services.py               # Serviços de negócio e ML
│   ├── external_clients.py       # Clientes HTTP para terceiros
│   ├── integration_service.py    # Orquestração das chamadas internas
│   └── routes/
│       ├── predictions.py        # `/api/v1/predictions/` e endpoints similares
│       ├── ships.py              # Informações da frota
│       ├── reports.py            # Relatórios e resumos
│       ├── integrations.py       # Health checks e integrações
│       └── operational.py        # Novos endpoints de operação
├── src/                          # Helpers de ciência de dados, clients e stubs
│   ├── pipeline/                 # Cálculo de features e orquestração de predição
│   │   ├── baseline.py           # Admiralty baseline e eficiência
│   │   ├── feature_engineering.py# Transformações idle/risk
│   │   ├── hydrodynamics.py      # Reynolds, CF e ΔR
│   │   ├── impact.py             # Custos e CO₂
│   │   └── prediction.py         # Orquestração final antes do modelo
│   ├── clients/                  # Clientes HTTP externos
│   │   └── ocean_api.py           # Assistente assíncrono usado pelo cache
│   ├── models/                   # Serialização de modelos stub
│   │   └── stub.py                # Build / save / load
│   ├── script.py                 # Script principal de treino
│   ├── analise_relatorio.py      # Análises auxiliar de relatórios
│   └── validacao_cientifica.py   # Validação estatística
├── data/                         # Dados que alimentam o pipeline
│   ├── raw/                      # Dados brutos recebidos
│   ├── processed/                # Outputs gerados (CSV/MD)
│   └── database/                 # SQLite para testes e demos
│       └── biofouling.db
├── models/                       # Artefatos treinados
│   ├── modelo_final_v13.pkl
│   └── encoder_final_v13.pkl
├── config/                       # Arquivos JSON e templates de configuração
├── reports/                      # Resumos e dashboards em Markdown/TXT
├── docs/                         # Documentação adicional (ex.: MICROSERVICES_ARCHITECTURE.md)
├── run_api.py                    # Inicia o FastAPI localmente
├── init_database.py              # Cria o banco SQLite
├── run_tests.py                  # Wrapper para executar `pytest`
├── test_api.py                   # Smoke tests da API
├── test_api_complete.py          # Suite completa de testes da API
├── README.md                     # Documentação principal
├── README_BACKEND.md             # Documentação do backend
├── requirements.txt              # Dependências Python
└── model_version.json            # Versão e hash SHA do modelo ativo
```

````

## 🧠 Camada `src` (orientação para a equipe de dados)

1. **`src/pipeline/`** concentra todos os cálculos físicos e a orquestração de features. Cada módulo traz docstrings detalhando fórmulas (baseline, índice, impacto, hidrodinâmica) e um `/prediction.py` que junta tudo antes de chamar `model.predict`.
2. **`src/clients/`** guarda wrappers assíncronos para APIs externas (começando pela Ocean API). Consulte `ocean_api.py` para saber como montar as chamadas e quais chaves são esperadas.
3. **`src/models/`** oferece helpers para instanciar, salvar e carregar o modelo de referência (`stub.py`). Use essa camada para centralizar rotas de versionamento ou fines de teste antes de puxar o artefato real em `models/modelo_final_v13.pkl`.

Essa organização deixa claro onde ajustar features e onde documentar experimentos; qualquer dúvida sobre um helper específico pode ser resolvida abrindo o arquivo relevante, que já descreve o que faz cada função.

---

## 🚀 Instalação e Execução

### Requisitos

- Python 3.8+
- ~2GB RAM para treinamento
- ~500MB para inferência

### Instalação

```bash
git clone <repository-url>
cd modelo-transpetro-v2
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
````

### Treinar Modelo

```bash
python src/script.py
```

### Iniciar API

```bash
python run_api.py
# ou
uvicorn api.main:app --reload --port 8000
```

---

## 📊 Dependências

| Pacote       | Versão | Uso                      |
| ------------ | ------ | ------------------------ |
| pandas       | ≥1.5   | Manipulação de dados     |
| numpy        | ≥1.24  | Computação numérica      |
| xgboost      | ≥1.7   | Modelo ML                |
| scikit-learn | ≥1.2   | Métricas e preprocessing |
| matplotlib   | ≥3.6   | Visualizações            |
| joblib       | ≥1.2   | Serialização de modelos  |
| openpyxl     | ≥3.1   | Leitura de Excel         |
| fastapi      | ≥0.109 | Framework web            |
| uvicorn      | ≥0.27  | Servidor ASGI            |
| pydantic     | ≥2.5   | Validação de dados       |
| httpx        | ≥0.27  | Cliente HTTP async       |

## <<<<<<< HEAD

## 🔄 Comparativo para Análise

=======

- **API**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **Documentação ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

> 📖 **Para detalhes completos sobre o backend e seus endpoints, consulte**: [README_BACKEND.md](README_BACKEND.md)

## 🔌 API Endpoints Principais

> > > > > > > origin/maikon

### Resumo Técnico para Comparação

| Aspecto               | Este Modelo                        |
| --------------------- | ---------------------------------- |
| **Algoritmo**         | XGBoost Regressor                  |
| **Target**            | Excess Ratio (consumo adicional %) |
| **Features**          | 8 (5 numéricas + 3 derivadas)      |
| **Baseline**          | Fórmula de Admiralty calibrada     |
| **Índice Biofouling** | Sigmoid (0-1) → escala 0-10        |
| **Split**             | 80/20 cronológico                  |
| **Regularização**     | L1 (α=1.0) + L2 (λ=2.0)            |
| **Early Stopping**    | Sim (30 rounds)                    |
| **Calibração**        | Per-ship efficiency factor         |
| **Custos**            | USD 500/ton combustível            |
| **Emissões**          | 3.114 tCO₂/ton combustível         |

## <<<<<<< HEAD

=======

### Navios

| Método | Endpoint                            | Descrição                     |
| ------ | ----------------------------------- | ----------------------------- |
| GET    | `/api/v1/ships/`                    | Lista todos os navios         |
| GET    | `/api/v1/ships/{ship_name}`         | Detalhes de um navio          |
| GET    | `/api/v1/ships/{ship_name}/summary` | Resumo de biofouling do navio |
| GET    | `/api/v1/ships/fleet/summary`       | Resumo da frota completa      |

### Relatórios

| Método | Endpoint                            | Descrição                           |
| ------ | ----------------------------------- | ----------------------------------- |
| GET    | `/api/v1/reports/biofouling`        | Relatório de biofouling com filtros |
| GET    | `/api/v1/reports/biofouling/export` | Exportar relatório em CSV           |
| GET    | `/api/v1/reports/statistics`        | Estatísticas gerais                 |
| GET    | `/api/v1/reports/high-risk`         | Navios com alto risco de biofouling |

### Exemplo de Requisição

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/" \
  -H "Content-Type: application/json" \
  -d '{
    "ship_name": "NAVIO EXEMPLO",
    "speed": 12.5,
    "duration": 24.0,
    "days_since_cleaning": 180,
    "displacement": 50000,
    "beaufort_scale": 3
  }'
```

### Exemplo de Resposta

```json
{
  "ship_name": "NAVIO EXEMPLO",
  "status": "success",
  "predicted_consumption": 45.23,
  "baseline_consumption": 42.1,
  "excess_ratio": 0.0743,
  "bio_index": 4.2,
  "bio_class": "Leve",
  "additional_fuel_tons": 3.13,
  "additional_cost_usd": 1565.0,
  "additional_co2_tons": 9.75,
  "model_version": "v13"
}
```

## 🧪 Testes

Execute os testes completos da API:

```bash
# Testes básicos
python test_api_complete.py

# Com APIs externas
python test_api_complete.py --external

# Modo verboso
python test_api_complete.py --verbose
```

## 🗄️ Banco de Dados

O projeto utiliza SQLite para armazenar predições e relatórios:

- **Localização**: `data/database/biofouling.db`
- **Inicialização**: Automática na primeira execução da API
- **Inicialização manual**: `python init_database.py`

O banco de dados funciona como fallback quando os arquivos CSV não estão disponíveis.

## 📊 Parâmetros do Algoritmo

O modelo utiliza diversos parâmetros configuráveis na classe `Config`:

| Categoria           | Parâmetro                | Descrição                                                |
| ------------------- | ------------------------ | -------------------------------------------------------- |
| Feature Engineering | `IDLE_SPEED_THRESHOLD`   | Velocidade limite para considerar navio parado (5.0 nós) |
| Feature Engineering | `ROLLING_WINDOW_DAYS`    | Janela de média móvel (30 dias)                          |
| Modelo              | `n_estimators`           | Número de árvores XGBoost (300)                          |
| Modelo              | `learning_rate`          | Taxa de aprendizado (0.03)                               |
| Modelo              | `max_depth`              | Profundidade máxima das árvores (5)                      |
| Biofouling          | `SIGMOID_MIDPOINT`       | Ponto médio da curva sigmoid (10%)                       |
| Custos              | `FUEL_PRICE_USD_PER_TON` | Preço do combustível (500 USD/ton)                       |

## 📈 Métricas de Performance

O modelo é avaliado usando:

- **RMSE** - Root Mean Square Error
- **MAE** - Mean Absolute Error
- **WMAPE** - Weighted Mean Absolute Percentage Error
- **Accuracy** - Acurácia geral do modelo

## 📝 Saídas

1. **biofouling_report.csv** - Relatório detalhado por evento

   - Índice de biofouling (0-10)
   - Classificação (Leve, Moderada, Severa)
   - Custo adicional estimado
   - Emissões extras de CO₂

2. **biofouling_summary_by_ship.csv** - Resumo agregado por navio
   - Média e máximo do índice de biofouling
   - Total de combustível adicional
   - Custo total e emissões totais
     > > > > > > > origin/maikon

## 📚 Documentação Adicional

- **[README_BACKEND.md](README_BACKEND.md)** - Documentação completa do backend API
- **[TEST_README.md](TEST_README.md)** - Guia de testes
- **[CORRECOES_ERROS.md](CORRECOES_ERROS.md)** - Correções implementadas

## 👥 Autor

**Marcio Loiola** - [GitHub](https://github.com/marcio-loiola)

## 📄 Licença

Desenvolvido para o **Hackathon Transpetro 2024**.
