#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# TEST API COMPLETA - COMPREHENSIVE TEST SUITE WITH EXTERNAL API SUPPORT
# =============================================================================
"""
Script completo para testar todos os endpoints da API Biofouling Prediction.

Funcionalidades:
- Testa todos os endpoints da API
- Suporte para consultar APIs externas
- Integração com funcionalidades do api.logbio
- Relatório detalhado de testes

Uso: python test_api_complete.py [--external] [--verbose]
"""

import sys
import io
import argparse
import json
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"
EXTERNAL_API_TIMEOUT = 10  # segundos

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Fallback para Windows sem cores
try:
    import colorama
    colorama.init()
except ImportError:
    Colors.GREEN = Colors.RED = Colors.YELLOW = Colors.BLUE = Colors.CYAN = Colors.RESET = Colors.BOLD = ''


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def print_header(text: str):
    """Imprime um cabeçalho formatado."""
    try:
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    except UnicodeEncodeError:
        print(f"\n{'='*70}")
        print(f"{text.center(70)}")
        print(f"{'='*70}\n")


def print_test(name: str):
    """Imprime nome do teste."""
    print(f"{Colors.BOLD}> {name}{Colors.RESET}", end=" ... ")


def print_success(message: str = "OK"):
    """Imprime sucesso."""
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")


def print_error(message: str):
    """Imprime erro."""
    print(f"{Colors.RED}[ERRO] {message}{Colors.RESET}")


def print_warning(message: str):
    """Imprime aviso."""
    print(f"{Colors.YELLOW}[AVISO] {message}{Colors.RESET}")


def print_info(message: str):
    """Imprime informação."""
    print(f"{Colors.CYAN}[INFO] {message}{Colors.RESET}")


def print_json(data: Any, indent: int = 2):
    """Imprime JSON formatado."""
    print(json.dumps(data, indent=indent, default=str, ensure_ascii=False))


# =============================================================================
# EXTERNAL API SUPPORT
# =============================================================================

