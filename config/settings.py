from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    model_path: str = "models/modelo_final_v13.pkl"
    encoder_path: str = "models/encoder_final_v13.pkl"
    ocean_api_url: Optional[str] = None
    ocean_api_key: Optional[str] = None
    environmental_enabled: bool = True

    class Config:
        env_file = ".env"

settings = Settings()