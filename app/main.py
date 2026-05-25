from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 导入 CORS
from .api import auth, device, notification, websocket, video, timing, agent, rag, smart_home, websocket_stream, monitoring
from .utils.database import Base, engine
from .services.websocket_manager import ws_manager

# tags是用于自动文档（Swagger UI）的分组显示

# 生成数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    await ws_manager.start()
    print("应用启动完成")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    await ws_manager.stop()
    print("应用关闭完成")

# ========== 先添加 CORS 中间件（必须在路由之前！）==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议改为具体域名
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
