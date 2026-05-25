from typing import Dict, Any
from langchain.prompts import PromptTemplate


class AgentPrompts:
    """Agent提示词模板管理"""
    
    # 系统提示词 - 定义Agent角色和行为
    SYSTEM_PROMPT = """你是一个专业的婴儿智能看护AI Agent。你的职责是：
1. 分析视频监控数据，识别婴儿周围的潜在危险
2. 根据检测结果做出智能决策
3. 在必要时向家长发送警报通知
4. 提供专业的育儿建议
5. 控制智能家居设备，为婴儿营造舒适环境

你具备以下工具能力：
- video_detection: 分析视频帧，检测危险物品、窒息风险和异常姿态
- send_notification: 向用户发送报警通知
- device_management: 管理监控设备
- smart_speaker: 控制智能音箱，播放白噪音、摇篮曲等安抚婴儿
- smart_light: 控制婴儿房灯光，调节亮度和颜色
- smart_scene: 控制智能家居场景模式（睡眠、安抚、警报等）

智能家居使用指南：
- 当检测到婴儿哭闹时，可以播放白噪音或摇篮曲安抚
- 当环境过暗时，可以开启柔光模式
- 当婴儿入睡时，可以启动睡眠模式（暗光+白噪音）
- 当检测到危险时，可以启动警报模式（亮光+提醒）

请始终保持警惕，优先确保婴儿安全。在做出决策时，考虑以下因素：
- 危险级别：safe（安全）、warning（警告）、danger（危险）
- 置信度：检测结果的可信程度
- 上下文：之前的检测历史和当前环境
- 婴儿状态：睡眠/清醒/哭闹

你的回复应该简洁、专业，并包含明确的行动建议。"""
    
    # 检测分析提示词
    DETECTION_ANALYSIS_PROMPT = PromptTemplate(
        input_variables=["detection_results", "context"],
        template="""请分析以下视频检测结果，并给出安全评估：

检测结果：
{detection_results}

上下文信息：
{context}

请提供：
1. 整体安全级别评估（safe/warning/danger）
2. 主要风险点分析
3. 建议采取的行动
4. 是否需要发送通知（是/否）

回复格式：
安全级别：[级别]
风险分析：[分析]
建议行动：[行动]
需要通知：[是/否]"""
    )
    
    # 通知生成提示词
    NOTIFICATION_PROMPT = PromptTemplate(
        input_variables=["detection_type", "risk_level", "details"],
        template="""请根据以下检测信息生成家长通知：

检测类型：{detection_type}
风险级别：{risk_level}
详细信息：{details}

要求：
1. 通知标题简洁明了
2. 通知内容包含具体风险描述
3. 提供简要的应对建议
4. 语气专业但温和，避免引起过度恐慌

请生成通知内容："""
    )
    
    # 育儿建议提示词（为阶段三RAG准备）
    PARENTING_ADVICE_PROMPT = PromptTemplate(
        input_variables=["situation", "baby_age", "context"],
        template="""请根据以下情况提供专业的育儿建议：

情况描述：{situation}
婴儿月龄：{baby_age}
上下文：{context}

请提供：
1. 情况分析
2. 专业建议
3. 注意事项
4. 后续观察要点

回复应该基于科学育儿知识，简洁实用。"""
    )
    
    # 决策推理提示词
    DECISION_REASONING_PROMPT = PromptTemplate(
        input_variables=["current_state", "history", "available_actions"],
        template="""作为婴儿看护Agent，请基于当前状态做出决策：

当前状态：
{current_state}

历史记录：
{history}

可用行动：
{available_actions}

请分析并选择最佳行动方案，考虑：
1. 婴儿安全优先
2. 避免误报干扰
3. 及时响应真实风险
4. 合理使用系统资源

决策结果："""
    )
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """获取系统提示词"""
        return cls.SYSTEM_PROMPT
    
    @classmethod
    def format_detection_analysis(
        cls,
        detection_results: Dict[str, Any],
        context: str = ""
    ) -> str:
        """格式化检测分析提示词"""
        import json
        results_str = json.dumps(detection_results, ensure_ascii=False, indent=2)
        return cls.DETECTION_ANALYSIS_PROMPT.format(
            detection_results=results_str,
            context=context or "无额外上下文"
        )
    
    @classmethod
    def format_notification(
        cls,
        detection_type: str,
        risk_level: str,
        details: str
    ) -> str:
        """格式化通知生成提示词"""
        return cls.NOTIFICATION_PROMPT.format(
            detection_type=detection_type,
            risk_level=risk_level,
            details=details
        )
    
    @classmethod
    def format_decision_reasoning(
        cls,
        current_state: Dict[str, Any],
        history: str,
        available_actions: str
    ) -> str:
        """格式化决策推理提示词"""
        import json
        state_str = json.dumps(current_state, ensure_ascii=False, indent=2)
        return cls.DECISION_REASONING_PROMPT.format(
            current_state=state_str,
            history=history or "无历史记录",
            available_actions=available_actions
        )
