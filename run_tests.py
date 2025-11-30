#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# SCRIPT PARA EXECUTAR TESTES DA API
# =============================================================================
"""
Script simples para executar os testes da API.

Uso:
    python run_tests.py              # Testes básicos
    python run_tests.py --external   # Inclui testes de APIs externas
    python run_tests.py --verbose    # Modo verboso
    python run_tests.py --all        # Todos os testes
"""

import sys
import subprocess
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    # Verificar se o arquivo de teste existe
    test_file = Path(__file__).parent / "test_api_complete.py"
    
    if not test_file.exists():
        print("Erro: Arquivo test_api_complete.py não encontrado!")
        sys.exit(1)
    
    # Executar o teste
    args = sys.argv[1:]  # Passar argumentos adiante
    cmd = [sys.executable, str(test_file)] + args
    
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao executar testes: {e}")
        sys.exit(1)

