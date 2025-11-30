# 🚢 Backend API - Predição de Biofouling Transpetro

## 📋 Visão Geral

API REST desenvolvida com **FastAPI** para predição de biofouling (incrustação biológica) e análise do impacto no consumo de combustível da frota Transpetro. O backend utiliza modelo de Machine Learning (XGBoost) treinado para fazer predições precisas.

## 🎯 O que o Backend Oferece

### 1. **Predições de Biofouling** 🤖

Sistema de predição inteligente que calcula:

- ✅ Consumo de combustível previsto
- ✅ Índice de biofouling (0-10)
- ✅ Classificação de severidade (Leve, Moderada, Severa)
- ✅ Custos adicionais estimados (USD)
- ✅ Emissões adicionais de CO₂ (toneladas)
- ✅ Comparação de cenários (casco limpo vs sujo)

**Endpoints:**

- `POST /api/v1/predictions/` - Predição única
- `POST /api/v1/predictions/batch` - Predições em lote
- `POST /api/v1/predictions/scenario` - Comparação de cenários

### 2. **Gestão de Navios** 🚤

Informações completas sobre a frota:

- ✅ Listagem de todos os navios
- ✅ Detalhes de navios específicos
- ✅ Resumo de biofouling por navio
- ✅ Resumo consolidado da frota

**Endpoints:**

- `GET /api/v1/ships/` - Lista todos os navios
- `GET /api/v1/ships/{ship_name}` - Detalhes de um navio
- `GET /api/v1/ships/{ship_name}/summary` - Resumo de biofouling
- `GET /api/v1/ships/fleet/summary` - Resumo da frota completa

### 3. **Relatórios e Analytics** 📊

Análises detalhadas e relatórios:

- ✅ Relatório completo de biofouling com filtros
- ✅ Exportação de relatórios em CSV
- ✅ Estatísticas gerais da frota
- ✅ Identificação de navios de alto risco
- ✅ Distribuição de classificações
- ✅ Análise de custos e emissões

**Endpoints:**

- `GET /api/v1/reports/biofouling` - Relatório completo (com filtros)
- `GET /api/v1/reports/biofouling/export` - Exportar CSV
- `GET /api/v1/reports/statistics` - Estatísticas gerais
- `GET /api/v1/reports/high-risk` - Navios de alto risco

### 4. **Informações do Modelo** 🧠

Metadados sobre o modelo de ML:

- ✅ Informações do modelo carregado
- ✅ Lista de features utilizadas
- ✅ Importância das features
- ✅ Versão do modelo

**Endpoints:**

- `GET /api/v1/model/info` - Informações do modelo
- `GET /api/v1/model/features` - Importância das features

### 5. **Health Check e Status** ✅

Monitoramento do status da API:

- ✅ Health check da aplicação
- ✅ Status do modelo
- ✅ Informações de versão

**Endpoints:**

- `GET /` - Informações da API
- `GET /health` - Status de saúde

## 🗄️ Persistência de Dados

### Banco de Dados SQLite

- ✅ Armazena predições realizadas
- ✅ Armazena relatórios de eventos
- ✅ Fallback automático quando CSV não disponível
- ✅ Localização: `data/database/biofouling.db`

### Fontes de Dados

1. **CSV Processados** (prioridade)

   - `data/processed/biofouling_report.csv`
   - `data/processed/biofouling_summary_by_ship.csv`

2. **Banco de Dados** (fallback)
   - Tabelas: `predictions`, `reports`
   - Dados históricos e predições

## 🛠️ Tecnologias

- **FastAPI** - Framework web moderno e rápido
- **XGBoost** - Modelo de Machine Learning
- **SQLAlchemy** - ORM para banco de dados
- **Pandas** - Manipulação de dados
- **Pydantic** - Validação de dados
- **SQLite** - Banco de dados

## 🚀 Como Executar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Inicializar Banco de Dados (opcional - é criado automaticamente)

```bash
python init_database.py
```

### 3. Executar API

```bash
python run_api.py
```

A API estará disponível em:

- **API**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **Documentação ReDoc**: http://localhost:8000/redoc

## 📝 Exemplo de Uso

### Fazer uma Predição

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

### Resposta Esperada

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

### Executar Testes Completos

```bash
python test_api_complete.py
```

### Testes com APIs Externas

```bash
python test_api_complete.py --external
```

### Modo Verboso

```bash
python test_api_complete.py --verbose
```

## 📂 Estrutura do Backend

```
api/
├── main.py              # Aplicação FastAPI principal
├── config.py            # Configurações
├── database.py          # Configuração do banco de dados
├── services.py          # Lógica de negócio e ML
├── schemas.py           # Modelos Pydantic
└── routes/              # Endpoints da API
    ├── predictions.py   # Endpoints de predição
    ├── ships.py         # Endpoints de navios
    └── reports.py       # Endpoints de relatórios
```

## 🔧 Configurações

As configurações podem ser ajustadas em:

- `api/config.py` - Configurações da aplicação
- Variáveis de ambiente (`.env`) - Configurações específicas

### Principais Configurações

- `HOST`: Host da API (padrão: 0.0.0.0)
- `PORT`: Porta da API (padrão: 8000)
- `MODEL_FILE`: Arquivo do modelo ML
- `DATA_RAW_DIR`: Diretório de dados brutos
- `MODELS_DIR`: Diretório dos modelos

## 📈 Funcionalidades Principais

1. **Predição em Tempo Real** ⚡

   - Predições instantâneas via API
   - Suporte a predições em lote
   - Comparação de múltiplos cenários

2. **Analytics Avançado** 📊

   - Estatísticas detalhadas da frota
   - Identificação de navios críticos
   - Análise de custos e economia potencial

3. **Relatórios Flexíveis** 📄

   - Filtros por navio, data, severidade
   - Exportação em CSV
   - Paginação de resultados

4. **Gestão de Dados** 💾
   - Persistência automática
   - Fallback inteligente entre fontes
   - Histórico completo de predições

## 🔒 Segurança

- Validação de dados com Pydantic
- Tratamento robusto de erros
- Logs detalhados de requisições
- CORS configurável

## 📚 Documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🎯 Casos de Uso

1. **Previsão de Consumo**

   - Estimar consumo futuro de combustível
   - Calcular custos operacionais
   - Planejar orçamento

2. **Gestão de Manutenção**

   - Identificar navios que precisam de limpeza
   - Priorizar docagens baseado em impacto
   - Otimizar custos de manutenção

3. **Análise de Impacto Ambiental**

   - Calcular emissões de CO₂
   - Avaliar impacto do biofouling
   - Planejar estratégias sustentáveis

4. **Tomada de Decisão**
   - Comparar cenários diferentes
   - Analisar ROI de limpezas
   - Otimizar operações da frota

## 🚀 Próximas Melhorias

- [ ] Autenticação e autorização
- [ ] Cache de predições
- [ ] WebSockets para atualizações em tempo real
- [ ] Integração com sistemas externos
- [ ] Dashboard administrativo

---

**Versão**: 1.0.0  
**Última atualização**: 2025
