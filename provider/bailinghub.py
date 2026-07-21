from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools._client import BailingHubClient, BailingHubClientError


class BailingHubProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            BailingHubClient.from_credentials(credentials).validate_credentials()
        except BailingHubClientError as exc:
            raise ToolProviderCredentialValidationError(exc.public_message) from exc
        except (TypeError, ValueError) as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
