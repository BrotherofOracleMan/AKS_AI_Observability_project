from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT", default="https://openai.azure.com/")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY", default="")
    azure_openai_model: str = Field(..., env="AZURE_OPENAI_MODEL", default="gpt-4o-mini")
    azure_openai_api_version: str = Field(..., env="AZURE_OPENAI_API_VERSION", default="2024-12-01-preview")
    base_url: str = Field(..., env="BASE_URL", default="http://localhost:8000")

    
config = Config()