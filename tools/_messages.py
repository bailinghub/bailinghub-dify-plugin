from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage


def emit_job_messages(tool: Any, job: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
    yield tool.create_json_message(job)
    for key in (
        "job_id",
        "request_id",
        "status",
        "terminal",
        "wait_timed_out",
        "route",
        "target",
        "result",
        "error",
    ):
        if key in job:
            yield tool.create_variable_message(key, job[key])
