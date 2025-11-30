# Guia de Testes da API - Modelo Transpetro v2

Este documento descreve como executar os testes completos da API de predição de biofouling.

## Arquivos de Teste

### `test_api_complete.py`
Script completo de testes que inclui:
- ✅ Testes de todos os endpoints da API
- ✅ Suporte para APIs externas
- ✅ Tratamento robusto de erros
- ✅ Modo verboso para debug
- ✅ Relatório detalhado de resultados

### `run_tests.py`
Script simplificado para executar os testes facilmente.

## Instalação de Dependências

Certifique-se de ter todas as dependências instaladas:

```bash
pip install -r requirements.txt
```

## Executando os Testes

### 1. Testes Básicos

```bash
python test_api_complete.py
```

Executa todos os testes básicos da API local.

### 2. Testes com APIs Externas

```bash
python test_api_complete.py --external
```

Inclui testes de:
- API de clima (Open-Meteo)
- Taxa de câmbio (ExchangeRate-API)

### 3. Modo Verboso

```bash
python test_api_complete.py --verbose
```

Exibe informações detalhadas sobre cada teste, incluindo respostas completas e erros.

### 4. Todos os Testes

```bash
python test_api_complete.py --external --verbose
```

Executa todos os testes com informações detalhadas.

### 5. Usando o Script Simplificado

```bash
python run_tests.py
python run_tests.py --external
python run_tests.py --verbose
```

## Opções de Linha de Comando

- `--external`: Habilita testes de APIs externas
- `--verbose` ou `-v`: Modo verboso com informações detalhadas
- `--url URL`: Especifica URL alternativa da API (padrão: http://localhost:8000)

### Exemplos

```bash
# Testar API em servidor remoto
python test_api_complete.py --url http://192.168.1.100:8000

# Testes completos em modo verboso
python test_api_complete.py --external --verbose

# Apenas testes básicos
python test_api_complete.py
```

## Pré-requisitos

1. **API em execução**: A API deve estar rodando antes de executar os testes
   ```bash
   python run_api.py
   ```

2. **Dependências instaladas**:
   - requests
   - urllib3
   - Todas as dependências do `requirements.txt`

## Estrutura dos Testes

Os testes são organizados em categorias:

### 1. Health Check & Informações
- Root endpoint
- Health check
- Informações do modelo
- Importância das features

### 2. Predições
- Predição única
- Predições em lote
- Comparação de cenários

### 3. Navios
- Listar todos os navios
- Obter navio específico
- Resumo de navio
- Resumo da frota

### 4. Relatórios
- Relatório de biofouling
- Relatório com filtros
- Estatísticas gerais
- Navios de alto risco

### 5. APIs Externas (opcional)
- API de clima
- Taxa de câmbio

## Interpretando os Resultados

### Status dos Testes

- ✅ **[OK]**: Teste passou com sucesso
- ❌ **[ERRO]**: Teste falhou
- ⚠️ **[AVISO]**: Teste passou mas com avisos (ex: modelo não carregado)
- ℹ️ **[INFO]**: Informações adicionais

### Relatório Final

O script exibe um resumo final com:
- Total de testes executados
- Número de testes que passaram
- Número de testes que falharam
- Número de avisos
- Taxa de sucesso (%)

## Solução de Problemas

### Erro: "Não foi possível conectar à API"

**Solução**: Certifique-se de que a API está rodando:
```bash
python run_api.py
```

### Erro: "Modelo não carregado"

**Solução**: Este é um aviso, não um erro. O teste continua normalmente. Para carregar o modelo, verifique:
- Se os arquivos de modelo existem em `models/`
- Se os caminhos estão configurados corretamente

### Erro: "Endpoint não encontrado (404)"

**Solução**: 
- Verifique se a versão da API está correta
- Alguns endpoints podem não estar implementados ainda

### Erros de Encoding no Windows

**Solução**: O script já está configurado para lidar com encoding UTF-8 no Windows. Se ainda houver problemas:
- Execute em terminal compatível com UTF-8
- Use Git Bash ou WSL

## Integração com CI/CD

O script retorna códigos de saída apropriados para integração:

- `0`: Todos os testes passaram
- `1`: Alguns testes falharam

### Exemplo de uso em CI/CD:

```bash
python test_api_complete.py --external
if [ $? -eq 0 ]; then
    echo "Todos os testes passaram!"
else
    echo "Alguns testes falharam"
    exit 1
fi
```

## Contribuindo

Ao adicionar novos endpoints:
1. Adicione testes correspondentes em `test_api_complete.py`
2. Atualize este README se necessário
3. Execute os testes antes de fazer commit

## Notas

- Os testes de APIs externas podem falhar se não houver conexão com a internet
- Alguns testes podem dar avisos se o modelo não estiver carregado (isso é normal)
- O modo verboso é útil para debug mas produz muita saída

