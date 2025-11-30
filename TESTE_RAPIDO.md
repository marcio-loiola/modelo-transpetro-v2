# 🚀 Guia Rápido de Testes

## Como Executar

### 1. Certifique-se de que a API está rodando:
```bash
python run_api.py
```

### 2. Em outro terminal, execute os testes:

**Testes básicos:**
```bash
python test_api_complete.py
```

**Testes com APIs externas:**
```bash
python test_api_complete.py --external
```

**Modo verboso (mais detalhes):**
```bash
python test_api_complete.py --verbose
```

**Todos os testes:**
```bash
python test_api_complete.py --external --verbose
```

## O que foi criado:

✅ **test_api_complete.py** - Script completo de testes com:
- Correção de todos os erros do script anterior
- Suporte para consultar APIs externas (clima, câmbio)
- Tratamento robusto de erros
- Modo verboso para debug
- Relatórios detalhados

✅ **run_tests.py** - Script simplificado para executar testes

✅ **TEST_README.md** - Documentação completa

✅ **requirements.txt** - Atualizado com dependências necessárias (requests, urllib3)

## Principais Melhorias:

1. ✅ Erros corrigidos:
   - Problema com list vs dict nos endpoints de navios
   - Tratamento de respostas 404/503
   - Encoding UTF-8 no Windows

2. ✅ Suporte para APIs externas:
   - API de clima (Open-Meteo)
   - Taxa de câmbio (ExchangeRate-API)
   - Configurável via flag --external

3. ✅ Funcionalidades similares ao api.logbio:
   - Estrutura similar de testes
   - Suporte para consultas externas
   - Relatórios detalhados

4. ✅ Robustez:
   - Retry automático em requisições
   - Timeouts configuráveis
   - Tratamento de erros de rede
   - Modo verboso para debug

## Estrutura dos Testes:

```
1. Health Check & Informações
   - Root endpoint
   - Health check  
   - Model info
   - Feature importances

2. Predições
   - Predição única
   - Predições em lote
   - Comparação de cenários

3. Navios
   - Listar navios
   - Obter navio específico
   - Resumo de navio
   - Resumo da frota

4. Relatórios
   - Relatório biofouling
   - Relatório com filtros
   - Estatísticas gerais
   - Navios de alto risco

5. APIs Externas (--external)
   - API de clima
   - Taxa de câmbio
```

## Exemplo de Saída:

```
======================================================================
            TESTE COMPLETO DA API - BIOFOULING PREDICTION             
======================================================================

> Root Endpoint ... [OK] OK
> Health Check ... [OK] OK
> Model Info ... [OK] OK
...

======================================================================
                          RESUMO DOS TESTES                           
======================================================================

Total de testes: 15
[OK] Passou: 12
[ERRO] Falhou: 0
[AVISO] Avisos: 3

Taxa de sucesso: 100.0%

[SUCESSO] Todos os testes passaram!
```

## Próximos Passos:

Se quiser adicionar mais funcionalidades do api.logbio (dashboard, logbooks, etc.), os testes podem ser facilmente estendidos adicionando novos métodos na classe `APITester`.

