import importlib.util
import os
from glob import glob
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Callable, cast

from azure.ai.agents.models import FunctionTool, McpTool, ToolSet


def agent_function_tool(func: Callable) -> Callable:
    setattr(func, "_is_agent_tool", True)
    return func


def load_tools(tool_dir: str | None = "./tools") -> ToolSet:
    tool_set = ToolSet()

    if tool_dir is None:
        return tool_set

    if not os.path.exists(tool_dir):
        raise ValueError(f"Given directory does not exist: {tool_dir}")

    module_paths = [Path(p).resolve() for p in glob(tool_dir + "/*.py")]
    for path in module_paths:
        func_tools, mcp_tools = load_tool_from_path(path)
        tool_set.add(func_tools)
        for mcp_tool in mcp_tools:
            tool_set.add(mcp_tool)

    return tool_set


def load_tool_from_path(path: Path) -> tuple[FunctionTool, list[McpTool]]:
    module_name = os.path.basename(path).split(".")[0]
    spec: ModuleSpec = cast(
        ModuleSpec, importlib.util.spec_from_file_location(module_name, path)
    )

    if not spec:
        raise ImportError(f"Could not create spec for {module_name}")
    if not spec.loader:
        raise ImportError(f"No loader available for {module_name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    funcs = []
    mcp_tools: list[McpTool] = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if getattr(attr, "_is_agent_tool", False):
            funcs.append(attr)
        if isinstance(attr, McpTool):
            mcp_tools.append(attr)

    return FunctionTool(set(funcs)), mcp_tools


def load_instructions(path: str) -> str:
    with open(path, "r") as file:
        instructions = file.read()
    return instructions


THREADS: dict[str, dict[str, str]] = {}


def get_thread_id(channel_id: str | None, conversation_id: str) -> str | None:
    if channel_id is None:
        channel_id = "unknown"
    if channel_id not in THREADS:
        return None
    thread_id = THREADS[channel_id].get(conversation_id, None)
    return thread_id


def set_thread_id(channel_id: str | None, conversation_id: str, thread_id: str):
    if channel_id is None:
        channel_id = "unknown"
    if channel_id not in THREADS:
        THREADS[channel_id] = {}
    THREADS[channel_id][conversation_id] = thread_id
