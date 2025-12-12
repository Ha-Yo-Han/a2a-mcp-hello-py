import re

from a2a.server.agent_execution import (  # type: ignore
    AgentExecutor,
    EventQueue,
    RequestContext,
)
from a2a.utils import new_agent_text_message  # type: ignore
from a2a.utils.parts import get_text_parts  # type: ignore

from agent import WeatherMCPAgent  # type: ignore

CITY_CANDIDATES = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]


def _extract_city(text: str) -> str:
    s = (text or "").strip()
    for c in CITY_CANDIDATES:
        if c in s:
            return c
    return "서울"


def _wants_city_list(text: str) -> bool:
    s = (text or "").strip()
    return bool(
        re.search(r"(지원\s*도시|도시\s*목록|지원\s*목록|목록\s*보여|리스트)", s)
    )


def _get_user_text(context: RequestContext) -> str:
    """
    RequestContext(RequestContext)에서 유저 텍스트(TextPart)를 최대한 안전하게 추출합니다.
    SDK 버전에 따라 context.message 또는 context.request.message에 들어있을 수 있어 방어합니다.
    """
    # 1) context.message가 있는 경우
    msg = getattr(context, "message", None)
    if msg is not None and getattr(msg, "parts", None):
        parts = get_text_parts(msg.parts)
        return " ".join(parts).strip()

    # 2) context.request.message가 있는 경우
    req = getattr(context, "request", None)
    if req is not None and getattr(req, "message", None) is not None:
        parts = get_text_parts(req.message.parts)
        return " ".join(parts).strip()

    return ""


class KMANowcastMCPAgentExecutor(AgentExecutor):
    def __init__(self, mcp_url: str):
        self.agent = WeatherMCPAgent(mcp_url)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = _get_user_text(context)
        if not user_text:
            reply = "도시명을 입력해 주세요. 예) 서울 지금 실황"
            await event_queue.enqueue_event(
                new_agent_text_message(
                    reply, context_id=context.context_id, task_id=context.task_id
                )
            )
            return

        # (선택) 여기서 분기하고 싶으면 분기 가능
        # - 다만 WeatherMCPAgent.invoke() 안에서 이미 분기한다면 그냥 넘겨도 됩니다.
        reply = await self.agent.invoke(user_text)

        await event_queue.enqueue_event(
            new_agent_text_message(
                reply, context_id=context.context_id, task_id=context.task_id
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # 단순 에이전트면 cancel 미지원으로 처리해도 됩니다.
        raise Exception("cancel not supported")
