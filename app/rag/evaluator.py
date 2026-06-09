from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EvaluationCase:
    """评估用例"""
    question: str
    ground_truth: str
    contexts: List[str]
    answer: str


class RAGEvaluator:
    """
    RAG系统评估器
    
    使用多种指标评估RAG系统质量：
    - Context Precision: 上下文精确度
    - Context Recall: 上下文召回率
    - Faithfulness: 忠实度
    - Answer Relevancy: 答案相关性
    """
    
    def __init__(self):
        self.metrics = {}
    
    async def evaluate(
        self,
        test_cases: List[Dict[str, Any]],
        llm: Any = None,
        embeddings: Any = None
    ) -> Dict[str, Any]:
        """
        评估RAG系统
        
        Args:
            test_cases: 测试用例列表
            llm: 语言模型（可选）
            embeddings: 嵌入模型（可选）
            
        Returns:
            评估结果
        """
        results = {
            "total_cases": len(test_cases),
            "metrics": {},
            "details": []
        }
        
        # 计算各项指标
        context_precision_scores = []
        context_recall_scores = []
        faithfulness_scores = []
        answer_relevancy_scores = []
        
        for case in test_cases:
            case_result = self._evaluate_single_case(case)
            results["details"].append(case_result)
            
            context_precision_scores.append(case_result.get("context_precision", 0))
            context_recall_scores.append(case_result.get("context_recall", 0))
            faithfulness_scores.append(case_result.get("faithfulness", 0))
            answer_relevancy_scores.append(case_result.get("answer_relevancy", 0))
        
        # 计算平均分数
        n = len(test_cases)
        if n > 0:
            results["metrics"] = {
                "context_precision": sum(context_precision_scores) / n,
                "context_recall": sum(context_recall_scores) / n,
                "faithfulness": sum(faithfulness_scores) / n,
                "answer_relevancy": sum(answer_relevancy_scores) / n
            }
        
        return results
    
    def _evaluate_single_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个测试用例"""
        question = case.get("question", "")
        ground_truth = case.get("ground_truth", "")
        contexts = case.get("contexts", [])
        answer = case.get("answer", "")
        
        # 计算各项指标
        context_precision = self._calculate_context_precision(question, contexts, answer)
        context_recall = self._calculate_context_recall(ground_truth, contexts)
        faithfulness = self._calculate_faithfulness(answer, contexts)
        answer_relevancy = self._calculate_answer_relevancy(question, answer)
        
        return {
            "question": question,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy
        }
    
    def _calculate_context_precision(
        self,
        question: str,
        contexts: List[str],
        answer: str
    ) -> float:
        """
        计算上下文精确度
        
        衡量检索到的上下文中有多少是相关的
        """
        if not contexts:
            return 0.0
        
        # 简单实现：检查答案中的关键信息是否出现在上下文中
        answer_tokens = set(answer.lower().split())
        relevant_count = 0
        
        for context in contexts:
            context_tokens = set(context.lower().split())
            # 如果上下文包含答案中的关键信息，认为是相关的
            overlap = len(answer_tokens & context_tokens)
            if overlap > 0:
                relevant_count += 1
        
        return relevant_count / len(contexts)
    
    def _calculate_context_recall(
        self,
        ground_truth: str,
        contexts: List[str]
    ) -> float:
        """
        计算上下文召回率
        
        衡量答案所需的信息有多少被检索到
        """
        if not contexts or not ground_truth:
            return 0.0
        
        # 简单实现：检查ground_truth中的关键信息是否出现在上下文中
        truth_tokens = set(ground_truth.lower().split())
        all_context = " ".join(contexts).lower()
        
        found_count = 0
        for token in truth_tokens:
            if token in all_context:
                found_count += 1
        
        return found_count / len(truth_tokens) if truth_tokens else 0.0
    
    def _calculate_faithfulness(
        self,
        answer: str,
        contexts: List[str]
    ) -> float:
        """
        计算忠实度
        
        衡量答案是否基于检索到的上下文
        """
        if not contexts or not answer:
            return 0.0
        
        # 简单实现：检查答案中的信息是否在上下文中
        answer_tokens = set(answer.lower().split())
        all_context = " ".join(contexts).lower()
        
        supported_count = 0
        for token in answer_tokens:
            if token in all_context:
                supported_count += 1
        
        return supported_count / len(answer_tokens) if answer_tokens else 0.0
    
    def _calculate_answer_relevancy(
        self,
        question: str,
        answer: str
    ) -> float:
        """
        计算答案相关性
        
        衡量答案是否与问题相关
        """
        if not question or not answer:
            return 0.0
        
        # 简单实现：检查问题和答案的关键词重叠
        question_tokens = set(question.lower().split())
        answer_tokens = set(answer.lower().split())
        
        overlap = len(question_tokens & answer_tokens)
        total = len(question_tokens | answer_tokens)
        
        return overlap / total if total > 0 else 0.0
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成评估报告"""
        metrics = results.get("metrics", {})
        
        report = f"""# RAG系统评估报告

## 总体指标

| 指标 | 分数 |
|------|------|
| Context Precision | {metrics.get('context_precision', 0):.4f} |
| Context Recall | {metrics.get('context_recall', 0):.4f} |
| Faithfulness | {metrics.get('faithfulness', 0):.4f} |
| Answer Relevancy | {metrics.get('answer_relevancy', 0):.4f} |

## 测试用例数: {results.get('total_cases', 0)}

## 详细结果

"""
        
        for i, detail in enumerate(results.get("details", []), 1):
            report += f"""### 用例 {i}
- 问题: {detail.get('question', '')}
- Context Precision: {detail.get('context_precision', 0):.4f}
- Context Recall: {detail.get('context_recall', 0):.4f}
- Faithfulness: {detail.get('faithfulness', 0):.4f}
- Answer Relevancy: {detail.get('answer_relevancy', 0):.4f}

"""
        
        return report


# 全局评估器实例
evaluator = RAGEvaluator()
