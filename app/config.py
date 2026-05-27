import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "Baby Monitor API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置 - 必须通过环境变量配置
    DATABASE_URL: str = ""
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = ""
    DATABASE_PASSWORD: str = ""
    DATABASE_NAME: str = "baby"
    
    # JWT配置 - 必须通过环境变量配置
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天
    
    # 小米MiMo API配置 - 必须通过环境变量配置
    MIMO_API_KEY: str = ""
    MIMO_BASE_URL: str = "https://api.mimo.xiaomi.com/v1"
    MIMO_MODEL: str = "MiMo-V2.5-Pro"
    
    # MQTT配置
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    
    # WebSocket配置
    WS_HEARTBEAT_TIMEOUT: int = 30
    
    # CORS配置 - 默认只允许本地开发
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"]
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()


# 全局配置实例
settings = get_settings()

# 启动时验证必需的配置
def validate_settings():
    """验证必需的配置是否已设置"""
    errors = []
    
    if not settings.SECRET_KEY:
        errors.append("SECRET_KEY 未设置，请在 .env 文件中配置")
    
    if not settings.DATABASE_URL and not settings.DATABASE_USER:
        errors.append("DATABASE_URL 或 DATABASE_USER 未设置，请在 .env 文件中配置")
    
    if not settings.MIMO_API_KEY:
        errors.append("MIMO_API_KEY 未设置，请在 .env 文件中配置")
    
    if errors:
        raise ValueError("配置错误:\n" + "\n".join(f"  - {e}" for e in errors))
