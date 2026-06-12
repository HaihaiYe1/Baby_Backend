import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from .api import auth, device, notification, websocket, video, timing, agent, rag, smart_home, websocket_stream, monitoring
from .utils.database import Base, engine
from .services.websocket_manager import ws_manager
from .config import settings, validate_settings
from .utils.logger import setup_logging, request_logger

# 配置日志系统
setup_logging(
    log_level=settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO",
    log_dir=settings.LOG_DIR if hasattr(settings, 'LOG_DIR') else "logs",
    log_file=settings.LOG_FILE if hasattr(settings, 'LOG_FILE') else "app.log",
    enable_console=True,
    enable_file=True
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")
    
    # 验证配置
    try:
        validate_settings()
        logger.info("配置验证通过")
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        raise
    
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已创建")
    
    # 启动WebSocket管理器
    await ws_manager.start()
    logger.info("WebSocket管理器已启动")
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("应用关闭中...")
    await ws_manager.stop()
    logger.info("应用关闭完成")


# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="婴儿智能看护系统 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# 不需要记录日志的路径（健康检查、静态资源等）
SKIP_LOG_PATHS = {"/docs", "/redoc", "/openapi.json", "/favicon.ico"}


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    # 跳过不需要记录的路径
    if request.url.path in SKIP_LOG_PATHS:
        return await call_next(request)
    
    start_time = time.time()
    
    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # 获取请求体大小
    content_length = request.headers.get("content-length", 0)
    
    # 获取查询参数
    query_params = str(request.query_params) if request.query_params else ""
    
    # 尝试获取用户信息（从token）
    user_info = ""
    auth_header = request.headers.get("authorization", "")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from app.utils.security import get_current_user
            from app.utils.database import SessionLocal
            from jose import jwt
            from app.config import settings
            
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
            if email:
                user_info = f" | User: {email}"
        except Exception:
            pass  # token无效或过期，忽略
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # 构建日志消息
        log_msg = (
            f"{request.method} {request.url.path}"
            f"{'?'+query_params if query_params else ''} "
            f"| {response.status_code} "
            f"| {duration:.3f}s "
            f"| IP: {client_ip}"
            f"{user_info}"
            f"| Size: {content_length}B"
        )
        
        # 根据状态码选择日志级别
        if response.status_code >= 500:
            logger.error(log_msg)
        elif response.status_code >= 400:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(
            f"{request.method} {request.url.path} "
            f"| ERROR: {str(e)} "
            f"| IP: {client_ip}"
            f"{user_info} "
            f"| Duration: {duration:.3f}s",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(device.router, prefix="/device", tags=["Device"])
app.include_router(notification.router, prefix="/notification", tags=["Notification"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(video.router, prefix="/video", tags=["Video"])
app.include_router(timing.router, prefix="/timing", tags=["Timing"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(smart_home.router, prefix="/smart-home", tags=["SmartHome"])
app.include_router(websocket_stream.router, prefix="/ws/stream", tags=["WebSocketStream"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
