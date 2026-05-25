from typing import Dict, Any, List, Optional, Type
from langchain.tools import BaseTool


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        """初始化工具注册中心"""
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, tool: BaseTool, category: str = "general") -> bool:
        """
        注册工具
        
        Args:
            tool: 工具实例
            category: 工具类别
            
        Returns:
            是否注册成功
        """
        try:
            tool_name = tool.name
            
            if tool_name in self._tools:
                print(f"工具 {tool_name} 已存在，将被覆盖")
            
            self._tools[tool_name] = tool
            
            # 添加到类别
            if category not in self._categories:
                self._categories[category] = []
            
            if tool_name not in self._categories[category]:
                self._categories[category].append(tool_name)
            
            print(f"工具 {tool_name} 注册成功，类别: {category}")
            return True
            
        except Exception as e:
            print(f"注册工具失败: {e}")
            return False
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否注销成功
        """
        if tool_name not in self._tools:
            print(f"工具 {tool_name} 不存在")
            return False
        
        try:
            del self._tools[tool_name]
            
            # 从类别中移除
            for category, tools in self._categories.items():
                if tool_name in tools:
                    tools.remove(tool_name)
            
            print(f"工具 {tool_name} 注销成功")
            return True
            
        except Exception as e:
            print(f"注销工具失败: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具实例
        """
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        获取所有工具
        
        Returns:
            工具列表
        """
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """
        按类别获取工具
        
        Args:
            category: 工具类别
            
        Returns:
            工具列表
        """
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_categories(self) -> List[str]:
        """
        获取所有类别
        
        Returns:
            类别列表
        """
        return list(self._categories.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具信息
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具信息
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else None
        }
    
    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """
        获取所有工具信息
        
        Returns:
            工具信息列表
        """
        return [self.get_tool_info(name) for name in self._tools.keys()]
    
    def search_tools(self, query: str) -> List[BaseTool]:
        """
        搜索工具
        
        Args:
            query: 搜索查询
            
        Returns:
            匹配的工具列表
        """
        query_lower = query.lower()
        matched_tools = []
        
        for tool in self._tools.values():
            # 搜索名称和描述
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower()):
                matched_tools.append(tool)
        
        return matched_tools
    
    def clear(self):
        """清空所有工具"""
        self._tools.clear()
        self._categories.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取注册中心状态
        
        Returns:
            状态信息
        """
        return {
            "total_tools": len(self._tools),
            "categories": {cat: len(tools) for cat, tools in self._categories.items()},
            "tool_names": list(self._tools.keys())
        }


# 全局工具注册中心实例
tool_registry = ToolRegistry()
