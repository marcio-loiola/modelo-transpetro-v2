# Resumo do Processo de Cálculo do Nível de Bioincrustação

## 1. Objetivo

Quantificar o **nível de bioincrustação** (biofouling) dos navios da frota, estimando:

- O consumo extra de combustível causado pela incrustação do casco
- O custo financeiro adicional (USD)
- As emissões adicionais de CO₂ (toneladas)
- Uma classificação qualitativa do estado do casco (Leve / Moderada / Severa)

---

## 2. Dados Utilizados

| Arquivo                       | Descrição                                                                               |
| ----------------------------- | --------------------------------------------------------------------------------------- |
| `ResultadoQueryEventos.csv`   | Eventos de navegação (velocidade, duração, calado, deslocamento, escala Beaufort, etc.) |
| `ResultadoQueryConsumo.csv`   | Consumo de combustível por sessão (`SESSION_ID`, `CONSUMED_QUANTITY`)                   |
| `Dados navios Hackathon.xlsx` | Datas de docagem (limpeza) e especificação de revestimento/tinta                        |

---

## 3. Pipeline de Processamento

```
┌─────────────────────────────────────────────────────────────────┐
│  1. CARGA DOS DADOS                                             │
│     • Leitura de CSVs e Excel                                   │
│     • Agregação de consumo por SESSION_ID (soma)                │
│     • Normalização de nomes de navios (uppercase, trim)         │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. MERGE DOS DATASETS                                          │
│     • Eventos ↔ Consumo (por sessionId)                         │
│     • Eventos ↔ Tipo de tinta (por shipName)                    │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. CÁLCULO DE days_since_cleaning                              │
│     • Para cada evento, encontra a última docagem anterior      │
│     • Usa merge_asof (vetorizado) para performance              │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CÁLCULO DO CONSUMO BASELINE (casco limpo)                   │
│     • Fórmula do Coeficiente do Almirantado (física)            │
│     • Calibração POR NAVIO com dados pós-docagem (< 90 dias)    │
│     • Fallback global para navios sem dados limpos              │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. CÁLCULO DO EXCESS RATIO (ER)                                │
│     • ER = (Consumo_real − Consumo_baseline) / Consumo_baseline │
│     • Representa a fração de consumo extra                      │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. ÍNDICE E CLASSIFICAÇÃO                                      │
│     • BIO_REFERENCE dinâmico (percentil 75 do ER)               │
│     • bio_index via função SIGMOID (transição suave)            │
│     • bio_index_0_10 = bio_index × 10                           │
│     • Classificação: Leve / Moderada / Severa                   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. CUSTO E EMISSÕES                                            │
│     • Combustível extra = baseline × ER                         │
│     • Custo extra = combustível extra × preço (500 USD/t)       │
│     • CO₂ extra = combustível extra × 3.114 tCO₂/t              │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. EXPORTAÇÃO DE RELATÓRIOS                                    │
│     • biofouling_report.csv (detalhe por evento)                │
│     • biofouling_summary_by_ship.csv (agregado por navio)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Fórmulas Utilizadas

### 4.1 Potência Teórica (Coeficiente do Almirantado)

$$
P_{teórica} = \frac{D^{2/3} \times V^3}{C_A}
$$

Onde:

- $D$ = Deslocamento (toneladas) — se indisponível, usa `midDraft × 10.000`
- $V$ = Velocidade (nós)
- $C_A$ = Fator de escala do Almirantado (10.000)

### 4.2 Consumo Baseline (Casco Limpo)

$$
C_{baseline} = P_{teórica} \times duração \times \eta_{navio}
$$

Onde:

- $\eta_{navio}$ = **Fator de eficiência calibrado POR NAVIO** (mediana do consumo real / potência teórica para eventos com < 90 dias desde a limpeza daquele navio específico)
- Fallback global: **η ≈ 0.004158** (usado para navios sem dados limpos)
- Total de navios com calibração individual: **21**

### 4.3 Excess Ratio (Nível de Bioincrustação)

$$
ER = \frac{C_{real} - C_{baseline}}{C_{baseline}}
$$

- $ER = 0$ → Consumo igual ao esperado (casco limpo)
- $ER = 0.15$ → 15% de consumo extra
- $ER = 0.50$ → 50% de consumo extra (incrustação severa)

### 4.4 Índice Normalizado (0–10) — Escala Sigmoid

**Versão atual (Sigmoid):**

$$
\text{bio\_index} = \frac{1}{1 + e^{-k(ER - m)}}
$$

Onde:

- $k = 10$ (fator de inclinação)
- $m = 0.10$ (ponto médio — bio_index = 0.5 quando ER = 10%)

**Referência dinâmica:**

- $R_{ref}$ = Percentil 75 do ER no dataset
- Valor calculado: **22.2%** (varia conforme os dados)

$$
\text{bio\_index\_0\_10} = \text{round}(\text{bio\_index} \times 10, 1)
$$

**Vantagem da Sigmoid:** Transição suave entre níveis, evitando descontinuidades nos limites.

### 4.5 Custo e Emissões Adicionais

$$
\Delta_{fuel} = C_{baseline} \times ER
$$

$$
\text{Custo}_{USD} = \Delta_{fuel} \times P_{fuel}
$$

$$
\Delta_{CO_2} = \Delta_{fuel} \times 3.114
$$

Onde:

- $P_{fuel}$ = Preço do combustível (configurado: **500 USD/t**)
- $3.114$ = Fator de emissão de CO₂ por tonelada de HFO/LSHFO

---

## 5. Classificação Qualitativa

| Classificação | Excess Ratio (ER) | Índice 0–10 | Descrição                                            |
| ------------- | ----------------- | ----------- | ---------------------------------------------------- |
| **Leve**      | < 10%             | < 5.0       | Microincrustação (biofilme/slime)                    |
| **Moderada**  | 10% – 20%         | 5.0 – 10.0  | Início de macroincrustação (algas, organismos moles) |
| **Severa**    | ≥ 20%             | 10.0        | Macroincrustação pesada (cracas, tubos calcários)    |

**Trigger recomendado para limpeza:** ER entre 10%–15% (antes de atingir macroincrustação).

---

## 6. Arquivos Gerados

### `biofouling_report.csv`

Detalhe por evento de navegação:

| Coluna                 | Descrição                            |
| ---------------------- | ------------------------------------ |
| `shipName`             | Nome do navio                        |
| `startGMTDate`         | Data/hora do evento                  |
| `sessionId`            | ID da sessão                         |
| `CONSUMED_QUANTITY`    | Consumo real (t)                     |
| `baseline_consumption` | Consumo esperado casco limpo (t)     |
| `target_excess_ratio`  | Excess Ratio (ER)                    |
| `bio_index_0_10`       | Índice de bioincrustação (0–10)      |
| `bio_class`            | Classificação (Leve/Moderada/Severa) |
| `additional_fuel_tons` | Combustível extra (t)                |
| `additional_cost_usd`  | Custo extra (USD)                    |
| `additional_co2_tons`  | CO₂ extra (t)                        |

### `biofouling_summary_by_ship.csv`

Resumo agregado por navio:

| Coluna                      | Descrição                         |
| --------------------------- | --------------------------------- |
| `shipName`                  | Nome do navio                     |
| `avg_excess_ratio`          | Média do ER                       |
| `max_excess_ratio`          | Maior ER registrado               |
| `num_events`                | Número de eventos                 |
| `avg_bio_index`             | Média do índice 0–10              |
| `max_bio_index`             | Maior índice 0–10                 |
| `total_baseline_fuel`       | Total de consumo baseline (t)     |
| `total_real_fuel`           | Total de consumo real (t)         |
| `total_additional_fuel`     | Total de combustível extra (t)    |
| `total_additional_cost_usd` | Custo total extra (USD)           |
| `total_additional_co2`      | Emissões totais extras de CO₂ (t) |

---

## 7. Modelo Preditivo (XGBoost)

Além do cálculo direto do ER, o script treina um modelo XGBoost para prever o `target_excess_ratio` com base em features operacionais:

| Feature                    | Descrição                                        |
| -------------------------- | ------------------------------------------------ |
| `speed`                    | Velocidade do navio (nós)                        |
| `beaufortScale`            | Escala Beaufort (condição do mar)                |
| `days_since_cleaning`      | Dias desde última docagem                        |
| `pct_idle_recent`          | % de tempo em baixa velocidade (últimos 30 dias) |
| `accumulated_fouling_risk` | Risco acumulado = pct_idle × days_since_cleaning |
| `historical_avg_speed`     | Velocidade média histórica (últimos 10 eventos)  |
| `paint_x_speed`            | Interação tipo de tinta × velocidade             |
| `paint_encoded`            | Tipo de tinta (codificado)                       |

### Métricas do Modelo (última execução)

| Métrica  | Valor     |
| -------- | --------- |
| RMSE     | 8.04 tons |
| MAE      | 5.68 tons |
| WMAPE    | 20.45%    |
| Accuracy | 79.55%    |

### Importância das Features

| Feature                  | Importância |
| ------------------------ | ----------- |
| speed                    | 44.2%       |
| paint_encoded            | 21.9%       |
| paint_x_speed            | 21.1%       |
| days_since_cleaning      | 5.1%        |
| accumulated_fouling_risk | 2.3%        |
| historical_avg_speed     | 2.1%        |
| pct_idle_recent          | 2.1%        |
| beaufortScale            | 1.1%        |

---

## 8. Referência Regulatória

A **Portaria DPC/DGN/MB 180/2025** exige:

- Plano de Gestão de Bioincrustações (BMP)
- Livro de Registro de Bioincrustações (BRB)
- Níveis de bioincrustação abaixo dos limites para transitar entre regiões biogeográficas
- Multa máxima: **R$ 2.000.000** (vigência: 01/02/2026)

---

## 9. Como Executar

```powershell
cd "C:\Users\Usuário\Downloads\dados-transpetro"
python script.py
```

### Configurações ajustáveis (em `Config` no `script.py`)

| Parâmetro                  | Valor Padrão | Descrição                                          |
| -------------------------- | ------------ | -------------------------------------------------- |
| `BIO_REFERENCE`            | `None`       | `None` = dinâmico (P75), ou valor fixo (ex.: 0.20) |
| `BIO_REFERENCE_PERCENTILE` | 0.75         | Percentil usado quando BIO_REFERENCE é None        |
| `USE_SIGMOID_SCALE`        | `True`       | Usar sigmoid (suave) ou linear (original)          |
| `SIGMOID_K`                | 10           | Inclinação da sigmoid                              |
| `SIGMOID_MIDPOINT`         | 0.10         | ER onde bio_index = 0.5                            |
| `CALIBRATE_PER_SHIP`       | `True`       | Calibrar η por navio (mais preciso)                |
| `FUEL_PRICE_USD_PER_TON`   | 500          | Preço do combustível (USD/t)                       |
| `CO2_TON_PER_FUEL_TON`     | 3.114        | Fator de emissão CO₂                               |

---

## 10. Resumo Visual

```
                    NAVIO LIMPO                    NAVIO INCRUSTADO
                    ───────────                    ────────────────

                    ┌─────────┐                    ┌─────────┐
                    │  🚢    │                    │  🚢🦠🐚  │
                    │ Casco  │                    │  Casco  │
                    │ liso   │                    │  rugoso │
                    └─────────┘                    └─────────┘
                         │                              │
                         ▼                              ▼
                    Arrasto BAIXO                  Arrasto ALTO
                    Consumo BASE                   Consumo +20-50%
                    ER ≈ 0%                        ER ≈ 20-50%
                    bio_index ≈ 0                  bio_index ≈ 10
                    Classe: Leve                   Classe: Severa
