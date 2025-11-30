# Backup de Mudanças no Backend

Este arquivo contém as alterações feitas nos arquivos de configuração e serviço do backend para garantir a resiliência e a integração correta com o frontend.

## 1. `backend-api/api/config.py`

**Mudança:** Adicionado `extra = "ignore"` na classe `Config` para evitar erros de validação ao ler o arquivo `.env` que contém variáveis do frontend.

```python
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # <--- ADICIONADO
```

## 2. `backend-api/api/services.py`

**Mudança:** Adicionados logs detalhados no método `get_ship_summary` para diagnosticar problemas de carregamento de arquivos CSV.

```python
    def get_ship_summary(self) -> pd.DataFrame:
        """Load the ship summary report from CSV or database."""
        # Try CSV first
        path = settings.DATA_PROCESSED_DIR / "biofouling_summary_by_ship.csv"
        logger.info(f"Attempting to load summary from: {path.absolute()}")  # <--- LOG ADICIONADO
        if path.exists():
            try:
                df = pd.read_csv(path)
                logger.info(f"Loaded summary CSV. Shape: {df.shape}")  # <--- LOG ADICIONADO
                if not df.empty:
                    return df
            except Exception as e:
                logger.error(f"Error loading CSV summary from {path}: {e}")  # <--- LOG ADICIONADO
        else:
            logger.warning(f"Summary CSV not found at: {path.absolute()}")  # <--- LOG ADICIONADO
        
        # ... restante do código ...
```
