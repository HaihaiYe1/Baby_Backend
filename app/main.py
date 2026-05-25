from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware  # 导入 CORS
from fastapi.responses import JSONResponse
import time
import logging

from .api import auth, device, notification, websocket, video, timing, agent, rag, smart_home, websocket_stream, monitoring
from .utils.database import Base, engine
from .services.websocket_manager import ws_manager
from .config import settings
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

# tags是用于自动文档（Swagger UI）的分组显示

# 生成数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="婴儿智能看护系统 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # 记录请求日志
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
        
        # 记录错误日志
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

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    await ws_manager.start()
    logger.info("应用启动完成")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    await ws_manager.stop()
    logger.info("应用关闭完成")

# ========== 先添加 CORS 中间件（必须在路由之前！）==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法，包括 OPTIONS
    allow_headers=["*"],  # 允许所有请求头
)
# =========================================================

# 然后再注册路由
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(device.router, prefix="/device", tags=["Device"])
app.include_router(notification.router, prefix="/notification", tags=["Notification"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(video.router, prefix="/video", tags=["Video"])
# timing仅供测试
app.include_router(timing.router, prefix="/timing", tags=["Timing"])
# Agent相关接口
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
# RAG育儿知识库接口
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
# 智能家居控制接口
app.include_router(smart_home.router, prefix="/smart-home", tags=["SmartHome"])
# WebSocket流接口（视频流、音频流、语音对讲）
app.include_router(websocket_stream.router, prefix="/ws/stream", tags=["WebSocketStream"])
# 性能监控接口
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