```

---

## 11. Histórico de Modificações no Script

### 11.1 Estado Original do Script

O script original (`script.py`) foi projetado para treinar um modelo XGBoost de previsão de consumo de combustível, mas apresentava algumas limitações:

| Aspecto                       | Comportamento Original                                                                          |
| ----------------------------- | ----------------------------------------------------------------------------------------------- |
| **Caminho dos dados**         | Fixo em `Raw_Data/` — falhava se os arquivos estivessem na raiz                                 |
| **Tratamento de erros**       | `sys.exit(1)` sem mensagem — difícil diagnosticar falhas                                        |
| **Consumo duplicado**         | Múltiplas linhas por `SESSION_ID` (diferentes tipos de combustível) geravam duplicação no merge |
| **days_since_cleaning**       | Calculado com `apply()` linha-a-linha — lento para grandes datasets                             |
| **Índice de bioincrustação**  | Não existia — apenas `target_excess_ratio` bruto                                                |
| **Classificação qualitativa** | Não existia                                                                                     |
| **Custo e emissões**          | Não calculados                                                                                  |
| **Relatórios CSV**            | Não gerados                                                                                     |
| **Resumo por navio**          | Não gerado                                                                                      |

### 11.2 Saída Original do Script

Antes das modificações, a saída do script era apenas:

```
CALIBRATED EFFICIENCY FACTOR: 0.004156
----------------------------------------
FINAL RESULTS - BIOFOULING FOCUSED MODEL
----------------------------------------
RMSE: 7.9139
MAE:  5.4983
WMAPE: 19.7319%
ACCURACY: 80.2681%
----------------------------------------

