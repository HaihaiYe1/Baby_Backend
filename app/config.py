import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "Baby Monitor API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://fastapi:171008@localhost/baby"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "fastapi"
    DATABASE_PASSWORD: str = "171008"
    DATABASE_NAME: str = "baby"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天
    
    # 小米MiMo API配置
    MIMO_API_KEY: str = "sk-cky9npvg2kk9c2m8iv7n0ycgnxggfqq73nmvt7sdx9efouwj"
    MIMO_BASE_URL: str = "https://api.mimo.xiaomi.com/v1"
    MIMO_MODEL: str = "MiMo-V2.5-Pro"
    
    # MQTT配置
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    
    # WebSocket配置
    WS_HEARTBEAT_TIMEOUT: int = 30
    
    # CORS配置
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()


# 全局配置实例
settings = get_settings()
