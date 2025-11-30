# 🔌 Arquitetura de Microserviços - Biofouling Service

## Visão Geral

Este serviço foi projetado para funcionar como um **microserviço** em uma arquitetura maior, podendo ser integrado com outras APIs e sistemas.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│                    (Kong, AWS API Gateway, Azure APIM)                      │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
         ┌──────────▼──────────┐   ┌──────────▼──────────┐
         │   Other Services    │   │  Biofouling Service │
         │  (Fleet, Crew, etc) │   │     (This API)      │
         └─────────────────────┘   └──────────┬──────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              │                               │                               │
    ┌─────────▼─────────┐         ┌──────────▼──────────┐        ┌───────────▼───────────┐
    │   Weather API     │         │  Vessel Tracking    │        │    Fuel Prices API    │
    │  (Sea Conditions) │         │   (AIS/Position)    │        │    (Bunker Prices)    │
    └───────────────────┘         └─────────────────────┘        └───────────────────────┘
              │                               │                               │
    ┌─────────▼─────────┐         ┌──────────▼──────────┐
    │  Maintenance API  │         │   Emissions API     │
    │ (Drydock/Cleaning)│         │   (IMO DCS/MRV)     │
    └───────────────────┘         └─────────────────────┘
```

## Componentes

### 1. 🧠 Core Service (Local)

- **ML Model**: XGBoost para predição de biofouling
- **Data Processing**: Engenharia de features
- **Analysis Engine**: Cálculos de consumo, custos, emissões

### 2. 🌐 External API Clients

Clientes HTTP assíncronos para integração com:

| API                 | Propósito           | Dados                     |
| ------------------- | ------------------- | ------------------------- |
| **Weather API**     | Condições marítimas | Beaufort, ondas, vento    |
| **Vessel Tracking** | Rastreamento AIS    | Posição, velocidade, rota |
| **Fuel Prices**     | Preços de bunker    | USD/ton por porto         |
| **Maintenance API** | Agendamento         | Histórico de limpezas     |
| **Emissions API**   | Reporting IMO       | CO2, consumo, viagens     |

### 3. 🔧 Integration Service

Orquestrador que combina dados de múltiplas fontes:

```python
# Predição enriquecida com dados externos
result = await integrated_service.get_enhanced_prediction(
    vessel_id="9123456",
    prediction_request={
        "speed": 12.5,
        "displacement": 50000,
        "days_since_cleaning": 180,
        "latitude": -23.95,
        "longitude": -46.30
    }
)
# Retorna predição ML + condições do mar + preços + histórico
```

## Endpoints de Integração

### `/api/v1/integrations/health`

Status de todas as APIs externas configuradas.

### `/api/v1/integrations/predictions/enhanced`

Predição enriquecida com dados de múltiplas fontes.

### `/api/v1/integrations/fleet/optimization`

Relatório de otimização para toda a frota.

### `/api/v1/integrations/vessels/{id}/emissions`

Submissão de emissões para API regulatória.

### `/api/v1/integrations/vessels/{id}/cleaning-recommendation`

Recomendação de limpeza baseada em múltiplos fatores.

## Configuração

### Variáveis de Ambiente

```env
# APIs Externas
WEATHER_API_URL=https://api.weather-service.com/v1
WEATHER_API_KEY=your-key

VESSEL_API_URL=https://api.ais-tracking.com/v2
VESSEL_API_KEY=your-key

FUEL_API_URL=https://api.bunker-prices.com/v1
FUEL_API_KEY=your-key

MAINTENANCE_API_URL=https://your-maintenance-system.com/api
MAINTENANCE_API_KEY=your-key

EMISSIONS_API_URL=https://api.emissions-reporting.com/v1
EMISSIONS_API_KEY=your-key

# Service Mesh
SERVICE_REGISTRY_URL=http://consul:8500
SERVICE_NAME=biofouling-service

# Observability
OTEL_ENABLED=true
OTEL_EXPORTER_ENDPOINT=http://jaeger:4317
```

## Padrões Implementados

### Circuit Breaker

Protege contra falhas em cascata:

```python
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30
```

### Retry with Backoff

Tentativas automáticas com delay exponencial:

```python
max_retries=3
retry_delay=1.0 * (attempt + 1)
```

### Caching

Cache em memória para reduzir chamadas:

```python
# Dados de clima: 1 hora
# Preços de combustível: 1 hora
```

### Health Checks

Endpoint `/api/v1/integrations/health` para orchestração:

```json
{
  "status": "healthy",
  "services": {
    "biofouling_model": { "loaded": true },
    "external_apis": {
      "weather": true,
      "vessel_tracking": true,
      "fuel_prices": true,
      "maintenance": false,
      "emissions": false
    }
  }
}
```

## Exemplo de Uso em Backend Maior

```python
# Em outro microserviço
import httpx

BIOFOULING_SERVICE_URL = "http://biofouling-service:8000"

async def get_fleet_status():
    async with httpx.AsyncClient() as client:
        # Obter predição enriquecida
        response = await client.post(
            f"{BIOFOULING_SERVICE_URL}/api/v1/integrations/predictions/enhanced",
            json={
                "vessel_id": "9123456",
                "speed": 12.5,
                "displacement": 50000,
                "draft": 10.2,
                "days_since_cleaning": 180,
                "latitude": -23.95,
                "longitude": -46.30,
                "port": "BRSSZ"
            }
        )
        return response.json()
```

## Docker Compose (Exemplo)

```yaml
version: "3.8"

services:
  biofouling-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WEATHER_API_URL=${WEATHER_API_URL}
      - WEATHER_API_KEY=${WEATHER_API_KEY}
      - VESSEL_API_URL=${VESSEL_API_URL}
      - VESSEL_API_KEY=${VESSEL_API_KEY}
    depends_on:
      - redis

  fleet-service:
    build: ./fleet-service
    ports:
      - "8001:8001"
    environment:
      - BIOFOULING_SERVICE_URL=http://biofouling-service:8000

  api-gateway:
    image: kong:latest
    ports:
      - "80:8000"
    depends_on:
      - biofouling-service
      - fleet-service
```

## Próximos Passos

1. **Kubernetes Deployment**: Helm charts para deploy em K8s
2. **Service Mesh**: Istio/Linkerd para observability
3. **Event-Driven**: Kafka/RabbitMQ para eventos assíncronos
4. **GraphQL Federation**: Schema stitching com outros serviços