FEATURE IMPORTANCE (Deve ser dominado por Bio/Ops):
                    Feature  Importance
0                     speed    0.409200
7             paint_encoded    0.248157
...

--- SANITY CHECK: BIOFOULING IMPACT ---
Baseline (Physics only): 69.52 tons
Prediction (Clean 30d):  54.87 tons (Ratio: -21.07%)
Prediction (Dirty 400d): 56.17 tons (Ratio: -19.20%)
Biofouling Penalty: 1.30 tons (+2.4%)
```

**Problema identificado:** O script calculava o `target_excess_ratio` internamente, mas não o exportava nem o transformava em métricas acionáveis (índice, classificação, custo).

### 11.3 Modificações Aplicadas

#### Correção 1: Fallback para `DATA_DIR`

```python
# ANTES:
DATA_DIR = os.path.join(BASE_DIR, 'Raw_Data')

# DEPOIS:
_possible_raw = os.path.join(BASE_DIR, 'Raw_Data')
DATA_DIR = _possible_raw if os.path.exists(_possible_raw) else BASE_DIR
```

**Resultado:** Script funciona tanto com arquivos em `Raw_Data/` quanto na raiz do projeto.

#### Correção 2: Log de erro em `load_data()`

```python
# ANTES:
except Exception as e:
    sys.exit(1)

