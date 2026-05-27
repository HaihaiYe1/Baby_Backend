import os
import logging
from typing import List, Dict, Any, Optional
import chromadb

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """知识库管理类，使用ChromaDB向量数据库"""
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "parenting_knowledge"
    ):
        """
        初始化知识库
        
        Args:
            persist_directory: 持久化存储目录
            collection_name: 集合名称
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # 创建持久化目录
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化ChromaDB客户端（使用新API）
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "育儿知识库"}
        )
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档到知识库
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: 文档ID列表
            
        Returns:
            添加的文档ID列表
        """
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
        
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        # 添加到集合
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        查询知识库
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            where: 过滤条件
            
        Returns:
            查询结果
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "ids": results["ids"][0] if results["ids"] else []
        }
    
    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}", exc_info=True)
            return False
    
    def update_document(
        self,
        doc_id: str,
        document: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新文档
        
        Args:
            doc_id: 文档ID
            document: 新文档内容
            metadata: 新元数据
            
        Returns:
            是否更新成功
        """
        try:
            self.collection.update(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata] if metadata else None
            )
            return True
        except Exception as e:
            logger.error(f"更新文档失败: {e}", exc_info=True)
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Returns:
            统计信息
        """
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_directory": self.persist_directory
        }
    
    def add_from_files(
        self,
        file_paths: List[str],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        从文件添加文档
        
        Args:
            file_paths: 文件路径列表
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            
        Returns:
            添加的文档ID列表
        """
        from app.knowledge.loader import DocumentLoader
        
        loader = DocumentLoader()
        all_ids = []
        
        for file_path in file_paths:
            try:
                # 加载文档
                chunks = loader.load_and_split(
                    file_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # 添加元数据
                metadatas = [
                    {
                        "source": file_path,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                    for i in range(len(chunks))
                ]
                
                # 添加到知识库
                ids = self.add_documents(chunks, metadatas)
                all_ids.extend(ids)
                
                logger.info(f"已添加文件 {file_path}，共 {len(chunks)} 个分块")
                
            except Exception as e:
                logger.error(f"处理文件 {file_path} 失败: {e}", exc_info=True)
        
        return all_ids
    
    def search_by_category(
        self,
        category: str,
        query_text: str,
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        按类别搜索
        
        Args:
            category: 知识类别
            query_text: 查询文本
            n_results: 返回结果数量
            
        Returns:
            搜索结果
        """
        where = {"category": category}
        return self.query(query_text, n_results, where)
    
    def persist(self):
        """持久化数据库（新版本自动持久化）"""
        pass


# 全局知识库实例
knowledge_base = KnowledgeBase()
