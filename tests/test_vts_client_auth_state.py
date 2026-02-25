from vtsd.config import VtsdConfig
from vtsd.vts_client import VtsClient


def _client() -> VtsClient:
    client = VtsClient(VtsdConfig())
    client.auth_state = "UNKNOWN"
    return client


def test_sync_auth_state_from_api_state_authenticated_true() -> None:
    client = _client()
    client._sync_auth_state_from_response(  # noqa: SLF001
        "APIStateRequest",
        {"data": {"currentSessionAuthenticated": True}},
    )
    assert client.auth_state == "AUTHENTICATED"


def test_sync_auth_state_from_api_state_authenticated_false() -> None:
    client = _client()
    client._sync_auth_state_from_response(  # noqa: SLF001
        "APIStateRequest",
        {"data": {"currentSessionAuthenticated": False}},
    )
    assert client.auth_state == "UNAUTHENTICATED"


def test_sync_auth_state_from_authentication_request_true() -> None:
    client = _client()
    client._sync_auth_state_from_response(  # noqa: SLF001
        "AuthenticationRequest",
        {"data": {"authenticated": True}},
    )
    assert client.auth_state == "AUTHENTICATED"


def test_sync_auth_state_from_authentication_request_false() -> None:
    client = _client()
    client._sync_auth_state_from_response(  # noqa: SLF001
        "AuthenticationRequest",
        {"data": {"authenticated": False}},
    )
    assert client.auth_state == "UNAUTHENTICATED"


def test_sync_auth_state_ignores_unrelated_message_type() -> None:
    client = _client()
    client._sync_auth_state_from_response("StatisticsRequest", {"data": {}})  # noqa: SLF001
    assert client.auth_state == "UNKNOWN"
