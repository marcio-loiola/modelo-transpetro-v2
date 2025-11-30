# 🎨 Guia de Integração Frontend - Transpetro Biofouling

Este guia descreve como consumir a API Backend para construir as interfaces visuais do sistema de monitoramento de biofouling.

## 🔐 1. Tela de Login (Tela 2)

**Nota:** O sistema de autenticação (JWT/OAuth) está listado como uma melhoria futura na API.

- **Ação Recomendada:** Para o protótipo/MVP, implementar um login simulado no frontend.
- **Fluxo:** O login deve aceitar **CPF** ou **Matrícula**.
  - **CPF:** Formato padrão `000.000.000-00` (Exemplo para testes: `080.973.623-33`).
  - **Matrícula:** Número de 6 dígitos (Exemplo para testes: `473740`).
  - **Validação:** O frontend deve aplicar máscara de input para CPF ou validar os 6 dígitos da matrícula.
  - **Persistência:** Armazenar um token fictício no LocalStorage para manter a sessão ativa.

## 🚢 2. Visão da Frota (Dashboard Principal)

Esta tela oferece uma visão macro da operação.

### 📊 KPIs da Frota (Topo)

- **Dados Necessários:** Total de navios, alertas críticos, prejuízo diário total, CO2 evitado.
- **Endpoint:** `GET /api/v1/reports/statistics`
- **Mapeamento:**
  - `total_ships` -> "Navios Monitorados"
  - `critical_alerts` -> "Alertas Críticos"
  - `total_loss_usd` -> "Prejuízo Diário (Bio)"
  - `co2_avoided` -> "CO2 Evitado"

### 🗺️ Mapa e Lista de Risco (Inferior)

- **Dados Necessários:** Lista de navios com suas coordenadas (se disponíveis) e nível de risco.
- **Endpoint:** `GET /api/v1/ships/fleet/summary`
- **Uso:**
  - Iterar sobre a lista retornada.
  - Usar `bio_class` (Leve, Moderada, Severa) para colorir os ícones no mapa e as barras de progresso na lista "Prioridades de Atenção".
  - Filtrar/Ordenar por `bio_index` decrescente para a lista de prioridades.

## ⚓ 3. Visão de Navio - Dados Básicos

Detalhes técnicos e cadastrais de uma embarcação específica.

### 🔽 Seletor de Navio

- **Endpoint:** `GET /api/v1/ships/`
- **Uso:** Preencher o dropdown com a lista de nomes de navios (`ship_name`).

### 📋 Atributos e Especificações

- **Endpoint:** `GET /api/v1/ships/{ship_name}`
- **Mapeamento:**
  - `type`, `class` -> "Tipo", "Classe"
  - `dimensions` (length, beam, draft) -> "Comprimento", "Boca", "Calado"
  - `coating_info` -> "Especificações de Revestimento" (Tipo de tinta, data aplicação).

### ⚠️ Status Atual

- **Endpoint:** `GET /api/v1/ships/{ship_name}/summary`
- **Mapeamento:**
  - `bio_index` -> Nível do alerta (ex: "Nível 3 - Alerta").

## 📡 4. Visão de Navio - Radar Operacional

Monitoramento de performance e condições em tempo real.

### ⏱️ Métricas Atuais (Topo)

- **Endpoint:** `GET /api/v1/ships/{ship_name}/summary`
- **Mapeamento:**
  - `current_consumption` -> "Consumo (t)"
  - `speed` -> "Velocidade (nós)"
  - `weather_condition` -> "Condição Mar (BFT)"
  - `risk_percentage` -> "Risco Bio (%)"

### 📈 Gráfico de Performance

- **Endpoint:** `GET /api/v1/reports/biofouling`
- **Parâmetros:** `?ship_name={NOME}&days=30` (para pegar histórico recente).
- **Uso:**
  - Eixo X: `date`
  - Eixo Y: `excess_consumption` ou `bio_index`.
  - Plotar a linha de tendência para visualizar a degradação da performance.

### 🚨 Alertas (NORMAM 401)

- **Lógica Frontend:** Se `bio_class` == "Severa" ou `bio_index` > 7, exibir o banner vermelho de alerta sugerindo inspeção.

## 💰 5. Visão de Navio - Financeiro

Calculadora de impacto econômico e decisão de limpeza.

### 💵 Calculadora de Payback

- **Endpoint:** `POST /api/v1/predictions/scenario`
- **Payload (Exemplo):**
  ```json
  {
    "ship_name": "Rafael Santos",
    "current_state": { ...dados atuais... },
    "simulated_state": { "days_since_cleaning": 0 } // Simula casco limpo
  }
  ```
- **Uso:**
  - A API retornará a diferença de consumo (`savings_fuel_tons`).
  - **Frontend:**
    - Input `Preço Combustível` (USD/ton).
    - Input `Custo Limpeza` (USD).
    - Cálculo: `Prejuízo Diário` = `savings_fuel_tons` \* `Preço Combustível`.
    - Cálculo: `Payback (dias)` = `Custo Limpeza` / `Prejuízo Diário`.
  - **Lógica de Decisão:** Se `Payback` < X dias (ex: 90 dias), exibir recomendação de limpeza. Caso contrário, exibir "Aguardar".

## 📚 6. Referência de Dados

### Enum: BiofoulingClass

Valores possíveis para classificação de risco (`bio_class`):

- `"Leve"` - Baixo risco, operação normal.
- `"Moderada"` - Atenção necessária, monitorar performance.
- `"Severa"` - Alto risco, planejar limpeza/inspeção.
- `"Unknown"` - Dados insuficientes.

### Estrutura de Resposta de Erro

```json
{
  "detail": "Mensagem descritiva do erro",
  "error_code": "CODE_OPTIONAL",
  "timestamp": "2023-10-27T10:00:00"
}
```
