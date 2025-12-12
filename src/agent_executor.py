from a2a.server.agent_execution import AgentExecutor, RequestContext  # type: ignore
from a2a.server.events.event_queue import EventQueue  # type: ignore
from a2a.utils import new_agent_text_message  # type: ignore

from agent import WeatherMCPAgent  # type: ignore


class KMANowcastMCPAgentExecutor(AgentExecutor):
    def __init__(self, mcp_url: str):
        self.agent = WeatherMCPAgent(mcp_url)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # SDK 공식 API로 유저 입력 추출 (가장 안전) :contentReference[oaicite:4]{index=4}
        user_text = (context.get_user_input() or "").strip()

        if not user_text:
            reply = "도시명을 입력해 주세요. 예) 서울 지금 실황"
            await event_queue.enqueue_event(
                new_agent_text_message(
                    reply,
                    context_id=context.context_id,
                    task_id=context.task_id,
                )
            )
            return

        try:
            reply = await self.agent.invoke(user_text)
        except Exception as e:
            reply = f"에이전트 처리 중 오류가 발생했습니다: {e}"

        # new_agent_text_message는 context_id/task_id를 옵션으로 받습니다 :contentReference[oaicite:5]{index=5}
        await event_queue.enqueue_event(
            new_agent_text_message(
                reply,
                context_id=context.context_id,
                task_id=context.task_id,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")