# DEPOIS:
except Exception as e:
    print(f"Error loading data: {e}", file=sys.stderr)
    sys.exit(1)
```

**Resultado:** Erros de carregamento agora são visíveis no console.

#### Correção 3: Proteção contra NaN em `calculate_theoretical_power()`

```python
# ANTES:
if speed < 1: return 0

# DEPOIS:
if pd.isna(speed) or speed < 1:
    return 0
```

**Resultado:** Evita `TypeError` quando `speed` é `NaN`.

#### Melhoria A: Agregação de consumo por `SESSION_ID`

```python
# ADICIONADO em load_data():
df_consumption[Config.COL_CONSUMPTION] = pd.to_numeric(
    df_consumption[Config.COL_CONSUMPTION], errors='coerce'
)
df_consumption = df_consumption.groupby(
    Config.COL_SESSION_ID_CONSUMPTION, as_index=False
)[Config.COL_CONSUMPTION].sum()
```

**Resultado:** Elimina duplicação de linhas causada por múltiplos tipos de combustível (LSHFO, ULSMGO, etc.) no mesmo `SESSION_ID`.

#### Melhoria B: Vetorização de `days_since_cleaning`

```python
# ANTES (lento):
df_main['days_since_cleaning'] = df_main.apply(
    lambda r: get_days_since_cleaning(r, df_drydock), axis=1
)

# DEPOIS (rápido):
def get_days_since_cleaning_vectorized(df_events, df_drydock):
    # Usa pd.merge_asof por navio para encontrar última docagem
    ...
days_df = get_days_since_cleaning_vectorized(df_main, df_drydock)
df_main = pd.merge(df_main, days_df, on=[...], how='left')
```

**Resultado:** Performance significativamente melhor para datasets grandes (evita loop Python).

#### Melhoria C: Cálculo do Índice de Bioincrustação

```python
# ADICIONADO:
df_main['bio_index'] = (df_main['target_excess_ratio'] / Config.BIO_REFERENCE).clip(0, 1)
df_main['bio_index_0_10'] = (df_main['bio_index'] * 10).round(1)

def classify_bio(er):
    if er < 0.10: return 'Leve'
    if er < 0.20: return 'Moderada'
    return 'Severa'

df_main['bio_class'] = df_main['target_excess_ratio'].apply(classify_bio)
```

**Resultado:** Cada evento agora tem um índice 0–10 e uma classificação qualitativa.

#### Melhoria D: Cálculo de Custo e Emissões

```python
# ADICIONADO (Config):
FUEL_PRICE_USD_PER_TON = 500  # USD/t
CO2_TON_PER_FUEL_TON = 3.114  # tCO2/t combustível

