"""A2A Agent that uses MCP Weather Nowcast Server."""

import re

from mcp_client import MCPWeatherClient  # type: ignore

SUPPORTED_CITIES = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]


def _extract_city(user_message: str) -> str:
    """
    사용자 메시지에서 광역시명을 찾아 반환합니다.
    없으면 기본값으로 '서울'을 반환합니다.
    """
    msg = (user_message or "").strip()

    for c in SUPPORTED_CITIES:
        if c in msg:
            return c

    return "서울"


def _wants_city_list(user_message: str) -> bool:
    """
    '지원 도시 목록' 류의 요청인지 간단히 판별합니다.
    """
    msg = (user_message or "").strip()
    return bool(re.search(r"(지원\s*도시|도시\s*목록|지원\s*목록|목록\s*보여)", msg))


class WeatherMCPAgent:
    """Agent that fetches KMA nowcast using MCP Weather Server."""

    def __init__(self, mcp_url: str):
        self.mcp_client = MCPWeatherClient(mcp_url)

    async def invoke(self, user_message: str) -> str:
        """
        사용자 메시지를 처리해 MCP 도구를 호출합니다.

        - '지원 도시 목록' 요청: list_supported_cities
        - 그 외: get_now_weather(city)
        """
        msg = (user_message or "").strip()

        # 1) 지원 도시 목록
        if _wants_city_list(msg):
            res = await self.mcp_client.list_supported_cities()
            # res가 dict면 보기 좋게 문자열로 변환(템플릿 스타일에 맞춰 간단히)
            if isinstance(res, dict) and "supported_cities" in res:
                cities = ", ".join(res["supported_cities"])
                return f"지원 도시: {cities}"
            return str(res)

        # 2) 현재 실황 조회
        city = _extract_city(msg)
        res = await self.mcp_client.get_now_weather(city)

        # MCP 서버 응답이 ok=false면 에러를 사람이 읽기 좋게 반환
        if isinstance(res, dict) and res.get("ok") is False:
            return f"조회 실패: {res.get('error', '알 수 없는 오류')}"

        return str(res)
