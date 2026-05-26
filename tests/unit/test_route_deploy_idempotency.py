import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _setup_temp_project(home: Path) -> Path:
    project_dir = home / "Documents" / "trae_projects" / "qq"
    project_dir.mkdir(parents=True, exist_ok=True)

    for name in [
        "deploy-routes.sh",
        "claude-use-anthropic-official.sh",
        "claude-use-volcengine-ark.sh",
        "claude-use-deepseek.sh",
        "claude-use-deepseek-flash.sh",
        "claude-use-deepseek-flash-full.sh",
    ]:
        shutil.copy2(REPO_ROOT / name, project_dir / name)
    return project_dir


def _run_deploy(project_dir: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(project_dir / "deploy-routes.sh")],
        cwd=project_dir,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def _read_zshrc(home: Path) -> str:
    return (home / ".zshrc").read_text(encoding="utf-8")


def test_first_and_repeated_deploy_are_idempotent(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text("# seed\n", encoding="utf-8")

    project_dir = _setup_temp_project(home)

    _run_deploy(project_dir, home)
    _run_deploy(project_dir, home)

    zshrc = _read_zshrc(home)
    assert zshrc.count("# BEGIN CLAUDE_ROUTE_SWITCHERS") == 1
    assert zshrc.count("# END CLAUDE_ROUTE_SWITCHERS") == 1
    assert zshrc.count('export PATH="$HOME/.ai-routes:$PATH"') == 1


def test_new_route_after_prior_deploy_is_auto_discovered(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text("", encoding="utf-8")

    project_dir = _setup_temp_project(home)
    _run_deploy(project_dir, home)

    shutil.copy2(REPO_ROOT / "claude-use-mimo-full.sh", project_dir / "claude-use-mimo-full.sh")
    _run_deploy(project_dir, home)

    env = os.environ.copy()
    env["HOME"] = str(home)
    cmd = "source ~/.zshrc; command -v cc-mimo-full; which cc-mimo-full || true"
    result = subprocess.run(["bash", "-lc", cmd], env=env, check=True, text=True, capture_output=True)
    assert "cc-mimo-full" in result.stdout


def test_path_guard_keeps_ai_routes_single_entry(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text("", encoding="utf-8")

    project_dir = _setup_temp_project(home)
    _run_deploy(project_dir, home)

    env = os.environ.copy()
    env["HOME"] = str(home)
    cmd = (
        "source ~/.zshrc; "
        "source ~/.zshrc; "
        "echo \"$PATH\" | tr ':' '\\n' | grep -F \"$HOME/.ai-routes\" | wc -l"
    )
    result = subprocess.run(["bash", "-lc", cmd], env=env, check=True, text=True, capture_output=True)
    assert result.stdout.strip() == "1"
