from typer.testing import CliRunner
from backend.app.cli.main import app

runner = CliRunner()


def test_doctor_command():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "System Diagnostics" in result.stdout
    assert "PASS" in result.stdout


def test_info_command():
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "AI Video Studio" in result.stdout
