from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_model: str
    azure_openai_api_version: str
    
config = Config()