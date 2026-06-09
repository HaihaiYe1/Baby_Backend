from typing import List, Dict, Any, Optional
import os


class MCPManager:
    """
    MCP (Model Context Protocol) 管理器
    
    用于管理MCP客户端连接和工具
    """
    
    def __init__(self):
        self._client = None
        self._tools: List[Any] = []
        self._initialized = False
    
    async def initialize(self, servers: Dict[str, Dict[str, Any]] = None) -> None:
        """
        初始化MCP客户端
        
        Args:
            servers: MCP服务器配置
        """
        if self._initialized:
            return
        
        if servers is None:
            servers = self._get_default_servers()
        
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            self._client = MultiServerMCPClient(servers)
            self._tools = await self._client.get_tools()
            self._initialized = True
            
            print(f"MCP initialized with {len(self._tools)} tools")
            
        except ImportError:
            print("langchain-mcp-adapters not installed, MCP disabled")
        except Exception as e:
            print(f"MCP initialization error: {e}")
    
    def _get_default_servers(self) -> Dict[str, Dict[str, Any]]:
        """获取默认MCP服务器配置"""
        return {
            "smart_home": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "app.mcp.smart_home_server"]
            }
        }
    
    def get_tools(self) -> List[Any]:
        """获取MCP工具列表"""
        return self._tools
    
    async def get_tools_async(self) -> List[Any]:
        """异步获取MCP工具列表"""
        if not self._initialized:
            await self.initialize()
        return self._tools
    
    async def close(self) -> None:
        """关闭MCP客户端"""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                print(f"MCP close error: {e}")
            finally:
                self._initialized = False
                self._client = None
                self._tools = []


class MCPToolAdapter:
    """MCP工具适配器"""
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
    
    async def get_langchain_tools(self) -> List[Any]:
        """获取LangChain格式的工具"""
        return await self.mcp_manager.get_tools_async()
    
    def filter_tools(
        self,
        tools: List[Any],
        tool_names: List[str]
    ) -> List[Any]:
        """过滤工具"""
        return [t for t in tools if t.name in tool_names]


# 全局MCP管理器实例
mcp_manager = MCPManager()
mcp_tool_adapter = MCPToolAdapter(mcp_manager)
