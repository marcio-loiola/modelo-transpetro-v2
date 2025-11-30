# 🚢 Modelo de Predição de Biofouling - Transpetro v2

## 📋 Visão Geral

Este projeto implementa um **modelo de Machine Learning (XGBoost)** para predição do impacto de **biofouling** (incrustação biológica) no consumo de combustível de navios da frota Transpetro.

O biofouling é o acúmulo de organismos marinhos no casco dos navios, causando aumento da resistência ao avanço e, consequentemente, maior consumo de combustível e emissões de CO₂.

---

## 🔬 Detalhes Técnicos do Modelo

### Algoritmo: XGBoost Regressor

| Parâmetro               | Valor              | Descrição                          |
| ----------------------- | ------------------ | ---------------------------------- |
| `objective`             | `reg:squarederror` | Regressão com erro quadrático      |
| `n_estimators`          | **300**            | Número de árvores no ensemble      |
| `learning_rate`         | **0.03**           | Taxa de aprendizado (conservadora) |
| `max_depth`             | **5**              | Profundidade máxima das árvores    |
| `min_child_weight`      | **10**             | Peso mínimo em nós folha           |
| `subsample`             | **0.8**            | Fração de amostras por árvore      |
| `colsample_bytree`      | **0.8**            | Fração de features por árvore      |
| `reg_alpha`             | **1.0**            | Regularização L1 (Lasso)           |
| `reg_lambda`            | **2.0**            | Regularização L2 (Ridge)           |
| `early_stopping_rounds` | **30**             | Parada antecipada                  |
| `random_state`          | **42**             | Reprodutibilidade                  |

### Variável Alvo (Target)

```
target_excess_ratio = (consumo_real - consumo_baseline) / consumo_baseline
```

- **Tipo**: Regressão contínua
- **Intervalo válido**: -0.5 a 1.0 (excesso de -50% a +100%)
- **Interpretação**: Percentual de consumo adicional devido ao biofouling

---

## 🧮 Features do Modelo

### Features Utilizadas (8 total)

| Feature                    | Tipo       | Descrição                     | Origem               |
| -------------------------- | ---------- | ----------------------------- | -------------------- |
| `speed`                    | Numérica   | Velocidade do navio (nós)     | Eventos AIS          |
| `beaufortScale`            | Numérica   | Escala de Beaufort (0-12)     | Dados meteorológicos |
| `days_since_cleaning`      | Numérica   | Dias desde última docagem     | Calculada            |
| `pct_idle_recent`          | Numérica   | % tempo parado (30 dias)      | Calculada            |
| `accumulated_fouling_risk` | Numérica   | Risco acumulado de fouling    | Calculada            |
| `historical_avg_speed`     | Numérica   | Média histórica de velocidade | Calculada            |
| `paint_x_speed`            | Numérica   | Interação tinta × velocidade  | Calculada            |
| `paint_encoded`            | Categórica | Tipo de tinta (codificada)    | Label Encoding       |

### Engenharia de Features

#### 1. Percentual de Tempo Ocioso (`pct_idle_recent`)

```python
# Janela móvel de 30 dias
IDLE_SPEED_THRESHOLD = 5.0  # nós
idle_hours = duration if speed < 5.0 else 0
pct_idle_recent = sum(idle_hours_30d) / sum(total_hours_30d)
```

#### 2. Risco Acumulado de Fouling (`accumulated_fouling_risk`)

```python
accumulated_fouling_risk = pct_idle_recent × days_since_cleaning
```

- **Lógica**: Navios parados por mais tempo em águas paradas acumulam mais biofouling

#### 3. Fator de Performance de Tinta (`paint_performance_factor`)

```python
if is_SPC and pct_idle_recent > 0.30:
    paint_performance_factor = 0.80  # Penalidade de 20%
else:
    paint_performance_factor = 1.00
```

- **SPC (Self-Polishing Coating)**: Funciona melhor com movimento

#### 4. Dias Desde Limpeza (`days_since_cleaning`)

```python
# Merge assíncrono com tabela de docagens
days_since_cleaning = event_date - last_drydock_date
```

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

### Fórmulas

```python
additional_fuel_tons = baseline_consumption × target_excess_ratio
additional_cost_usd = additional_fuel_tons × 500
additional_co2_tons = additional_fuel_tons × 3.114
```

---

## 📁 Dados de Entrada

### Arquivos Necessários

