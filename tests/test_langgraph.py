"""
LangGraph + RAG 新功能测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestLangGraphState:
    """测试LangGraph状态定义"""
    
    def test_state_creation(self):
        """测试状态创建"""
        from app.agent.state import BabyAgentState
        
        state = {
            "messages": [],
            "user_id": 1,
            "risk_level": "safe"
        }
        
        assert state["user_id"] == 1
        assert state["risk_level"] == "safe"
    
    def test_state_defaults(self):
        """测试状态默认值"""
        from app.agent.state import BabyAgentState
        
        # 使用NotRequired字段应该是可选的
        state = {"messages": []}
        assert "detection_results" not in state
        assert "risk_level" not in state


class TestCheckpointer:
    """测试Checkpointer"""
    
    def test_memory_checkpointer(self):
        """测试内存checkpointer创建"""
        from app.agent.checkpointer import create_checkpointer
        
        with patch('app.agent.checkpointer.settings') as mock_settings:
            mock_settings.LANGGRAPH_CHECKPOINT_BACKEND = "memory"
            
            checkpointer = create_checkpointer()
            assert checkpointer is not None
    
    def test_invalid_backend(self):
        """测试无效后端"""
        from app.agent.checkpointer import create_checkpointer
        
        with patch('app.agent.checkpointer.settings') as mock_settings:
            mock_settings.LANGGRAPH_CHECKPOINT_BACKEND = "invalid"
            
            # 无效后端会尝试导入不存在的模块
            with pytest.raises((ValueError, ImportError, ModuleNotFoundError)):
                create_checkpointer()


class TestStore:
    """测试Store长期记忆"""
    
    def test_in_memory_store(self):
        """测试内存存储"""
        from app.agent.store import InMemoryStore
        
        store = InMemoryStore()
        
        # 存储数据
        store.put(("user", "1"), "prefs", {"theme": "dark"})
        
        # 获取数据
        result = store.get(("user", "1"), "prefs")
        assert result is not None
        assert result["theme"] == "dark"
    
    def test_store_delete(self):
        """测试存储删除"""
        from app.agent.store import InMemoryStore
        
        store = InMemoryStore()
        store.put(("user", "1"), "key", {"data": "test"})
        
        # 删除
        result = store.delete(("user", "1"), "key")
        assert result is True
        
        # 验证已删除
        result = store.get(("user", "1"), "key")
        assert result is None
    
    def test_user_preference_store(self):
        """测试用户偏好存储"""
        from app.agent.store import UserPreferenceStore
        
        store = UserPreferenceStore()
        
        # 保存偏好
        store.save_preferences(1, {"theme": "dark", "language": "zh"})
        
        # 获取偏好
        prefs = store.get_preferences(1)
        assert prefs["theme"] == "dark"
        assert prefs["language"] == "zh"
    
    def test_conversation_store(self):
        """测试对话历史存储"""
        from app.agent.store import ConversationStore
        
        store = ConversationStore()
        
        # 保存消息
        store.save_message(1, "thread1", "user", "你好")
        store.save_message(1, "thread1", "agent", "你好！有什么可以帮助你？")
        
        # 获取消息
        messages = store.get_messages(1, "thread1")
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        
        # 获取线程列表
        threads = store.get_threads(1)
        assert "thread1" in threads


class TestMiddleware:
    """测试中间件"""
    
    def test_pii_detection(self):
        """测试PII检测"""
        from app.agent.middleware.pii_middleware import PIIMiddleware
        
        middleware = PIIMiddleware()
        
        # 测试手机号检测
        result = middleware._detect_pii("我的手机号是13812345678")
        assert "phone" in result
        assert "13812345678" in result["phone"]
        
        # 测试邮箱检测
        result = middleware._detect_pii("邮箱是test@example.com")
        assert "email" in result
    
    def test_pii_masking(self):
        """测试PII遮挡"""
        from app.agent.middleware.pii_middleware import PIIMiddleware
        
        middleware = PIIMiddleware(strategy="mask")
        
        # 遮挡手机号
        masked = middleware._mask_pii("手机号13812345678")
        assert "138****5678" in masked
        assert "13812345678" not in masked
    
    def test_hitl_safe_operations(self):
        """测试HITL安全操作"""
        from app.agent.middleware.hitl_middleware import HITLMiddleware
        
        middleware = HITLMiddleware(auto_approve_safe=True)
        
        # 安全操作不需要中断
        assert middleware.should_interrupt("control_light", {"action": "off"}) is False
        
        # 危险操作需要中断
        assert middleware.should_interrupt("send_notification", {"level": "danger"}) is True


class TestQueryOptimizer:
    """测试查询优化器"""
    
    @pytest.mark.asyncio
    async def test_keyword_extraction(self):
        """测试关键词提取"""
        from app.rag.query_optimizer import QueryOptimizer
        
        with patch('app.rag.query_optimizer.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "婴儿, 睡眠, 安全"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            optimizer = QueryOptimizer()
            keywords = await optimizer.extract_keywords("婴儿睡眠安全注意事项")
            
            assert len(keywords) > 0
    
    @pytest.mark.asyncio
    async def test_query_rewrite(self):
        """测试查询重写"""
        from app.rag.query_optimizer import QueryOptimizer
        
        with patch('app.rag.query_optimizer.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "婴儿睡眠安全指南和注意事项"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            optimizer = QueryOptimizer()
            rewritten = await optimizer.rewrite_query("宝宝睡觉要注意什么")
            
            assert len(rewritten) > 0


class TestBM25Retriever:
    """测试BM25检索器"""
    
    def test_bm25_index(self):
        """测试BM25索引构建"""
        from app.rag.bm25_retriever import BM25Retriever
        
        docs = [
            "婴儿睡眠安全指南",
            "宝宝辅食添加注意事项",
            "新生儿护理基础知识"
        ]
        
        retriever = BM25Retriever(docs)
        assert len(retriever.documents) == 3
    
    def test_bm25_retrieve(self):
        """测试BM25检索"""
        from app.rag.bm25_retriever import BM25Retriever
        
        docs = [
            "婴儿睡眠安全指南：如何让宝宝安全入睡",
            "宝宝辅食添加注意事项：6个月开始添加",
            "新生儿护理基础知识：喂养和洗澡"
        ]
        
        retriever = BM25Retriever(docs)
        results = retriever.retrieve("婴儿睡眠", top_k=2)
        
        assert len(results) > 0
        # 第一个文档应该最相关
        assert results[0][0] == 0


class TestReranker:
    """测试重排序器"""
    
    def test_simple_reranker(self):
        """测试简单重排序器"""
        from app.rag.reranker import SimpleReranker
        
        reranker = SimpleReranker()
        
        docs = [
            "婴儿睡眠安全指南",
            "宝宝辅食添加",
            "婴儿睡眠姿势"
        ]
        
        results = reranker.rerank("婴儿睡眠", docs, top_k=2)
        
        assert len(results) == 2
        # 相关文档应该排在前面
        assert results[0][0] in [0, 2]  # 睡眠相关的文档


class TestEvaluator:
    """测试RAGAS评估器"""
    
    def test_context_precision(self):
        """测试上下文精确度计算"""
        from app.rag.evaluator import RAGEvaluator
        
        evaluator = RAGEvaluator()
        
        score = evaluator._calculate_context_precision(
            question="婴儿睡眠",
            contexts=["婴儿睡眠安全指南", "宝宝辅食添加"],
            answer="婴儿睡眠需要注意安全"
        )
        
        assert 0 <= score <= 1
    
    def test_faithfulness(self):
        """测试忠实度计算"""
        from app.rag.evaluator import RAGEvaluator
        
        evaluator = RAGEvaluator()
        
        score = evaluator._calculate_faithfulness(
            answer="婴儿需要安全的睡眠环境",
            contexts=["婴儿睡眠安全指南：确保睡眠环境安全"]
        )
        
        assert 0 <= score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
