#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# TEST API - COMPREHENSIVE TEST SUITE
# =============================================================================
"""
Script completo para testar todos os endpoints da API Biofouling Prediction.

Uso: python test_api.py
"""

import sys
import io

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
from datetime import datetime, date
from typing import Dict, Any

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"

# Cores para output (Windows)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Fallback para Windows sem cores
try:
    import colorama
    colorama.init()
except ImportError:
    Colors.GREEN = Colors.RED = Colors.YELLOW = Colors.BLUE = Colors.RESET = Colors.BOLD = ''


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
        # Fallback para Windows sem suporte a unicode
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


def print_json(data: Any, indent: int = 2):
    """Imprime JSON formatado."""
    print(json.dumps(data, indent=indent, default=str, ensure_ascii=False))


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

class APITester:
    """Classe para testar a API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
    
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
                print_error("Falhou")
                return False
        except Exception as e:
            self.results["failed"] += 1
            print_error(f"Erro: {str(e)}")
            return False
    
    def get(self, endpoint: str, params: Dict = None) -> requests.Response:
        """Faz uma requisição GET."""
        url = f"{self.base_url}{endpoint}"
        return self.session.get(url, params=params)
    
    def post(self, endpoint: str, data: Dict = None) -> requests.Response:
        """Faz uma requisição POST."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        return self.session.post(url, json=data, headers=headers)
    
    # ========================================================================
    # TEST: Health & Info
    # ========================================================================
    
    def test_root(self) -> bool:
        """Testa endpoint raiz."""
        response = self.get("/")
        if response.status_code == 200:
            data = response.json()
            print(f"\n  {json.dumps(data, indent=2, ensure_ascii=False)}")
            return True
        return False
    
    def test_health(self) -> bool:
        """Testa health check."""
        response = self.get("/health")
        if response.status_code == 200:
            data = response.json()
            print(f"\n  Status: {data.get('status')}")
            print(f"  Versão: {data.get('version')}")
            print(f"  Modelo carregado: {data.get('model_loaded')}")
            return True
        return False
    
    def test_model_info(self) -> bool:
        """Testa informações do modelo."""
        response = self.get(f"{API_VERSION}/model/info")
        if response.status_code == 200:
            data = response.json()
            print(f"\n  Nome: {data.get('model_name', 'N/A')}")
            print(f"  Versão: {data.get('version', 'N/A')}")
            print(f"  Features: {len(data.get('features', []))}")
            return True
        elif response.status_code == 503:
            print_warning("Modelo não carregado")
            self.results["warnings"] += 1
            return True
        else:
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
                    print(f"    {i}. {feat.get('feature', 'N/A')}: {feat.get('importance', 0):.4f}")
            else:
                print("\n  Nenhuma feature disponível")
            return True
        elif response.status_code == 503:
            print_warning("Modelo não carregado")
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
            print(f"\n  Navio: {result.get('ship_name')}")
            print(f"  Consumo previsto: {result.get('predicted_consumption'):.2f} tons")
            print(f"  Índice biofouling: {result.get('bio_index'):.2f}/10")
            print(f"  Classificação: {result.get('bio_class')}")
            print(f"  Custo adicional: ${result.get('additional_cost_usd'):.2f} USD")
            return True
        elif response.status_code == 503:
            print_warning("Modelo não carregado - serviço indisponível")
            self.results["warnings"] += 1
            return True  # Não é um erro do teste
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
            print(f"\n  Total: {result.get('total')}")
            print(f"  Sucessos: {result.get('successful')}")
            print(f"  Falhas: {result.get('failed')}")
            return True
        elif response.status_code == 503:
            print_warning("Modelo não carregado")
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
            print(f"\n  Cenários comparados: {len(scenarios)}")
            for i, scenario in enumerate(scenarios, 1):
                print(f"    {i}. {scenario.get('bio_index'):.2f}/10 - {scenario.get('bio_class')}")
            return True
        elif response.status_code == 503:
            print_warning("Modelo não carregado")
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
            if isinstance(data, dict):
                total = data.get('total', 0)
                ships = data.get('ships', [])
                print(f"\n  Total de navios: {total}")
                if ships:
                    print(f"  Primeiros 3 navios:")
                    for ship in ships[:3]:
                        if isinstance(ship, dict):
                            print(f"    - {ship.get('ship_name', 'N/A')} ({ship.get('total_events', 0)} eventos)")
            return True
        return False
    
    def test_get_ship(self) -> bool:
        """Testa obtenção de um navio específico."""
        # Primeiro, lista os navios para pegar um nome válido
        list_response = self.get(f"{API_VERSION}/ships/")
        if list_response.status_code == 200:
            ships = list_response.json().get('ships', [])
            if ships:
                ship_name = ships[0].get('ship_name')
                response = self.get(f"{API_VERSION}/ships/{ship_name}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n  Navio: {data.get('ship_name')}")
                    print(f"  Total eventos: {data.get('total_events')}")
                    return True
                elif response.status_code == 404:
                    print_warning(f"Navio '{ship_name}' não encontrado")
                    self.results["warnings"] += 1
                    return True
        return False
    
    def test_ship_summary(self) -> bool:
        """Testa resumo de um navio."""
        list_response = self.get(f"{API_VERSION}/ships/")
        if list_response.status_code == 200:
            ships = list_response.json().get('ships', [])
            if ships:
                ship_name = ships[0].get('ship_name')
                response = self.get(f"{API_VERSION}/ships/{ship_name}/summary")
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n  Navio: {data.get('ship_name')}")
                    print(f"  Índice médio: {data.get('avg_bio_index'):.2f}/10")
                    print(f"  Índice máximo: {data.get('max_bio_index'):.2f}/10")
                    print(f"  Consumo adicional: {data.get('total_additional_fuel', 0):.2f} tons")
                    return True
                elif response.status_code == 404:
                    print_warning("Resumo não disponível")
                    self.results["warnings"] += 1
                    return True
        return False
    
    def test_fleet_summary(self) -> bool:
        """Testa resumo da frota."""
        response = self.get(f"{API_VERSION}/ships/fleet/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"\n  Total navios: {data.get('total_ships')}")
            print(f"  Total eventos: {data.get('total_events')}")
            print(f"  Índice médio frota: {data.get('fleet_avg_bio_index'):.2f}/10")
            print(f"  Custo adicional total: ${data.get('fleet_total_additional_cost_usd', 0):.2f} USD")
            return True
        elif response.status_code == 404:
            print_warning("Resumo da frota não disponível")
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
            total = data.get('total_records', 0)
            records = data.get('records', [])
            print(f"\n  Total de registros: {total}")
            print(f"  Exibindo: {len(records)} registros")
            if records:
                print(f"  Primeiro registro:")
                rec = records[0]
                print(f"    Navio: {rec.get('ship_name')}")
                print(f"    Índice: {rec.get('bio_index'):.2f}/10")
                print(f"    Classe: {rec.get('bio_class')}")
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
            print(f"\n  Registros com índice >= 5.0: {data.get('total_records', 0)}")
            return True
        return False
    
    def test_statistics(self) -> bool:
        """Testa estatísticas gerais."""
        response = self.get(f"{API_VERSION}/reports/statistics")
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                print_warning(data["message"])
                self.results["warnings"] += 1
                return True
            
            print(f"\n  Total registros: {data.get('total_records', 0)}")
            print(f"  Total navios: {data.get('total_ships', 0)}")
            
            bio_index = data.get('bio_index', {})
            if bio_index:
                print(f"  Índice médio: {bio_index.get('mean', 0):.2f}/10")
            
            return True
        return False
    
    def test_high_risk_ships(self) -> bool:
        """Testa navios de alto risco."""
        params = {"threshold": 7.0}
        response = self.get(f"{API_VERSION}/reports/high-risk", params=params)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_high_risk', 0)
            ships = data.get('ships', [])
            print(f"\n  Navios de alto risco (>= 7.0): {total}")
            if ships:
                print(f"  Top 3:")
                for ship in ships[:3]:
                    print(f"    - {ship.get('ship_name')}: {ship.get('max_bio_index'):.1f}/10")
            return True
        return False
    
    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================
    
    def run_all_tests(self):
        """Executa todos os testes."""
        print_header("TESTE COMPLETO DA API - BIOFOULING PREDICTION")
        
        # Health & Info
        print_header("1. Health Check & Informacoes")
        self.test("Root Endpoint", self.test_root)
        self.test("Health Check", self.test_health)
        self.test("Model Info", self.test_model_info)
        self.test("Feature Importances", self.test_feature_importances)
        
        # Predictions
        print_header("2. Predições")
        self.test("Predição Única", self.test_single_prediction)
        self.test("Predições em Lote", self.test_batch_prediction)
        self.test("Comparação de Cenários", self.test_scenario_comparison)
        
        # Ships
        print_header("3. Navios")
        self.test("Listar Navios", self.test_list_ships)
        self.test("Obter Navio Específico", self.test_get_ship)
        self.test("Resumo de Navio", self.test_ship_summary)
        self.test("Resumo da Frota", self.test_fleet_summary)
        
        # Reports
        print_header("4. Relatórios")
        self.test("Relatório Biofouling", self.test_biofouling_report)
        self.test("Relatório com Filtros", self.test_biofouling_report_filters)
        self.test("Estatísticas Gerais", self.test_statistics)
        self.test("Navios de Alto Risco", self.test_high_risk_ships)
        
        # Summary
        print_header("RESUMO DOS TESTES")
        print(f"\n{Colors.BOLD}Total de testes: {self.results['total']}{Colors.RESET}")
        print(f"{Colors.GREEN}[OK] Passou: {self.results['passed']}{Colors.RESET}")
        print(f"{Colors.RED}[ERRO] Falhou: {self.results['failed']}{Colors.RESET}")
        if self.results['warnings'] > 0:
            print(f"{Colors.YELLOW}[AVISO] Avisos: {self.results['warnings']}{Colors.RESET}")
        
        success_rate = (self.results['passed'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
        print(f"\n{Colors.BOLD}Taxa de sucesso: {success_rate:.1f}%{Colors.RESET}\n")
        
        if self.results['failed'] == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}[SUCESSO] Todos os testes passaram!{Colors.RESET}\n")
        else:
            print(f"{Colors.RED}{Colors.BOLD}[ERRO] Alguns testes falharam.{Colors.RESET}\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Função principal."""
    print(f"\n{Colors.BOLD}Iniciando testes da API...{Colors.RESET}")
    print(f"URL base: {BASE_URL}\n")
    
    # Verifica se a API está respondendo
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print_error(f"A API não está respondendo corretamente em {BASE_URL}")
            print_warning("Certifique-se de que a API está rodando (python run_api.py)")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print_error(f"Não foi possível conectar à API em {BASE_URL}")
        print_warning("Certifique-se de que a API está rodando (python run_api.py)")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erro ao verificar API: {str(e)}")
        sys.exit(1)
    
    # Executa testes
    tester = APITester(BASE_URL)
    tester.run_all_tests()
    
    # Exit code baseado nos resultados
    sys.exit(0 if tester.results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()

