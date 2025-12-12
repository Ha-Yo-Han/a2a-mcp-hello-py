"""A2A Server for KMA Nowcast MCP Agent."""

import os

import uvicorn  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

from a2a.server.apps import A2AStarletteApplication  # type: ignore
from a2a.server.request_handlers import DefaultRequestHandler  # type: ignore
from a2a.server.tasks import InMemoryTaskStore  # type: ignore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill  # type: ignore

from agent_executor import KMANowcastMCPAgentExecutor  # type: ignore

# MCP 서버(요한님이 Cloud Run에 올린 FastMCP 서버) 엔드포인트
MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://mcp-hello-py-1056645265236.asia-northeast3.run.app/mcp",
)

# A2A 서버(이 에이전트 자체)의 외부 URL(Cloud Run 환경이면 보통 이 값이 주어짐)
SERVICE_URL = os.environ.get("SERVICE_URL", "")


def create_agent_card(host: str, port: int) -> AgentCard:
    """Create the A2A Agent Card."""
    skill = AgentSkill(
        id="kma_nowcast",
        name="KMA Nowcast",
        description="광역시명을 받아 기상청 초단기실황을 조회해 사람이 읽기 좋은 JSON으로 제공합니다. MCP 서버를 사용합니다.",
        tags=["weather", "kma", "nowcast", "mcp", "korea"],
        examples=[
            "서울 지금 날씨 실황 알려줘",
            "부산 실황 보여줘",
            "지원 도시 목록 알려줘",
        ],
    )

    if SERVICE_URL:
        agent_url = SERVICE_URL
    else:
        agent_url = f"http://{host}:{port}/"

    return AgentCard(
        name="KMA Nowcast MCP Agent",
        description="MCP Weather Server를 사용하여 기상청 초단기실황을 조회하고 요약/정리해주는 A2A 에이전트입니다.",
        url=agent_url,
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )


def main():
    """Main entry point."""
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 9999))

    agent_card = create_agent_card(host, port)

    request_handler = DefaultRequestHandler(
        agent_executor=KMANowcastMCPAgentExecutor(MCP_SERVER_URL),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    print(f"Starting A2A KMA Nowcast MCP Agent on {host}:{port}")
    print(f"MCP Server URL: {MCP_SERVER_URL}")
    print(f"Service URL: {SERVICE_URL or f'http://{host}:{port}/'}")

    uvicorn.run(server.build(), host=host, port=port)


if __name__ == "__main__":
    main()