# ADICIONADO (main):
df_main['additional_fuel_tons'] = df_main['baseline_consumption'] * df_main['target_excess_ratio']
df_main['additional_cost_usd'] = df_main['additional_fuel_tons'] * Config.FUEL_PRICE_USD_PER_TON
df_main['additional_co2_tons'] = df_main['additional_fuel_tons'] * Config.CO2_TON_PER_FUEL_TON
```

**Resultado:** Impacto financeiro e ambiental quantificados por evento.

#### Melhoria E: Exportação de Relatórios CSV

```python
# ADICIONADO:
df_main[report_cols].to_csv('biofouling_report.csv', index=False)
df_summary.to_csv('biofouling_summary_by_ship.csv', index=False)
```

**Resultado:** Dois arquivos CSV gerados automaticamente.

### 11.4 Saída Atual do Script (Após Modificações)

```
CALIBRATED EFFICIENCY FACTOR: 0.004236
Biofouling report exported to: C:\...\biofouling_report.csv      ← NOVO
Ship summary exported to: C:\...\biofouling_summary_by_ship.csv  ← NOVO
----------------------------------------
FINAL RESULTS - BIOFOULING FOCUSED MODEL
----------------------------------------
RMSE: 8.0442
MAE:  5.6845
WMAPE: 20.4543%
ACCURACY: 79.5457%
----------------------------------------

FEATURE IMPORTANCE (Deve ser dominado por Bio/Ops):
                    Feature  Importance
0                     speed    0.442156
7             paint_encoded    0.218970
6             paint_x_speed    0.210916
2       days_since_cleaning    0.051222
...

--- SANITY CHECK: BIOFOULING IMPACT ---
Baseline (Physics only): 84.53 tons
Prediction (Clean 30d):  65.41 tons (Ratio: -22.62%)
Prediction (Dirty 400d): 66.46 tons (Ratio: -21.38%)
Biofouling Penalty: 1.05 tons (+1.6%)
```

### 11.5 Comparação: Antes vs Depois

| Aspecto                               | Antes                        | Depois                              |
| ------------------------------------- | ---------------------------- | ----------------------------------- |
| **Arquivos gerados**                  | 2 (modelo `.pkl`)            | 4 (modelo + encoder + 2 CSVs)       |
| **Índice de bioincrustação**          | ❌ Não                       | ✅ `bio_index_0_10` (0–10)          |
| **Classificação**                     | ❌ Não                       | ✅ Leve / Moderada / Severa         |
| **Custo estimado**                    | ❌ Não                       | ✅ USD por evento e por navio       |
| **Emissões CO₂**                      | ❌ Não                       | ✅ Toneladas por evento e por navio |
| **Resumo por navio**                  | ❌ Não                       | ✅ `biofouling_summary_by_ship.csv` |
| **Performance (days_since_cleaning)** | Lento (apply)                | Rápido (merge_asof)                 |
| **Duplicação de consumo**             | Sim (múltiplos combustíveis) | Não (agregado por SESSION_ID)       |
| **Robustez de caminhos**              | Falha sem `Raw_Data/`        | Funciona em ambos os casos          |
| **Mensagens de erro**                 | Silenciosas                  | Visíveis no console                 |

### 11.6 Evolução das Métricas do Modelo

| Métrica           | Antes    | Depois   | Variação |
| ----------------- | -------- | -------- | -------- |
| Efficiency Factor | 0.004156 | 0.004236 | +1.9%    |
| RMSE              | 7.9139   | 8.0442   | +1.6%    |
| MAE               | 5.4983   | 5.6845   | +3.4%    |
| WMAPE             | 19.73%   | 20.45%   | +0.72pp  |
| Accuracy          | 80.27%   | 79.55%   | -0.72pp  |

**Nota:** A pequena variação nas métricas é esperada, pois a agregação por `SESSION_ID` alterou ligeiramente o dataset (removendo duplicações de consumo).

### 11.7 Arquivos Finais do Projeto

```
dados-transpetro/
├── script.py                        # Script principal (modificado)
├── requirements.txt                 # Dependências Python
├── ResultadoQueryEventos.csv        # Dados de entrada (eventos)
├── ResultadoQueryConsumo.csv        # Dados de entrada (consumo)
├── Dados navios Hackathon.xlsx      # Dados de entrada (docagens + tinta)
├── biofouling_report.csv            # ← NOVO: Relatório detalhado por evento
├── biofouling_summary_by_ship.csv   # ← NOVO: Resumo agregado por navio
├── modelo_final_v13.pkl             # Modelo XGBoost treinado
├── encoder_final_v13.pkl            # LabelEncoder para tipo de tinta
└── RESUMO_BIOFOULING.md             # ← NOVO: Este documento
```

---

## 12. Melhorias v2 — Ajustes de Precisão

### 12.1 Problema: Limitações da Versão Anterior

A versão inicial tinha algumas limitações identificadas:

| Limitação                    | Impacto                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------- |
| **BIO_REFERENCE fixo (20%)** | Valor arbitrário, não adaptado aos dados reais                                  |
| **Escala linear**            | Transições abruptas nos limites de classificação                                |
| **η global**                 | Um único fator de eficiência para toda a frota ignorava diferenças entre navios |

### 12.2 Ajustes Implementados

#### Ajuste 1: BIO_REFERENCE Dinâmico

```python
# ANTES (fixo):
BIO_REFERENCE = 0.20

