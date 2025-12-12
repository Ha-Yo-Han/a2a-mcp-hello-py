import json
import re
from typing import Any, Dict, Optional

import httpx

CITY_CANDIDATES = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
]


def _extract_city(text: str) -> Optional[str]:
    s = (text or "").strip()
    for c in CITY_CANDIDATES:
        if c in s:
            return c
    return None


def _tool_result_to_text(tool_result: Any) -> str:
    """
    FastMCP(json_response=True)에서 tools/call의 result는 보통 다음 형태입니다.
    {
      "content":[{"type":"text","text":"{...JSON 문자열...}"}],
      "isError": false
    }
    """
    if isinstance(tool_result, dict):
        # 1) content[0].text 우선
        content = tool_result.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if (
                isinstance(first, dict)
                and first.get("type") == "text"
                and "text" in first
            ):
                return str(first["text"])

        # 2) result 자체를 보기 좋게
        try:
            return json.dumps(tool_result, ensure_ascii=False, indent=2)
        except Exception:
            return str(tool_result)

    return str(tool_result)


class KMANowcastMCPAgentExecutor:
    def __init__(self, mcp_url: str):
        self._mcp_url = (mcp_url or "").strip().rstrip("/")
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _mcp_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                r = client.post(
                    self._mcp_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                r.raise_for_status()
                return r.json()

        except httpx.TimeoutException:
            return {"error": {"message": "MCP 호출 타임아웃(timeout)"}}

        except httpx.HTTPStatusError as e:
            return {
                "error": {
                    "message": f"HTTP {e.response.status_code}: {e.response.text}"
                }
            }

        except httpx.RequestError as e:
            return {"error": {"message": f"RequestError: {e}"}}

        except Exception as e:
            return {"error": {"message": f"UnexpectedError: {e}"}}

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._mcp_call(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    def execute(self, text: str) -> str:
        """
        입력 텍스트를 보고:
        - '목록/지원/도시' 류면 list_supported_cities 호출
        - 그 외에는 문장에서 도시명을 찾아 get_now_weather 호출
        """
        t = (text or "").strip()

        # 0) MCP 호출 자체가 깨진 경우
        def _handle_rpc(res: Dict[str, Any]) -> str:
            if isinstance(res, dict) and "error" in res and res["error"]:
                return f"오류: {res['error'].get('message', res['error'])}"

            # JSON-RPC 응답은 보통 {"result": {...}} 형태
            result = res.get("result", res)
            return _tool_result_to_text(result)

        # 1) 지원 도시 목록
        if re.search(r"(지원|목록|도시\s*목록)", t):
            res = self._call_tool("list_supported_cities", {})
            return _handle_rpc(res)

        # 2) 도시 날씨 실황
        city = _extract_city(t) or "서울"
        res = self._call_tool("get_now_weather", {"city": city})
        return _handle_rpc(res)