| Arquivo                       | Formato | Descrição          | Colunas Principais                                                                        |
| ----------------------------- | ------- | ------------------ | ----------------------------------------------------------------------------------------- |
| `ResultadoQueryEventos.csv`   | CSV     | Eventos AIS        | shipName, sessionId, startGMTDate, speed, duration, displacement, midDraft, beaufortScale |
| `ResultadoQueryConsumo.csv`   | CSV     | Consumo por sessão | SESSION_ID, CONSUMED_QUANTITY                                                             |
| `Dados navios Hackathon.xlsx` | Excel   | Docagens e tintas  | Sheet: "Lista de docagens" → Navio, Docagem                                               |

### Mapeamento de Colunas

```python
COL_SHIP_NAME = 'shipName'
COL_START_DATE = 'startGMTDate'
COL_SESSION_ID = 'sessionId'
COL_SESSION_ID_CONSUMPTION = 'SESSION_ID'
COL_CONSUMPTION = 'CONSUMED_QUANTITY'
COL_SPEED = 'speed'
COL_DURATION = 'duration'
COL_DISPLACEMENT = 'displacement'
COL_DRAFT = 'midDraft'
COL_DOCAGEM_DATE = 'Docagem'
COL_DOCAGEM_SHIP = 'Navio'
COL_PAINT_TYPE = 'Tipo'
```

---

## 🔀 Split de Dados

| Conjunto      | Proporção         | Uso              |
| ------------- | ----------------- | ---------------- |
| **Treino**    | 80% (cronológico) | Ajuste do modelo |
| **Validação** | 10% do treino     | Early stopping   |
| **Teste**     | 20% (cronológico) | Avaliação final  |

```python
TRAIN_TEST_SPLIT_RATIO = 0.80
VALIDATION_SPLIT_RATIO = 0.90  # 90% do treino para fit, 10% para validação
```

⚠️ **Split cronológico**: Não aleatório, respeita ordem temporal para evitar data leakage.

---

## 📈 Métricas de Performance

### Métricas Calculadas

| Métrica      | Fórmula                  | Descrição                 |
| ------------ | ------------------------ | ------------------------- |
| **RMSE**     | √(Σ(real - pred)² / n)   | Erro quadrático médio     |
| **MAE**      | Σ\|real - pred\| / n     | Erro absoluto médio       |
| **WMAPE**    | Σ\|real - pred\| / Σreal | Erro percentual ponderado |
| **Accuracy** | 100 × (1 - WMAPE)        | Acurácia geral            |

### Sanity Check (Validação de Impacto)

```python
# Compara predição para navio limpo vs sujo
Cenário Limpo:  days_since_cleaning = 30
Cenário Sujo:   days_since_cleaning = 400

Biofouling Penalty = fuel_dirty - fuel_clean
```

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

## 🔧 Configuração

### Variáveis de Ambiente (`.env`)

```env
# APIs Externas (opcional)
WEATHER_API_URL=
WEATHER_API_KEY=
VESSEL_API_URL=
VESSEL_API_KEY=
FUEL_API_URL=
FUEL_API_KEY=

# Observabilidade
LOG_LEVEL=INFO
OTEL_ENABLED=false
METRICS_ENABLED=true
```

---

## 📁 Estrutura do Projeto

```
├── api/                          # Backend FastAPI
│   ├── main.py                   # Aplicação principal
│   ├── config.py                 # Configurações (60+ parâmetros)
│   ├── schemas.py                # Modelos Pydantic
│   ├── services.py               # BiofoulingService, DataService
│   ├── external_clients.py       # Clientes HTTP para APIs externas
│   ├── integration_service.py    # Orquestrador de serviços
│   └── routes/
│       ├── predictions.py        # Endpoints de predição
│       ├── ships.py              # Endpoints de navios
│       ├── reports.py            # Endpoints de relatórios
│       └── integrations.py       # Endpoints de integração
├── src/
│   ├── script.py                 # Script principal (662 linhas)
│   ├── analise_relatorio.py      # Análise dos relatórios
│   └── validacao_cientifica.py   # Validação científica
├── data/
│   ├── raw/                      # Dados brutos
│   └── processed/                # Relatórios gerados
├── models/                       # Modelos .pkl
├── config/                       # config_biofouling.json
├── reports/                      # Resumos texto/markdown
├── docs/                         # Documentação adicional
│   └── MICROSERVICES_ARCHITECTURE.md
├── run_api.py                    # Iniciar API
└── requirements.txt              # Dependências
```

---

## 🚀 Instalação e Execução

### Requisitos

- Python 3.8+
- ~2GB RAM para treinamento
- ~500MB para inferência

### Instalação

```bash
git clone https://github.com/marcio-loiola/modelo-transpetro-v2.git
cd modelo-transpetro-v2
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

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

---

## 🔄 Comparativo para Análise

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

---

## 👥 Autor

**Marcio Loiola** - [GitHub](https://github.com/marcio-loiola)

## 📄 Licença

Desenvolvido para o **Hackathon Transpetro 2024**.
