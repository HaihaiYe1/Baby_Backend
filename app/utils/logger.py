import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_file: str = "app.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        log_file: 日志文件名
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的备份文件数量
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
    
    Returns:
        配置好的logger实例
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除现有的handlers
    logger.handlers.clear()
    
    # 日志格式
    log_format = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
    
    # 文件handler（带轮转）
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    
    # 错误日志单独文件
    if enable_file:
        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(log_format)
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
    
    Returns:
        logger实例
    """
    return logging.getLogger(name)


class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, logger_name: str = "request"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        client_ip: str = None,
        user_agent: str = None
    ):
        """记录请求日志"""
        self.logger.info(
            f"{method} {path} | {status_code} | {duration:.3f}s | "
            f"IP: {client_ip} | UA: {user_agent}"
        )
    
    def log_error(
        self,
        method: str,
        path: str,
        error: Exception,
        client_ip: str = None
    ):
        """记录错误日志"""
        self.logger.error(
            f"{method} {path} | Error: {str(error)} | IP: {client_ip}",
            exc_info=True
        )


class DetectionLogger:
    """检测日志记录器"""
    
    def __init__(self, logger_name: str = "detection"):
        self.logger = logging.getLogger(logger_name)
    
    def log_detection(
        self,
        device_id: int,
        detection_type: str,
        result: dict,
        duration: float
    ):
        """记录检测日志"""
        self.logger.info(
            f"Device {device_id} | Type: {detection_type} | "
            f"Result: {result.get('overall_level', 'unknown')} | "
            f"Duration: {duration:.3f}s"
        )
    
    def log_alert(
        self,
        device_id: int,
        level: str,
        message: str,
        notification_id: int = None
    ):
        """记录警报日志"""
        self.logger.warning(
            f"Device {device_id} | Level: {level} | "
            f"Message: {message} | Notification: {notification_id}"
        )


class AgentLogger:
    """Agent日志记录器"""
    
    def __init__(self, logger_name: str = "agent"):
        self.logger = logging.getLogger(logger_name)
    
    def log_agent_action(
        self,
        user_id: int,
        action: str,
        result: dict,
        duration: float
    ):
        """记录Agent动作日志"""
        self.logger.info(
            f"User {user_id} | Action: {action} | "
            f"Success: {result.get('success', False)} | "
            f"Duration: {duration:.3f}s"
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        input_params: dict,
        output: dict,
        success: bool
    ):
        """记录工具调用日志"""
        self.logger.debug(
            f"Tool: {tool_name} | Input: {input_params} | "
            f"Success: {success}"
        )


# 全局日志实例
request_logger = RequestLogger()
detection_logger = DetectionLogger()
agent_logger = AgentLogger()
