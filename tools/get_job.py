from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import BailingHubClient, BailingHubClientError
from tools._messages import emit_job_messages


class GetJobTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            job = BailingHubClient.from_credentials(self.runtime.credentials).get_job(
                tool_parameters.get("job_id")
            )
        except BailingHubClientError as exc:
            raise RuntimeError(exc.public_message) from exc
        except (TypeError, ValueError) as exc:
            raise RuntimeError(str(exc)) from exc
        yield from emit_job_messages(self, job)
