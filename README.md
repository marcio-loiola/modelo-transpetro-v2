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
- **FastAPI** - Backend API REST
- **SQLAlchemy** - ORM para banco de dados
- **SQLite** - Banco de dados

## 📁 Estrutura do Projeto

```
├── api/                          # Backend FastAPI
│   ├── __init__.py
│   ├── main.py                   # Aplicação principal
│   ├── config.py                 # Configurações
│   ├── database.py               # Banco de dados SQLite
│   ├── schemas.py                # Modelos Pydantic
│   ├── services.py               # Serviços de negócio e ML
│   └── routes/                   # Rotas da API
│       ├── predictions.py        # Endpoints de predição
│       ├── ships.py              # Endpoints de navios
│       └── reports.py            # Endpoints de relatórios
├── src/                          # Código fonte do modelo
│   ├── script.py                 # Script principal do modelo
│   ├── analise_relatorio.py      # Análise dos relatórios gerados
│   └── validacao_cientifica.py   # Validação científica do modelo
├── data/
│   ├── raw/                      # Dados brutos de entrada
│   ├── processed/                # Dados processados (output)
│   └── database/                 # Banco de dados SQLite
│       └── biofouling.db
├── models/                       # Modelos treinados
│   ├── modelo_final_v13.pkl
│   └── encoder_final_v13.pkl
├── config/                       # Arquivos de configuração
├── reports/                      # Relatórios e resumos
├── docs/                         # Documentação
├── run_api.py                    # Script para iniciar a API
├── test_api_complete.py          # Testes completos da API
├── init_database.py              # Inicializar banco de dados
├── requirements.txt              # Dependências Python
├── README.md                     # Este arquivo
└── README_BACKEND.md             # Documentação do backend
```

## 🚀 Instalação

1. Clone o repositório:

```bash
git clone <repository-url>
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

### Treinar o Modelo

Execute o script principal para treinar o modelo:

```bash
python src/script.py
```

O script irá:

1. Carregar os dados de eventos e consumo
2. Realizar engenharia de features
3. Treinar o modelo XGBoost
4. Gerar relatórios de biofouling

### Iniciar a API

Execute o servidor FastAPI:

```bash
python run_api.py
```

Ou diretamente com uvicorn:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em:

- **API**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **Documentação ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

> 📖 **Para detalhes completos sobre o backend e seus endpoints, consulte**: [README_BACKEND.md](README_BACKEND.md)

## 🔌 API Endpoints Principais

### Predições

| Método | Endpoint                       | Descrição                              |
| ------ | ------------------------------ | -------------------------------------- |
| POST   | `/api/v1/predictions/`         | Predição de biofouling para uma viagem |
| POST   | `/api/v1/predictions/batch`    | Predições em lote                      |
| POST   | `/api/v1/predictions/scenario` | Comparação de cenários (limpo vs sujo) |

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

## 📚 Documentação Adicional

- **[README_BACKEND.md](README_BACKEND.md)** - Documentação completa do backend API
- **[TEST_README.md](TEST_README.md)** - Guia de testes
- **[CORRECOES_ERROS.md](CORRECOES_ERROS.md)** - Correções implementadas

## 👥 Autor

**Marcio Loiola**

## 📄 Licença

Este projeto foi desenvolvido para o Hackathon Transpetro 2024.
