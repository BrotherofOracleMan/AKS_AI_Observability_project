from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    azure_openai_model: str = Field(..., env="AZURE_OPENAI_MODEL")
    azure_openai_api_version: str = Field(..., env="AZURE_OPENAI_API_VERSION")
    base_url: str = Field(..., env="BASE_URL")

    
config = Config()