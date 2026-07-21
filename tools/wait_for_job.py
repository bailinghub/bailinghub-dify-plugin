from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import BailingHubClient, BailingHubClientError
from tools._messages import emit_job_messages


class WaitForJobTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            job = BailingHubClient.from_credentials(self.runtime.credentials).wait_for_job(
                tool_parameters.get("job_id"),
                max_wait_seconds=tool_parameters.get("max_wait_seconds", 20),
                poll_interval_seconds=tool_parameters.get("poll_interval_seconds", 2),
            )
        except BailingHubClientError as exc:
            raise RuntimeError(exc.public_message) from exc
        except (TypeError, ValueError) as exc:
            raise RuntimeError(str(exc)) from exc
        yield from emit_job_messages(self, job)
