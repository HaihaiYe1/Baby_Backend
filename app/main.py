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
    log_level="INFO",
    log_dir="logs",
    log_file="app.log",
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


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        request_logger.log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        request_logger.log_error(
            method=request.method,
            path=request.url.path,
            error=e,
            client_ip=client_ip
        )
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