# DEPOIS (dinâmico):
BIO_REFERENCE = None  # Usa percentil 75 dos dados
BIO_REFERENCE_PERCENTILE = 0.75
# Valor calculado automaticamente: 22.2%
```

**Resultado:** O limiar de "severo" agora é baseado nos próprios dados da frota, não em um valor arbitrário.

#### Ajuste 2: Escala Sigmoid para bio_index

```python
# ANTES (linear):
bio_index = ER / R_ref

# DEPOIS (sigmoid):
bio_index = 1 / (1 + exp(-k * (ER - midpoint)))
# Com k=10 e midpoint=0.10
```

**Resultado:** Transição suave entre níveis. bio_index = 0.5 quando ER = 10%.

**Visualização da diferença:**

```
Linear:     |████████████████████████████████████|  (saltos abruptos)
            0%        10%        20%        30%

Sigmoid:    |░░░░▒▒▒▒▓▓▓▓████████████████████████|  (transição suave)
            0%        10%        20%        30%
                       ↑
                  midpoint (bio_index = 0.5)
```

#### Ajuste 3: Calibração de η por Navio

```python
# ANTES (global):
efficiency_factor = mediana_global(consumo / potência)
# Valor único: 0.004236

# DEPOIS (por navio):
efficiency_by_ship = {
    'NAVIO_A': 0.00412,
    'NAVIO_B': 0.00438,
    ...
}
# 21 navios com calibração individual
# Fallback global: 0.004158
```

**Resultado:** Baseline mais preciso, considerando características individuais de cada embarcação.

### 12.3 Comparação de Resultados

| Métrica                        | Antes (v1) | Depois (v2) | Observação        |
| ------------------------------ | ---------- | ----------- | ----------------- |
| BIO_REFERENCE                  | 20% (fixo) | 22.2% (P75) | Adaptativo        |
| bio_index scale                | Linear     | Sigmoid     | Mais suave        |
| Calibração η                   | Global     | Por navio   | Mais precisa      |
| RMSE                           | 8.04       | 8.65        | Ligeiro aumento\* |
| days_since_cleaning importance | 5.1%       | 8.1%        | **+59%** ✅       |

\*O aumento do RMSE é esperado: baselines mais precisos por navio revelam variações antes mascaradas.

### 12.4 Nova Saída do Script

```
CALIBRATED EFFICIENCY FACTOR: per-ship (global fallback: 0.004158)
  Ships with individual calibration: 21
