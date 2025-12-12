"""MCP Client for calling MCP Weather Nowcast Server."""

from typing import Any

from mcp import ClientSession  # type: ignore
from mcp.client.streamable_http import streamablehttp_client  # type: ignore


class MCPWeatherClient:
    """Client to interact with MCP Weather Nowcast Server."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        MCP 서버의 tool을 호출하고, 첫 번째 content.text가 있으면 그걸 우선 반환합니다.
        없으면 result 자체를 dict/str로 반환합니다.
        """
        async with streamablehttp_client(self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                # FastMCP(json_response=True)인 경우, result.content[0].text 안에
                # JSON 문자열이 들어오는 형태가 흔해서 그대로 우선 반환합니다.
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text") and content.text is not None:
                        return content.text

                # 그래도 없으면 result를 그대로 반환(디버깅용)
                return result

    async def list_supported_cities(self) -> Any:
        """Call the list_supported_cities tool on MCP server."""
        return await self._call_tool("list_supported_cities", arguments={})

    async def get_now_weather(self, city: str) -> Any:
        """Call the get_now_weather tool on MCP server."""
        return await self._call_tool("get_now_weather", arguments={"city": city})

    async def list_tools(self) -> list[dict[str, str]]:
        """List available tools from MCP server."""
        async with streamablehttp_client(self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                return [
                    {"name": tool.name, "description": tool.description}
                    for tool in tools.tools
                ]
