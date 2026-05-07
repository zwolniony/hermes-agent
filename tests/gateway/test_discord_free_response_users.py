import os

from gateway.config import Platform, PlatformConfig, load_gateway_config
from gateway.platforms.discord import DiscordAdapter


def test_discord_free_response_users_accepts_list_and_csv(monkeypatch):
    adapter = DiscordAdapter(
        PlatformConfig(
            enabled=True,
            token="dummy",
            extra={"free_response_users": [123, "456"]},
        )
    )
    assert adapter._discord_free_response_users() == {"123", "456"}

    adapter.config.extra.pop("free_response_users")
    monkeypatch.setenv("DISCORD_FREE_RESPONSE_USERS", "789, abc")
    assert adapter._discord_free_response_users() == {"789", "abc"}


def test_discord_user_prompt_resolution_and_combination():
    adapter = DiscordAdapter(
        PlatformConfig(
            enabled=True,
            token="dummy",
            extra={"user_prompts": {"235": " Björn prompt "}},
        )
    )
    assert adapter._resolve_user_prompt("235") == " Björn prompt "
    assert adapter._resolve_user_prompt("999") is None
    assert adapter._combine_prompts("channel", " user ") == "channel\n\nuser"
    assert adapter._combine_prompts(None, " ") is None


def test_config_bridges_discord_free_response_users_and_user_prompts(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "config.yaml").write_text(
        """
model:
  provider: openai-codex
  model: gpt-5.5
discord:
  enabled: true
  free_response_users:
    - "235"
  user_prompts:
    "235": "Björn prompt"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy")
    monkeypatch.delenv("DISCORD_FREE_RESPONSE_USERS", raising=False)

    config = load_gateway_config()
    discord_cfg = config.platforms[Platform.DISCORD]
    assert discord_cfg.extra["free_response_users"] == ["235"]
    assert discord_cfg.extra["user_prompts"] == {"235": "Björn prompt"}
    assert os.getenv("DISCORD_FREE_RESPONSE_USERS") == "235"
