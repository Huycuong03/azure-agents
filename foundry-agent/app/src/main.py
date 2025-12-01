from os import getenv

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.core import AuthTypes, MemoryStorage, TurnContext
from microsoft_agents.hosting.core.app import AgentApplication
from microsoft_agents.hosting.fastapi import CloudAdapter, start_agent_process
from src.utils import get_thread_id, load_instructions, load_tools, set_thread_id

load_dotenv()

app = FastAPI()
connection_manager = MsalConnectionManager(
    connections_configurations={
        "SERVICE_CONNECTION": {
            "auth_type": AuthTypes.user_managed_identity,
            "client_id": getenv("AZURE_CLIENT_ID"),  # type: ignore
        }
    }
)
adapter = CloudAdapter(connection_manager=connection_manager)
agent_app = AgentApplication(storage=MemoryStorage(), adapter=adapter)

agent_client = AgentsClient(
    endpoint=getenv("AIF_PROJECT_ENDPOINT"),  # type: ignore
    credential=DefaultAzureCredential(),
)
toolset = load_tools(getenv("AGENT_TOOL_DIR"))  # type: ignore
agent_client.enable_auto_function_calls(toolset)
agent_id = getenv("AIF_AGENT_ID", None)  # type: ignore

if agent_id is None:
    instructions = load_instructions(getenv("AGENT_INSTRUCTIONS_PATH"))  # type: ignore
    agent = agent_client.create_agent(
        model=getenv("AGENT_DEPLOYMENT"),  # type: ignore
        name=getenv("AGENT_NAME"),  # type: ignore
        instructions=instructions,
        toolset=toolset,
    )
    agent_id = agent.id


@agent_app.activity("message")
async def on_message(context: TurnContext, state):
    channel_id = context.activity.channel_id
    conversation_id = context.activity.conversation.id
    try:
        thread_id = get_thread_id(channel_id, conversation_id)
        if thread_id is None:
            raise HttpResponseError("Thread ID not found")
        thread = agent_client.threads.get(thread_id=thread_id)
    except HttpResponseError:
        thread = agent_client.threads.create()
        set_thread_id(channel_id, conversation_id, thread.id)

    agent_client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=context.activity.text,
    )
    run = agent_client.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)  # type: ignore
    if run.status == "failed":
        response = f"Sorry, something went wrong while processing your request. {run.last_error}"
    else:
        response = agent_client.messages.get_last_message_text_by_role(
            thread_id=thread.id, role=MessageRole.AGENT
        )
        response = response.text.value  # type: ignore
    await context.send_activity(response)


@app.post("/api/messages")
async def messages(request: Request):
    return await start_agent_process(request, agent_app, adapter)
