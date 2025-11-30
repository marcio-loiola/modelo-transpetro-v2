#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# INITIALIZE DATABASE
# =============================================================================
"""
Script para inicializar o banco de dados SQLite.
Cria as tabelas necessárias para armazenar predições e relatórios.
"""

import sys
from pathlib import Path

# Adicionar o diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from api.database import init_db, DB_FILE

if __name__ == "__main__":
    print(f"Inicializando banco de dados em: {DB_FILE}")
    try:
        init_db()
        print("✅ Banco de dados inicializado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")
        sys.exit(1)

