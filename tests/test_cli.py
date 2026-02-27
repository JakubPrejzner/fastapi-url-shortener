from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli.main import cli
from tests.conftest import FakeRedis


@patch("cli.main._get_redis")
def test_add(mock_redis: MagicMock) -> None:
    mock_redis.return_value = FakeRedis()
    runner = CliRunner()
    result = runner.invoke(cli, ["add", "https://example.com"])
    assert result.exit_code == 0
    assert "http://localhost:9000/" in result.output


@patch("cli.main._get_redis")
def test_update(mock_redis: MagicMock) -> None:
    fake = FakeRedis()
    mock_redis.return_value = fake
    runner = CliRunner()

    # Create first
    result = runner.invoke(cli, ["add", "https://old.com"])
    assert result.exit_code == 0
    code = result.output.strip().rsplit("/", 1)[-1]

    # Update
    result = runner.invoke(cli, ["update", code, "https://new.com"])
    assert result.exit_code == 0
    assert "Updated" in result.output


@patch("cli.main._get_redis")
def test_update_missing(mock_redis: MagicMock) -> None:
    mock_redis.return_value = FakeRedis()
    runner = CliRunner()
    result = runner.invoke(cli, ["update", "missing", "https://x.com"])
    assert result.exit_code != 0


@patch("cli.main._get_redis")
def test_delete(mock_redis: MagicMock) -> None:
    fake = FakeRedis()
    mock_redis.return_value = fake
    runner = CliRunner()

    result = runner.invoke(cli, ["add", "https://example.com"])
    code = result.output.strip().rsplit("/", 1)[-1]

    result = runner.invoke(cli, ["delete", code])
    assert result.exit_code == 0
    assert "Deleted" in result.output


@patch("cli.main._get_redis")
def test_delete_missing(mock_redis: MagicMock) -> None:
    mock_redis.return_value = FakeRedis()
    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "missing"])
    assert result.exit_code != 0


def test_add_rejects_invalid_url() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["add", "not-a-url"])
    assert result.exit_code != 0
    assert "not a valid HTTP URL" in result.output


def test_add_rejects_empty_url() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["add", ""])
    assert result.exit_code != 0
    assert "not a valid HTTP URL" in result.output


@patch("cli.main._get_redis")
def test_add_accepts_valid_http_url(mock_redis: MagicMock) -> None:
    mock_redis.return_value = FakeRedis()
    runner = CliRunner()
    result = runner.invoke(cli, ["add", "https://example.com"])
    assert result.exit_code == 0
