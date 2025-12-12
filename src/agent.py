"""A2A Agent that uses MCP Weather Nowcast Server."""

import json
import re
from typing import Any

from mcp_client import MCPWeatherClient  # type: ignore

SUPPORTED_CITIES = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]

CITY_ALIASES = {
    "서울시": "서울",
    "서울특별시": "서울",
    "부산시": "부산",
    "부산광역시": "부산",
    "대구시": "대구",
    "대구광역시": "대구",
    "인천시": "인천",
    "인천광역시": "인천",
    "광주시": "광주",
    "광주광역시": "광주",
    "대전시": "대전",
    "대전광역시": "대전",
    "울산시": "울산",
    "울산광역시": "울산",
    "세종시": "세종",
    "세종특별자치시": "세종",
}


def _maybe_json_load(x: Any) -> Any:
    """
    MCP 응답이 str(JSON 문자열)인 경우 dict/list로 파싱 시도합니다.
    실패하면 원본 그대로 반환합니다.
    """
    if isinstance(x, str):
        s = x.strip()
        if (s.startswith("{") and s.endswith("}")) or (
            s.startswith("[") and s.endswith("]")
        ):
            try:
                return json.loads(s)
            except Exception:
                return x
    return x


def _extract_city(user_message: str) -> str:
    msg = (user_message or "").strip()

    # 별칭 먼저 처리
    for k, v in CITY_ALIASES.items():
        if k in msg:
            return v

    # 기본 후보 처리
    for c in SUPPORTED_CITIES:
        if c in msg:
            return c

    return "서울"


def _wants_city_list(user_message: str) -> bool:
    msg = (user_message or "").strip()
    return bool(
        re.search(
            r"(지원\s*도시|도시\s*목록|지원\s*목록|도시\s*리스트|목록\s*보여)", msg
        )
    )


class WeatherMCPAgent:
    """Agent that fetches KMA nowcast using MCP Weather Server."""

    def __init__(self, mcp_url: str):
        self.mcp_client = MCPWeatherClient(mcp_url)

    async def invoke(self, user_message: str) -> str:
        msg = (user_message or "").strip()
        if not msg:
            return "도시명을 입력해 주세요. 예) 서울, 부산, 대구"

        try:
            # 1) 지원 도시 목록
            if _wants_city_list(msg):
                res = await self.mcp_client.list_supported_cities()
                res = _maybe_json_load(res)

                # 예: {"supported_cities": ["서울", ...]} 형태면 깔끔하게 출력
                if isinstance(res, dict) and "supported_cities" in res:
                    cities = ", ".join(res["supported_cities"])
                    return f"지원 도시: {cities}"

                # 그 외에는 JSON 문자열로 반환
                return (
                    json.dumps(res, ensure_ascii=False, indent=2)
                    if not isinstance(res, str)
                    else res
                )

            # 2) 현재 실황 조회
            city = _extract_city(msg)
            res = await self.mcp_client.get_now_weather(city)
            res = _maybe_json_load(res)

            # MCP 서버가 {"ok": false, "error": "..."} 같은 형태로 주는 경우
            if isinstance(res, dict) and res.get("ok") is False:
                return f"조회 실패: {res.get('error', '알 수 없는 오류')}"

            return (
                json.dumps(res, ensure_ascii=False, indent=2)
                if not isinstance(res, str)
                else res
            )

        except Exception as e:
            # A2A에서 무응답처럼 보이지 않게, 항상 문자열로 반환
            return f"에이전트 오류(Exception): {e}"