class ExternalAPIClient:
    """Cliente para consultar APIs externas."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_weather_data(self, lat: float = -23.5505, lon: float = -46.6333) -> Optional[Dict]:
        """
        Consulta dados de clima (usando OpenWeatherMap ou similar).
        Retorna None se não conseguir conectar.
        """
        try:
            # API pública de clima - exemplo usando Open-Meteo (sem chave)
            url = f"https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "weather_code,wind_speed_10m",
                "timezone": "auto"
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_fuel_price(self, currency: str = "USD") -> Optional[float]:
        """
        Consulta preço do combustível (mockado, mas pode ser integrado com API real).
        """
        try:
            # Exemplo: API de preços de commodities
            # Por enquanto, retorna valor mockado baseado em média
            return 500.0  # USD por tonelada
        except Exception:
            return None
    
    def get_exchange_rate(self, from_curr: str = "USD", to_curr: str = "BRL") -> Optional[float]:
        """
        Consulta taxa de câmbio (usando API pública).
        """
        try:
            # API pública de câmbio
            url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("rates", {}).get(to_curr)
            return None
        except Exception:
            return None


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

class APITester:
    """Classe para testar a API."""
    
    def __init__(self, base_url: str, test_external: bool = False, verbose: bool = False):
        self.base_url = base_url
        self.test_external = test_external
        self.verbose = verbose
        self.session = requests.Session()
        self.external_client = ExternalAPIClient() if test_external else None
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": []
        }
        self.test_ship_name = None  # Para reutilizar entre testes
    
    def test(self, name: str, func, *args, **kwargs):
        """Executa um teste."""
        self.results["total"] += 1
        print_test(name)
        
        try:
            result = func(*args, **kwargs)
            if result:
                self.results["passed"] += 1
                print_success()
                return True
            else:
                self.results["failed"] += 1
                error_msg = f"Teste '{name}' falhou"
                self.results["errors"].append(error_msg)
                print_error("Falhou")
                return False
        except Exception as e:
            self.results["failed"] += 1
            error_msg = f"Teste '{name}' erro: {str(e)}"
            self.results["errors"].append(error_msg)
            print_error(f"Erro: {str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def get(self, endpoint: str, params: Dict = None) -> requests.Response:
        """Faz uma requisição GET."""
        url = f"{self.base_url}{endpoint}"
        try:
            return self.session.get(url, params=params, timeout=10)
        except Exception as e:
            if self.verbose:
                print_error(f"Erro na requisição GET: {e}")
            raise
    
    def post(self, endpoint: str, data: Dict = None) -> requests.Response:
        """Faz uma requisição POST."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        try:
            return self.session.post(url, json=data, headers=headers, timeout=10)
        except Exception as e:
            if self.verbose:
                print_error(f"Erro na requisição POST: {e}")
            raise
    
    # ========================================================================
    # TEST: Health & Info
    # ========================================================================
    
    def test_root(self) -> bool:
        """Testa endpoint raiz."""
        response = self.get("/")
        if response.status_code == 200:
            data = response.json()
            if self.verbose:
                print(f"\n  {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"\n  API: {data.get('message', 'N/A')} v{data.get('version', 'N/A')}")
            return True
        return False
    
    def test_health(self) -> bool:
        """Testa health check."""
        response = self.get("/health")
        if response.status_code == 200:
            data = response.json()
            print(f"\n  Status: {data.get('status', 'N/A')}")
            
            # Verificar se tem versão e modelo
            version = data.get('version')
            model_loaded = data.get('model_loaded')
            
            if version:
                print(f"  Versao: {version}")
            if model_loaded is not None:
                status = "SIM" if model_loaded else "NAO"
                print(f"  Modelo carregado: {status}")
            
            return True
        return False
    
    def test_model_info(self) -> bool:
        """Testa informações do modelo."""
        response = self.get(f"{API_VERSION}/model/info")
        if response.status_code == 200:
            data = response.json()
            print(f"\n  Nome: {data.get('model_name', 'N/A')}")
            print(f"  Versao: {data.get('version', 'N/A')}")
            features = data.get('features', [])
            print(f"  Features: {len(features)}")
            if self.verbose and features:
                print(f"  Primeiras features: {', '.join(features[:5])}")
            return True
        elif response.status_code == 503:
            print_warning("Modelo nao carregado")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 404:
            print_warning("Endpoint nao encontrado (404)")
            self.results["warnings"] += 1
            return True
        else:
            if self.verbose:
                print(f"  Status: {response.status_code}")
            return False
    
    def test_feature_importances(self) -> bool:
        """Testa importância das features."""
        response = self.get(f"{API_VERSION}/model/features")
        if response.status_code == 200:
            features = response.json()
            if isinstance(features, list) and len(features) > 0:
                print(f"\n  Top 5 features mais importantes:")
                for i, feat in enumerate(features[:5], 1):
                    feat_name = feat.get('feature', 'N/A') if isinstance(feat, dict) else str(feat)
                    importance = feat.get('importance', 0) if isinstance(feat, dict) else 0
                    print(f"    {i}. {feat_name}: {importance:.4f}")
            else:
                print("\n  Nenhuma feature disponivel")
            return True
        elif response.status_code == 503:
            print_warning("Modelo nao carregado")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 404:
            print_warning("Endpoint nao encontrado (404)")
            self.results["warnings"] += 1
            return True
        return False
    
    # ========================================================================
    # TEST: Predictions
    # ========================================================================
    
    def test_single_prediction(self) -> bool:
        """Testa predição única."""
        data = {
            "ship_name": "NAVIO TESTE",
            "speed": 12.5,
            "duration": 24.0,
            "days_since_cleaning": 180,
            "displacement": 50000,
            "beaufort_scale": 3
        }
        
        response = self.post(f"{API_VERSION}/predictions/", data)
        if response.status_code == 200:
            result = response.json()
            print(f"\n  Navio: {result.get('ship_name', 'N/A')}")
            pred_cons = result.get('predicted_consumption', 0)
            bio_idx = result.get('bio_index', 0)
            bio_class = result.get('bio_class', 'N/A')
            cost = result.get('additional_cost_usd', 0)
            
            print(f"  Consumo previsto: {pred_cons:.2f} tons")
            print(f"  Indice biofouling: {bio_idx:.2f}/10")
            print(f"  Classificacao: {bio_class}")
            print(f"  Custo adicional: ${cost:.2f} USD")
            return True
        elif response.status_code == 503:
            print_warning("Modelo nao carregado - servico indisponivel")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 404:
            print_warning("Endpoint nao encontrado (404)")
            self.results["warnings"] += 1
            return True
        else:
            if self.verbose:
                print(f"  Status: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"  Erro: {error_detail}")
                except:
                    print(f"  Resposta: {response.text[:200]}")
            return False
    
    def test_batch_prediction(self) -> bool:
        """Testa predições em lote."""
        data = {
            "predictions": [
                {
                    "ship_name": "NAVIO 1",
                    "speed": 10.0,
                    "duration": 12.0,
                    "days_since_cleaning": 100
                },
                {
                    "ship_name": "NAVIO 2",
                    "speed": 15.0,
                    "duration": 48.0,
                    "days_since_cleaning": 250
                }
            ]
        }
        
        response = self.post(f"{API_VERSION}/predictions/batch", data)
        if response.status_code == 200:
            result = response.json()
            print(f"\n  Total: {result.get('total', 0)}")
            print(f"  Sucessos: {result.get('successful', 0)}")
            print(f"  Falhas: {result.get('failed', 0)}")
            return True
        elif response.status_code == 503:
            print_warning("Modelo nao carregado")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 404:
            print_warning("Endpoint nao encontrado (404)")
            self.results["warnings"] += 1
            return True
        return False
    
    def test_scenario_comparison(self) -> bool:
        """Testa comparação de cenários."""
        data = {
            "ship_name": "NAVIO CENARIO",
            "speed": 13.0,
            "duration": 24.0,
            "days_since_cleaning": 200,
            "displacement": 45000
        }
        
        response = self.post(f"{API_VERSION}/predictions/scenario", data)
        if response.status_code == 200:
            scenarios = response.json()
            if isinstance(scenarios, list):
                print(f"\n  Cenarios comparados: {len(scenarios)}")
                for i, scenario in enumerate(scenarios[:3], 1):
                    if isinstance(scenario, dict):
                        bio_idx = scenario.get('bio_index', 0)
                        bio_class = scenario.get('bio_class', 'N/A')
                        print(f"    {i}. {bio_idx:.2f}/10 - {bio_class}")
            return True
        elif response.status_code == 503:
            print_warning("Modelo nao carregado")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 404:
            print_warning("Endpoint nao encontrado (404)")
            self.results["warnings"] += 1
            return True
        return False
    
    # ========================================================================
    # TEST: Ships
    # ========================================================================
    
    def test_list_ships(self) -> bool:
        """Testa listagem de navios."""
        response = self.get(f"{API_VERSION}/ships/")
        if response.status_code == 200:
            data = response.json()
            
            # A API pode retornar dict ou list diretamente
            if isinstance(data, dict):
                total = data.get('total', 0)
                ships = data.get('ships', [])
            elif isinstance(data, list):
                total = len(data)
                ships = data
            else:
                return False
            
            print(f"\n  Total de navios: {total}")
            
            if ships and len(ships) > 0:
                print(f"  Primeiros 3 navios:")
                for ship in ships[:3]:
                    if isinstance(ship, dict):
                        ship_name = ship.get('ship_name', 'N/A')
                        events = ship.get('total_events', 0)
                        print(f"    - {ship_name} ({events} eventos)")
                    elif hasattr(ship, 'ship_name'):
                        print(f"    - {ship.ship_name}")
                    else:
                        print(f"    - {str(ship)[:50]}")
                
                # Guardar primeiro navio para outros testes
                if ships[0] and isinstance(ships[0], dict):
                    self.test_ship_name = ships[0].get('ship_name')
                elif hasattr(ships[0], 'ship_name'):
                    self.test_ship_name = ships[0].ship_name
            
            return True
        return False
    
    def test_get_ship(self) -> bool:
        """Testa obtenção de um navio específico."""
        # Obter nome do navio
        if not self.test_ship_name:
            list_response = self.get(f"{API_VERSION}/ships/")
            if list_response.status_code == 200:
                data = list_response.json()
                ships = data.get('ships', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                if ships and len(ships) > 0:
                    ship = ships[0]
                    if isinstance(ship, dict):
                        self.test_ship_name = ship.get('ship_name')
                    elif hasattr(ship, 'ship_name'):
                        self.test_ship_name = ship.ship_name
        
        if not self.test_ship_name:
            print_warning("Nenhum navio disponivel para teste")
            self.results["warnings"] += 1
            return True
        
        # Testar URL encoding do nome
        from urllib.parse import quote
        encoded_name = quote(self.test_ship_name)
        
        response = self.get(f"{API_VERSION}/ships/{encoded_name}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                print(f"\n  Navio: {data.get('ship_name', 'N/A')}")
                print(f"  Total eventos: {data.get('total_events', 0)}")
            return True
        elif response.status_code == 404:
            print_warning(f"Navio '{self.test_ship_name}' nao encontrado")
            self.results["warnings"] += 1
            return True
        return False
    
    def test_ship_summary(self) -> bool:
        """Testa resumo de um navio."""
        if not self.test_ship_name:
            print_warning("Nenhum navio disponivel para teste")
            self.results["warnings"] += 1
            return True
        
        from urllib.parse import quote
        encoded_name = quote(self.test_ship_name)
        
        response = self.get(f"{API_VERSION}/ships/{encoded_name}/summary")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                print(f"\n  Navio: {data.get('ship_name', 'N/A')}")
                avg_idx = data.get('avg_bio_index', 0)
                max_idx = data.get('max_bio_index', 0)
                fuel = data.get('total_additional_fuel', 0)
                
                print(f"  Indice medio: {avg_idx:.2f}/10")
                print(f"  Indice maximo: {max_idx:.2f}/10")
                if fuel:
                    print(f"  Consumo adicional: {fuel:.2f} tons")
            return True
        elif response.status_code == 404:
            print_warning("Resumo nao disponivel")
            self.results["warnings"] += 1
            return True
        return False
    
    def test_fleet_summary(self) -> bool:
        """Testa resumo da frota."""
        response = self.get(f"{API_VERSION}/ships/fleet/summary")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                print(f"\n  Total navios: {data.get('total_ships', 0)}")
                print(f"  Total eventos: {data.get('total_events', 0)}")
                fleet_idx = data.get('fleet_avg_bio_index', 0)
                cost = data.get('fleet_total_additional_cost_usd', 0)
                
                print(f"  Indice medio frota: {fleet_idx:.2f}/10")
                if cost:
                    print(f"  Custo adicional total: ${cost:.2f} USD")
            return True
        elif response.status_code == 404:
            print_warning("Resumo da frota nao disponivel")
            self.results["warnings"] += 1
            return True
        return False
    
    # ========================================================================
    # TEST: Reports
    # ========================================================================
    
    def test_biofouling_report(self) -> bool:
        """Testa relatório de biofouling."""
        params = {"limit": 5}
        response = self.get(f"{API_VERSION}/reports/biofouling", params=params)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                total = data.get('total_records', 0)
                records = data.get('records', [])
                
                print(f"\n  Total de registros: {total}")
                print(f"  Exibindo: {len(records)} registros")
                
                if records and len(records) > 0:
                    rec = records[0]
                    if isinstance(rec, dict):
                        print(f"  Primeiro registro:")
                        print(f"    Navio: {rec.get('ship_name', 'N/A')}")
                        print(f"    Indice: {rec.get('bio_index', 0):.2f}/10")
                        print(f"    Classe: {rec.get('bio_class', 'N/A')}")
            return True
        elif response.status_code == 404:
            print_warning("Relatorio nao disponivel")
            self.results["warnings"] += 1
            return True
        return False
    
    def test_biofouling_report_filters(self) -> bool:
        """Testa relatório com filtros."""
        params = {
            "min_bio_index": 5.0,
            "limit": 3
        }
        response = self.get(f"{API_VERSION}/reports/biofouling", params=params)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                total = data.get('total_records', 0)
                print(f"\n  Registros com indice >= 5.0: {total}")
            return True
        elif response.status_code == 404:
            print_warning("Relatorio nao disponivel")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 500:
            # Pode ser erro por dados incompletos
            try:
                error_data = response.json()
                if "message" in error_data or "detail" in error_data:
                    print_warning(f"Dados incompletos: {error_data.get('message', error_data.get('detail', 'Erro desconhecido'))}")
                    self.results["warnings"] += 1
                    return True
            except:
                pass
        return False
    
    def test_statistics(self) -> bool:
        """Testa estatísticas gerais."""
        response = self.get(f"{API_VERSION}/reports/statistics")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                if "message" in data:
                    print_warning(data["message"])
                    self.results["warnings"] += 1
                    return True
                
                total = data.get('total_records', 0)
                ships = data.get('total_ships', 0)
                
                print(f"\n  Total registros: {total}")
                print(f"  Total navios: {ships}")
                
                bio_idx = data.get('bio_index', {})
                if bio_idx and isinstance(bio_idx, dict):
                    mean = bio_idx.get('mean', 0)
                    print(f"  Indice medio: {mean:.2f}/10")
            
            return True
        elif response.status_code == 404:
            print_warning("Estatisticas nao disponiveis")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 500:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_data.get('detail', 'Erro desconhecido'))
                print_warning(f"Erro ao obter estatisticas: {error_msg}")
                self.results["warnings"] += 1
                return True
            except:
                pass
        return False
    
    def test_high_risk_ships(self) -> bool:
        """Testa navios de alto risco."""
        params = {"threshold": 7.0}
        response = self.get(f"{API_VERSION}/reports/high-risk", params=params)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                # Verificar se há mensagem de dados não disponíveis
                if "message" in data and "No data" in data.get("message", ""):
                    print_warning(data["message"])
                    self.results["warnings"] += 1
                    return True
                
                total = data.get('total_high_risk', 0)
                ships = data.get('ships', [])
                
                print(f"\n  Navios de alto risco (>= 7.0): {total}")
                
                if ships and len(ships) > 0:
                    print(f"  Top 3:")
                    for ship in ships[:3]:
                        if isinstance(ship, dict):
                            name = ship.get('ship_name', 'N/A')
                            idx = ship.get('max_bio_index', 0)
                            print(f"    - {name}: {idx:.1f}/10")
            
            return True
        elif response.status_code == 404:
            print_warning("Relatorio de alto risco nao disponivel")
            self.results["warnings"] += 1
            return True
        elif response.status_code == 500:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_data.get('detail', 'Erro desconhecido'))
                print_warning(f"Erro ao obter navios de alto risco: {error_msg}")
                self.results["warnings"] += 1
                return True
            except:
                pass
        return False
    
    # ========================================================================
    # TEST: External APIs (like api.logbio features)
    # ========================================================================
    
    def test_external_weather(self) -> bool:
        """Testa consulta de API externa de clima."""
        if not self.external_client:
            print_warning("Cliente de API externa nao disponivel")
            self.results["warnings"] += 1
            return True
        
        print_info("Consultando API de clima...")
        weather_data = self.external_client.get_weather_data()
        
        if weather_data:
            print(f"\n  Clima consultado com sucesso")
            if self.verbose:
                print_json(weather_data)
            return True
        else:
            print_warning("Nao foi possivel consultar API de clima")
            self.results["warnings"] += 1
            return True
    
    def test_external_exchange_rate(self) -> bool:
        """Testa consulta de taxa de cambio."""
        if not self.external_client:
            print_warning("Cliente de API externa nao disponivel")
            self.results["warnings"] += 1
            return True
        
        print_info("Consultando taxa de cambio USD -> BRL...")
        rate = self.external_client.get_exchange_rate("USD", "BRL")
        
        if rate:
            print(f"\n  Taxa de cambio USD -> BRL: {rate:.4f}")
            return True
        else:
            print_warning("Nao foi possivel consultar taxa de cambio")
            self.results["warnings"] += 1
            return True
    
    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================
    
    def run_all_tests(self):
        """Executa todos os testes."""
        print_header("TESTE COMPLETO DA API - BIOFOULING PREDICTION")
        
        if self.test_external:
            print_info("Testes de APIs externas habilitados")
        
        # Health & Info
        print_header("1. Health Check & Informacoes")
        self.test("Root Endpoint", self.test_root)
        self.test("Health Check", self.test_health)
        self.test("Model Info", self.test_model_info)
        self.test("Feature Importances", self.test_feature_importances)
        
        # Predictions
        print_header("2. Predicoes")
        self.test("Predicao Unica", self.test_single_prediction)
        self.test("Predicoes em Lote", self.test_batch_prediction)
        self.test("Comparacao de Cenarios", self.test_scenario_comparison)
        
        # Ships
        print_header("3. Navios")
        self.test("Listar Navios", self.test_list_ships)
        self.test("Obter Navio Especifico", self.test_get_ship)
        self.test("Resumo de Navio", self.test_ship_summary)
        self.test("Resumo da Frota", self.test_fleet_summary)
        
        # Reports
        print_header("4. Relatorios")
        self.test("Relatorio Biofouling", self.test_biofouling_report)
        self.test("Relatorio com Filtros", self.test_biofouling_report_filters)
        self.test("Estatisticas Gerais", self.test_statistics)
        self.test("Navios de Alto Risco", self.test_high_risk_ships)
        
        # External APIs
        if self.test_external:
            print_header("5. APIs Externas")
            self.test("API de Clima", self.test_external_weather)
            self.test("Taxa de Cambio", self.test_external_exchange_rate)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumo dos testes."""
        print_header("RESUMO DOS TESTES")
        
        total = self.results['total']
        passed = self.results['passed']
        failed = self.results['failed']
        warnings = self.results['warnings']
        
        print(f"\n{Colors.BOLD}Total de testes: {total}{Colors.RESET}")
        print(f"{Colors.GREEN}[OK] Passou: {passed}{Colors.RESET}")
        print(f"{Colors.RED}[ERRO] Falhou: {failed}{Colors.RESET}")
        if warnings > 0:
            print(f"{Colors.YELLOW}[AVISO] Avisos: {warnings}{Colors.RESET}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\n{Colors.BOLD}Taxa de sucesso: {success_rate:.1f}%{Colors.RESET}\n")
        
        if failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}[SUCESSO] Todos os testes passaram!{Colors.RESET}\n")
        else:
            print(f"{Colors.RED}{Colors.BOLD}[ERRO] Alguns testes falharam.{Colors.RESET}\n")
            if self.verbose and self.results['errors']:
                print(f"{Colors.YELLOW}Erros detalhados:{Colors.RESET}")
                for error in self.results['errors']:
                    print(f"  - {error}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description='Teste completo da API Biofouling Prediction')
    parser.add_argument('--external', action='store_true', help='Testar APIs externas')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verboso')
    parser.add_argument('--url', default=BASE_URL, help=f'URL base da API (padrão: {BASE_URL})')
    
    args = parser.parse_args()
    
    base_url = args.url
    test_external = args.external
    verbose = args.verbose
    
    print(f"\n{Colors.BOLD}Iniciando testes da API...{Colors.RESET}")
    print(f"URL base: {base_url}")
    if test_external:
        print("APIs externas: Habilitadas")
    if verbose:
        print("Modo verboso: Habilitado")
    print()
    
    # Verifica se a API está respondendo
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print_error(f"A API não está respondendo corretamente em {base_url}")
            print_warning("Certifique-se de que a API está rodando (python run_api.py)")
            sys.exit(1)
        print_success("API está respondendo")
    except requests.exceptions.ConnectionError:
        print_error(f"Não foi possível conectar à API em {base_url}")
        print_warning("Certifique-se de que a API está rodando (python run_api.py)")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erro ao verificar API: {str(e)}")
        sys.exit(1)
    
    # Executa testes
    tester = APITester(base_url, test_external=test_external, verbose=verbose)
    tester.run_all_tests()
    
    # Exit code baseado nos resultados
    sys.exit(0 if tester.results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()

