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


class KMANowcastMCPAgentExecutor:
    def __init__(self, mcp_url: str):
        self._mcp_url = mcp_url

    def _mcp_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        with httpx.Client(timeout=15.0) as client:
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

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._mcp_call(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    # ↓↓↓ 여기 메서드 이름/시그니처는 요한님 템플릿에 맞춰 조정하세요.
    # 템플릿이 "execute(text: str) -> str" 형태면 그대로 쓰시면 됩니다.
    def execute(self, text: str) -> str:
        """
        입력 텍스트를 보고:
        - '목록/지원/도시' 류면 list_supported_cities 호출
        - 그 외에는 문장에서 도시명을 찾아 get_now_weather 호출
        """
        t = (text or "").strip()

        # 1) 지원 도시 목록
        if re.search(r"(지원|목록|도시\s*목록)", t):
            res = self._call_tool("list_supported_cities", {})
            return str(res.get("result", res))

        # 2) 도시 날씨 실황
        city = _extract_city(t) or "서울"
        res = self._call_tool("get_now_weather", {"city": city})
        return str(res.get("result", res))
