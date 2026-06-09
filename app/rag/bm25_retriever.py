from typing import List, Tuple, Dict, Any, Optional
import jieba
import re


class BM25Retriever:
    """
    BM25稀疏检索器
    
    使用jieba分词进行中文分词，然后使用BM25算法进行检索
    """
    
    def __init__(self, documents: List[str] = None, k1: float = 1.5, b: float = 0.75):
        """
        初始化BM25检索器
        
        Args:
            documents: 文档列表
            k1: BM25参数k1
            b: BM25参数b
        """
        self.k1 = k1
        self.b = b
        self.documents = documents or []
        self.tokenized_docs: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.idf: Dict[str, float] = {}
        
        if documents:
            self._build_index(documents)
    
    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        # 清理文本
        text = re.sub(r'[^\w\s]', ' ', text)
        text = text.lower().strip()
        
        # 使用jieba分词
        tokens = list(jieba.cut(text))
        
        # 去除停用词和单字符
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        tokens = [t for t in tokens if t not in stop_words and len(t) > 1]
        
        return tokens
    
    def _build_index(self, documents: List[str]) -> None:
        """构建BM25索引"""
        self.documents = documents
        self.tokenized_docs = [self._tokenize(doc) for doc in documents]
        self.doc_lengths = [len(doc) for doc in self.tokenized_docs]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        
        # 计算IDF
        df: Dict[str, int] = {}
        for doc_tokens in self.tokenized_docs:
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                df[token] = df.get(token, 0) + 1
        
        n = len(documents)
        self.idf = {
            token: max(0, (n - freq + 0.5) / (freq + 0.5))
            for token, freq in df.items()
        }
    
    def add_documents(self, documents: List[str]) -> None:
        """添加文档并重建索引"""
        self._build_index(documents)
    
    def _calculate_score(self, query_tokens: List[str], doc_idx: int) -> float:
        """计算查询与文档的BM25分数"""
        doc_tokens = self.tokenized_docs[doc_idx]
        doc_length = self.doc_lengths[doc_idx]
        
        # 计算词频
        tf: Dict[str, int] = {}
        for token in doc_tokens:
            tf[token] = tf.get(token, 0) + 1
        
        score = 0.0
        for query_token in query_tokens:
            if query_token in tf:
                term_freq = tf[query_token]
                idf = self.idf.get(query_token, 0)
                
                # BM25公式
                numerator = term_freq * (self.k1 + 1)
                denominator = term_freq + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                
                score += idf * numerator / denominator
        
        return score
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            
        Returns:
            (文档索引, 分数) 列表
        """
        if not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # 计算所有文档的分数
        scores = []
        for idx in range(len(self.documents)):
            score = self._calculate_score(query_tokens, idx)
            scores.append((idx, score))
        
        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]
    
    def retrieve_with_scores(self, query: str, top_k: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        检索相关文档（带详细信息）
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            min_score: 最小分数阈值
            
        Returns:
            包含文档内容和分数的结果列表
        """
        results = self.retrieve(query, top_k)
        
        detailed_results = []
        for idx, score in results:
            if score >= min_score:
                detailed_results.append({
                    "index": idx,
                    "document": self.documents[idx],
                    "score": score
                })
        
        return detailed_results


# 全局BM25检索器实例（需要在应用启动时初始化）
bm25_retriever: Optional[BM25Retriever] = None


def get_bm25_retriever() -> BM25Retriever:
    """获取BM25检索器实例"""
    global bm25_retriever
    if bm25_retriever is None:
        bm25_retriever = BM25Retriever()
    return bm25_retriever


def initialize_bm25_retriever(documents: List[str]) -> BM25Retriever:
    """初始化BM25检索器"""
    global bm25_retriever
    bm25_retriever = BM25Retriever(documents)
    return bm25_retriever