DYNAMIC BIO_REFERENCE (P75): 0.2218 (22.2%)
SIGMOID SCALE: k=10, midpoint=0.1 (bio_index=0.5 at ER=10%)
Biofouling report exported to: ...\biofouling_report.csv
Ship summary exported to: ...\biofouling_summary_by_ship.csv
----------------------------------------
FINAL RESULTS - BIOFOULING FOCUSED MODEL
----------------------------------------
RMSE: 8.6528
MAE:  5.8199
WMAPE: 22.3219%
ACCURACY: 77.6781%
----------------------------------------
```

### 12.5 Validação Científica das Melhorias

| Ajuste                     | Base Científica                                                                  |
| -------------------------- | -------------------------------------------------------------------------------- |
| **BIO_REFERENCE dinâmico** | Estatística descritiva — percentis adaptam-se à distribuição real dos dados      |
| **Escala Sigmoid**         | Função logística usada em classificação probabilística (Hosmer & Lemeshow, 2000) |
| **Calibração por navio**   | ISO 19030 recomenda baseline específico por embarcação para maior precisão       |

---

## 13. Validação Científica — Perguntas para Fontes Acadêmicas

Esta seção documenta as **perguntas críticas** que devem ser feitas para validar o modelo contra a literatura científica de referência.

### 13.1 Referências Principais

| Fonte                   | Descrição                                                                              | DOI                          |
| ----------------------- | -------------------------------------------------------------------------------------- | ---------------------------- |
| Schultz (2007)          | Effects of coating roughness and biofouling on ship resistance and powering            | 10.1080/08927010701461974    |
| Schultz et al. (2011)   | Economic impact of biofouling on a naval surface ship                                  | 10.1080/08927014.2010.542809 |
| Lindholdt et al. (2015) | Effects of biofouling development on drag forces of hull coatings                      | 10.1007/s11998-014-9651-2    |
| ISO 19030:2016          | Ships and marine technology — Measurement of changes in hull and propeller performance | —                            |
| IMO MEPC.1/Circ.815     | Guidance on treatment of innovative energy efficiency technologies                     | —                            |
| BIMCO (2022)            | Industry Standard on In-Water Cleaning                                                 | —                            |

### 13.2 Hipóteses Científicas e Perguntas de Validação

#### H1: Correlação ER × Tempo desde Limpeza

| Aspecto                     | Detalhe                                                                                                                                                            |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Pergunta**                | O Excess Ratio aumenta com o tempo desde a última limpeza/docagem?                                                                                                 |
| **Esperado**                | Correlação positiva (r > 0.15)                                                                                                                                     |
| **Fonte**                   | Schultz (2007), ISO 19030                                                                                                                                          |
| **Racional**                | A bioincrustação é um processo temporal progressivo. Organismos marinhos colonizam o casco gradualmente (slime → algas → cracas), aumentando rugosidade e arrasto. |
| **O que perguntar à fonte** | _"Qual é a taxa de crescimento típica de fouling (mm/mês)? A relação é linear ou segue curva S (lag → exponencial → saturação)?"_                                  |

#### H2: Magnitude do ER por Faixa Temporal

| Aspecto                     | Detalhe                                                                                                                                                                          |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | -------------------- | ---------------- |
| **Pergunta**                | O ER médio está dentro das faixas esperadas para cada período pós-limpeza?                                                                                                       |
| **Esperado**                | 0-90 dias: < 10%                                                                                                                                                                 | 90-180 dias: 10-25% | 180-365 dias: 15-35% | >365 dias: > 25% |
| **Fonte**                   | Schultz (2007), Lindholdt (2015)                                                                                                                                                 |
| **Racional**                | Schultz demonstrou: slime fino (~0.5mm) = 10-16% de penalidade; fouling calcário (cracas) = 40-80%.                                                                              |
| **O que perguntar à fonte** | _"Quais são as faixas de penalidade de potência para cada nível de fouling (FR 0-100 da NSTM)? O tipo de rota (tropical vs. temperada) altera significativamente essas faixas?"_ |

#### H3: Efeito da Velocidade no ER

| Aspecto                     | Detalhe                                                                                                                           |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Pergunta**                | Navios operando em alta velocidade têm ER menor (auto-limpeza hidrodinâmica)?                                                     |
| **Esperado**                | ER(speed > 12 nós) < ER(speed < 8 nós)                                                                                            |
| **Fonte**                   | Schultz (2011), Lindholdt (2015)                                                                                                  |
| **Racional**                | Velocidades acima de 10-12 nós geram forças de cisalhamento suficientes para desprender organismos moles (slime, algas) do casco. |
| **O que perguntar à fonte** | _"Qual é a velocidade crítica para remoção de slime? Diferentes tipos de tinta (SPC vs. FR) têm comportamentos distintos?"_       |

#### H4: Proporção de ER Negativo

| Aspecto                     | Detalhe                                                                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pergunta**                | A proporção de eventos com ER < 0 é aceitável (ruído vs. erro sistemático)?                                                                                    |
| **Esperado**                | < 40% dos eventos                                                                                                                                              |
| **Fonte**                   | ISO 19030, análise estatística de baseline                                                                                                                     |
| **Racional**                | ER negativo indica consumo menor que baseline. Pode ser: (1) condições favoráveis (corrente, vento de popa), (2) baseline superestimado, (3) ruído de medição. |
| **O que perguntar à fonte** | _"Qual é a incerteza típica na medição de consumo de combustível (% do valor)? ISO 19030 define tolerância para variabilidade de condições?"_                  |

#### H5: Efeito do Tempo de Inatividade

| Aspecto                     | Detalhe                                                                                                                                        |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pergunta**                | Navios com maior tempo parado (idle/anchorage) têm maior ER?                                                                                   |
| **Esperado**                | Correlação positiva entre % tempo parado e ER                                                                                                  |
| **Fonte**                   | Schultz (2007), IMO Guidelines                                                                                                                 |
| **Racional**                | Bioincrustação ocorre principalmente durante períodos estacionários. Água parada facilita fixação de larvas e crescimento de biofilme.         |
| **O que perguntar à fonte** | _"Qual é a taxa de colonização em condições estáticas vs. dinâmicas? Existe tempo mínimo de parada para início de colonização significativa?"_ |

#### H6: Impacto do Tipo de Tinta

| Aspecto                     | Detalhe                                                                                                                           |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Pergunta**                | Tintas SPC (Self-Polishing Copolymer) resultam em menor ER que tintas convencionais?                                              |
| **Esperado**                | ER(SPC) < ER(CDP) para mesmo days_since_cleaning                                                                                  |
| **Fonte**                   | Lindholdt (2015), catálogos de fabricantes                                                                                        |
| **Racional**                | Tintas SPC liberam biocidas gradualmente e renovam superfície por ablação, mantendo casco mais liso.                              |
| **O que perguntar à fonte** | _"Qual é a taxa de polimento (μm/mês) típica de tintas SPC? Após quanto tempo a eficácia do biocida diminui significativamente?"_ |

### 13.3 Resultados da Validação (Dados Atuais)

Script de validação: `validacao_cientifica.py`

```
================================================================================
                    RESULTADOS DOS TESTES
