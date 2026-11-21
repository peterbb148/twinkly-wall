"""Verify MCP registration and polling without a live provider."""

from unittest.mock import MagicMock

import pytest

from twinkly_wall import mcp_client


@pytest.mark.parametrize("register", [True, False])
def test_run_only_registers_when_requested(monkeypatch, register):
    client = mcp_client.MCPClient(server_url="http://localhost:8000")
    registration = MagicMock(return_value=True)
    monkeypatch.setattr(client, "register_cards", registration)
    monkeypatch.setattr(mcp_client.time, "sleep", MagicMock())

    def poll_once():
        client.stop()
        return []

    monkeypatch.setattr(client, "poll_commands", poll_once)
    client.run(register=register)
    assert registration.call_count == int(register)
    assert client._running is False


def test_registration_then_polling_preserves_auth_and_command_cursor(monkeypatch):
    client = mcp_client.MCPClient(server_url="http://localhost:8000", api_key="test-key")
    registered = MagicMock()
    registered.json.return_value = {"count": 1}
    post = MagicMock(return_value=registered)
    previous = MagicMock()
    previous.json.return_value = {"commands": [{"id": "cmd_000001"}]}
    current = MagicMock()
    current.json.return_value = {
        "commands": [{"id": "cmd_000002", "type": "twinklysay", "payload": {"text": "Hi"}}]
    }
    get = MagicMock(side_effect=[previous, current])
    monkeypatch.setattr(mcp_client.requests, "post", post)
    monkeypatch.setattr(mcp_client.requests, "get", get)
    assert client.register_cards()
    assert client.last_command_id == "cmd_000001"
    assert client.check_for_commands()
    assert client.last_command_id == "cmd_000002"
    assert client.has_pending_commands()
    assert client.get_next_card() is not None
    assert not client.has_pending_commands()
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert get.call_args.args[0].endswith("?after=cmd_000001")
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
