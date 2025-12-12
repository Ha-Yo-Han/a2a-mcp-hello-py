"""MCP Client (HTTP JSON-RPC) for calling MCP Weather Nowcast Server."""

from __future__ import annotations

import itertools
import json
from typing import Any

import httpx


class MCPWeatherClient:
    """Client to interact with MCP Weather Nowcast Server over plain HTTP JSON-RPC."""

    def __init__(self, mcp_url: str):
        # /mcp로 들어오는 URL을 가정
        self.mcp_url = (mcp_url or "").strip().rstrip("/")
        self._ids = itertools.count(1)
        self._client = httpx.AsyncClient(timeout=20.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _jsonrpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": method,
            "params": params,
        }

        r = await self._client.post(
            self.mcp_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )
        r.raise_for_status()

        data = r.json()

        # JSON-RPC error
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(str(data["error"]))

        # 정상 응답(result)
        if isinstance(data, dict) and "result" in data:
            result = data["result"]
            if isinstance(result, dict):
                return result
            return {"value": result}

        # 예외 케이스(서버가 바로 주는 경우)
        if isinstance(data, dict):
            return data

        return {"value": data}

    def _tool_result_to_json(self, tool_result: dict[str, Any]) -> Any:
        """
        FastMCP(json_response=True) tool 응답은 보통
        {
                "content":[{"type":"text","text":"{...JSON 문자열...}"}],
                "isError": false
        }
        형태라서 text가 JSON이면 dict로 파싱합니다.
        """
        if not isinstance(tool_result, dict):
            return tool_result

        # 1) structuredContent가 있으면 우선 사용(있을 때만)
        if (
            "structuredContent" in tool_result
            and tool_result["structuredContent"] is not None
        ):
            return tool_result["structuredContent"]

        # 2) content[0].text 파싱
        content = tool_result.get("content")
        if (
            isinstance(content, list)
            and len(content) > 0
            and isinstance(content[0], dict)
        ):
            text = content[0].get("text")
            if isinstance(text, str):
                s = text.strip()
                # JSON 문자열이면 dict로 변환 시도
                if (s.startswith("{") and s.endswith("}")) or (
                    s.startswith("[") and s.endswith("]")
                ):
                    try:
                        return json.loads(s)
                    except Exception:
                        return {"raw_text": text}
                return {"text": text}

        return tool_result

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        result = await self._jsonrpc(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )

        # tool 실행 결과를 JSON으로 정리
        return self._tool_result_to_json(result)

    async def list_supported_cities(self) -> Any:
        return await self._call_tool("list_supported_cities", {})

    async def get_now_weather(self, city: str) -> Any:
        return await self._call_tool("get_now_weather", {"city": city})

    async def list_tools(self) -> Any:
        return await self._jsonrpc("tools/list", {})