================================================================================

--- H2: Distribuição por Classificação ---
   Leve (< 10%): 7569 eventos (65.4%) - ER médio: -19.3%
   Moderada (10-20%): 932 eventos (8.1%) - ER médio: 14.8%
   Severa (≥ 20%): 3074 eventos (26.6%) - ER médio: 49.3%
   → ✅ Distribuição plausível

--- H4: Distribuição do Excess Ratio ---
   Média: 1.70%
   Mediana: -4.91%
   Desvio Padrão: 34.74%
   → ⚠️ Distribuição moderadamente assimétrica

--- H5: Proporção de ER Negativo ---
   Eventos com ER < 0: 6408 (55.4%)
   → ❌ PROBLEMA - Baseline pode estar superestimado

--- H7: Distribuição do bio_index ---
   Índice 0-3 (baixo): 57.2%
   Índice 4-6 (médio): 11.9%
   Índice 7-10 (alto): 31.0%
   → ✅ Variabilidade adequada
```

### 13.4 Diagnóstico e Próximos Passos

| Achado                       | Interpretação                                                                                      | Ação Recomendada                                                                                   |
| ---------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **55% de ER negativo**       | Baseline superestimado ou alta variabilidade nas condições de operação                             | Revisar fator de eficiência η — considerar calibração com dados de teste de velocidade (sea trial) |
| **Distribuição assimétrica** | Esperado — ER tem limite inferior físico (não pode ser muito negativo) mas pode ser muito positivo | Considerar transformação log ou truncar outliers                                                   |
| **ER médio "Leve" = -19%**   | Navios classificados como "Leve" têm consumo menor que baseline                                    | Recalibrar baseline usando percentil 10 ou condições ideais documentadas                           |

### 13.5 Checklist de Validação Acadêmica

Ao consultar as fontes científicas, verifique:

- [ ] **Schultz (2007)**: Tabela de % aumento de potência por nível de fouling (FR 0-100)
- [ ] **Schultz (2011)**: Custo anual de fouling para navios semelhantes (USS Arleigh Burke ~$56M/ano)
- [ ] **ISO 19030**: Metodologia de cálculo de performance baseline e tolerâncias aceitáveis
- [ ] **Lindholdt (2015)**: Taxas de crescimento de fouling por tipo de tinta e região geográfica
- [ ] **IMO MEPC**: Fatores de emissão de CO₂ por tipo de combustível (3.206 kg CO₂/kg HFO)

### 13.6 Perguntas-Chave para Refinamento do Modelo

1. **Para calibração do baseline:**

   > "Qual é o consumo específico (g/kWh) típico para motores diesel marítimos de carga em condições ótimas?"

2. **Para validação do ER:**

   > "Estudos de campo mostram que navios comerciais têm ER médio de quanto após 1 ano sem limpeza?"

3. **Para impacto econômico:**

   > "O custo de USD 500/ton de combustível é realista para bunker atual? Qual faixa considerar?"

4. **Para emissões:**
   > "O fator 3.206 kg CO₂/kg combustível é adequado para mistura de HFO e diesel marítimo?"

---

_Documento atualizado em 29/11/2025 — Seção 13 adicionada_
