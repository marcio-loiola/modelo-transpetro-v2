# Modelo de Predição de Biofouling - Transpetro v2

## 📋 Descrição

Este projeto implementa um modelo de Machine Learning (XGBoost) para predição do impacto de **biofouling** (incrustação biológica) no consumo de combustível de navios da frota Transpetro.

O biofouling é o acúmulo de organismos marinhos no casco dos navios, causando aumento da resistência ao avanço e, consequentemente, maior consumo de combustível e emissões de CO₂.

## 🎯 Objetivos

- Prever o **excesso de consumo de combustível** causado por biofouling
- Calcular o **índice de biofouling** (escala 0-10) para cada embarcação
- Estimar **custos adicionais** e **emissões de CO₂** associadas
- Auxiliar na tomada de decisão sobre **limpeza de casco** (docagem)

## 🛠️ Tecnologias Utilizadas

- **Python 3.8+**
- **Pandas** - Manipulação de dados
- **NumPy** - Computação numérica
- **XGBoost** - Modelo de Machine Learning
- **Scikit-learn** - Métricas e pré-processamento
- **Matplotlib** - Visualizações

## 📁 Estrutura do Projeto

```
├── src/                          # Código fonte
│   ├── script.py                 # Script principal do modelo
│   ├── analise_relatorio.py      # Análise dos relatórios gerados
│   └── validacao_cientifica.py   # Validação científica do modelo
├── data/
│   ├── raw/                      # Dados brutos de entrada
│   │   ├── ResultadoQueryEventos.csv
│   │   ├── ResultadoQueryConsumo.csv
│   │   └── Dados navios Hackathon.xlsx
│   └── processed/                # Dados processados (output)
│       ├── biofouling_report.csv
│       └── biofouling_summary_by_ship.csv
├── models/                       # Modelos treinados
│   ├── modelo_final_v13.pkl
│   └── encoder_final_v13.pkl
├── config/                       # Arquivos de configuração
│   └── config_biofouling.json
├── reports/                      # Relatórios e resumos
│   ├── RESUMO_BIOFOULING.md
│   └── RESUMO_BIOFOULING.txt
├── docs/                         # Documentação e referências
├── requirements.txt              # Dependências Python
└── README.md                     # Este arquivo
```

## 🚀 Instalação

1. Clone o repositório:

```bash
git clone https://github.com/marcio-loiola/modelo-transpetro-v2.git
cd modelo-transpetro-v2
```

2. Crie um ambiente virtual:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## 💻 Uso

Execute o script principal:

```bash
python src/script.py
```

O script irá:

1. Carregar os dados de eventos e consumo
2. Realizar engenharia de features
3. Treinar o modelo XGBoost
4. Gerar relatórios de biofouling

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

## 👥 Autor

**Marcio Loiola**

## 📄 Licença

Este projeto foi desenvolvido para o Hackathon Transpetro 2024.
