# 🍼 Baby Monitor Backend

基于 FastAPI 的婴儿智能看护系统后端服务，集成 AI Agent、多模态感知、RAG 知识库和智能家居控制。

## 🚀 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM |
| LangChain | 0.1+ | AI Agent 框架 |
| YOLOv8 | 8.1+ | 目标检测 |
| MediaPipe | 0.10+ | 姿态检测 |
| ChromaDB | 0.4+ | 向量数据库 |
| paho-mqtt | 1.6+ | MQTT 客户端 |

## 📁 项目结构

```
backend/
├── app/
│   ├── agent/                  # AI Agent 模块
│   │   ├── baby_agent.py       # 核心 Agent 类
│   │   ├── tools/              # Agent 工具集
│   │   ├── prompts/            # Prompt 模板
│   │   └── memory/             # 记忆管理
│   │
│   ├── api/                    # API 端点
│   │   ├── auth.py             # 认证模块
│   │   ├── device.py           # 设备管理
│   │   ├── video.py            # 视频检测
│   │   ├── agent.py            # Agent 接口
│   │   ├── rag.py              # RAG 知识库
│   │   ├── smart_home.py       # 智能家居
│   │   ├── websocket.py        # WebSocket
│   │   └── monitoring.py       # 性能监控
│   │
│   ├── detection/              # 检测模块
│   │   ├── multi_detector.py   # 多模态检测器
│   │   ├── danger_detection.py # 危险物品检测
│   │   ├── suffocation_detection.py # 窒息检测
│   │   └── action_detection.py # 姿态检测
│   │
│   ├── rag/                    # RAG 知识库
│   │   ├── knowledge_base.py   # 知识库管理
│   │   ├── retriever.py        # 检索器
│   │   └── advisor.py          # 育儿顾问
│   │
│   ├── services/               # 服务层
│   │   ├── vlm_service.py      # VLM 视觉语言模型
│   │   ├── scene_analyzer.py   # 场景分析器
│   │   ├── websocket_manager.py # WebSocket 管理
│   │   └── audio_service.py    # 音频服务
│   │
│   ├── tools/                  # 工具集
│   │   └── smart_home/         # 智能家居工具
│   │       ├── mqtt_client.py  # MQTT 客户端
│   │       ├── speaker_tool.py # 音箱控制
│   │       ├── light_tool.py   # 灯光控制
│   │       └── scene_tool.py   # 场景控制
│   │
│   ├── utils/                  # 工具类
│   │   ├── database.py         # 数据库连接
│   │   ├── security.py         # 安全认证
│   │   ├── logger.py           # 日志系统
│   │   └── video_utils.py      # 视频工具
│   │
│   ├── config.py               # 配置管理
│   ├── main.py                 # 应用入口
│   ├── models.py               # 数据库模型
│   ├── schemas.py              # Pydantic 模型
│   └── crud.py                 # 数据库操作
│
├── alembic/                    # 数据库迁移
├── tests/                      # 单元测试
├── knowledge/                  # 知识库文档
├── requirements.txt            # Python 依赖
├── Dockerfile                  # Docker 配置
├── .env.example                # 环境变量模板
└── README.md                   # 项目说明
```

## 🛠️ 安装与运行

### 1. 环境要求

- Python 3.11+
- MySQL 8.0+
- Docker (可选)

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写配置
# 必须配置：
# - DATABASE_URL: 数据库连接
# - SECRET_KEY: JWT 密钥
# - MIMO_API_KEY: 小米 MiMo API 密钥
```

### 4. 初始化数据库

```bash
# 方式1：使用 Docker
docker-compose -f docker-mysql.yml up -d

# 方式2：使用现有 MySQL
mysql -u root -p < baby.sql
```

### 5. 运行服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Docker 部署

```bash
# 构建镜像
docker build -t baby-monitor-backend .

# 运行容器
docker run -d -p 8000:8000 --env-file .env baby-monitor-backend
```

## 📚 API 文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要 API 模块

| 模块 | 前缀 | 说明 |
|------|------|------|
| Auth | `/auth` | 用户认证 |
| Device | `/device` | 设备管理 |
| Video | `/video` | 视频检测 |
| Agent | `/agent` | AI Agent |
| RAG | `/rag` | 育儿知识库 |
| SmartHome | `/smart-home` | 智能家居 |
| WebSocket | `/ws/stream` | 实时流 |
| Monitoring | `/monitoring` | 性能监控 |

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_auth.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

## 🔧 核心功能

### AI Agent

基于 LangChain 的智能决策系统，支持：
- 多轮对话
- 工具调用
- 记忆管理
- 上下文理解

### 多模态感知

双层检测架构：
1. **第一层**: YOLOv8 + MediaPipe 快速检测
2. **第二层**: VLM 视觉语言模型深度推理

### RAG 知识库

基于 ChromaDB 的育儿知识库：
- 知识检索增强生成
- 语义搜索
- 上下文关联

### 智能家居控制

通过 MQTT 协议控制：
- 智能音箱（白噪音、摇篮曲）
- 智能灯光（亮度、颜色、模式）
- 场景模式（睡眠、安抚、警报）

## 📊 监控

访问 `/monitoring/stats` 获取系统状态：
- WebSocket 连接数
- 消息收发统计
- 音频设备状态
- 系统延迟

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

---

<p align="center">
  Made with ❤️ for baby safety
</p>
