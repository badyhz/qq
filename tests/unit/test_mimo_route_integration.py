import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_mimo_provider_script_auth_and_defaults() -> None:
    text = _read("claude-use-mimo-full.sh")

    assert 'if [ -z "${MIMO_API_KEY:-}" ]; then' in text
    assert 'export MIMO_BASE_URL="${MIMO_BASE_URL:-https://token-plan-cn.xiaomimimo.com/v1}"' in text
    assert (
        'export MIMO_ANTHROPIC_BASE_URL="${MIMO_ANTHROPIC_BASE_URL:-https://token-plan-cn.xiaomimimo.com/anthropic}"'
        in text
    )
    assert 'export ANTHROPIC_BASE_URL="$MIMO_ANTHROPIC_BASE_URL"' in text
    assert 'export ANTHROPIC_AUTH_TOKEN="$MIMO_API_KEY"' in text


def test_mimo_model_alias_mapping() -> None:
    text = _read("claude-use-mimo-full.sh")

    assert 'CANONICAL_MIMO_MODEL="mimo-v2.5"' in text
    assert 'NORMALIZED_MIMO_MODEL="$(printf \'%s\' "$RAW_MIMO_MODEL" | tr \'[:upper:]\' \'[:lower:]\')"' in text
    assert 'export ANTHROPIC_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_DEFAULT_OPUS_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_DEFAULT_SONNET_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_DEFAULT_HAIKU_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_SMALL_FAST_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export CLAUDE_CODE_SUBAGENT_MODEL="$CANONICAL_MIMO_MODEL"' in text


def test_mimo_full_access_flags_match_full_route_policy() -> None:
    mimo = _read("claude-use-mimo-full.sh")
    deep_full = _read("claude-use-deepseek-flash-full.sh")

    expected_flags = 'exec claude --permission-mode bypassPermissions --dangerously-skip-permissions "$@"'
    assert expected_flags in mimo
    assert expected_flags in deep_full


def test_route_resolver_and_cli_help_include_mimo_full() -> None:
    deploy = _read("deploy-routes.sh")

    assert "_cc_route_register_dynamic" in deploy
    assert "for script in \"$_cc_route_dir\"/claude-use-*.sh;" in deploy
    assert "echo \"  cc-$route\"" in deploy
    assert "echo \"  cc-test-$route\"" in deploy


def test_provider_registry_and_docs_include_mimo() -> None:
    install = _read("install-routes.sh")
    routes_doc = _read("automation/model_routes.md")

    assert "ROUTE_SCRIPTS=(~/Documents/trae_projects/qq/claude-use-*.sh)" in install
    assert "chmod +x ~/.ai-routes/claude-use-*.sh" in install

    assert "MiMo full route: `cc-mimo-full`" in routes_doc
    assert "MiMo Full / Bypass: `mimo-v2.5`" in routes_doc
    assert "Anthropic-compatible API" in routes_doc
    assert "MIMO_ANTHROPIC_BASE_URL" in routes_doc
    assert "MIMO_BASE_URL" in routes_doc
    assert "MIMO_API_KEY" in routes_doc


def test_existing_routes_still_present() -> None:
    deploy = _read("deploy-routes.sh")

    assert "cc-deep-flash-full() { cc-deepseek-flash-full" in deploy
    assert "cc-deep-flash-bypass() { cc-deepseek-flash-full" in deploy
    assert "cc-deep-flash-unsafe() { cc-deepseek-flash-full" in deploy
    assert "cc-ark() { cc-volcengine-ark" in deploy
    assert "cc-deep() { cc-deepseek" in deploy


def test_mimo_full_route_invocation_propagates_auth_and_flags(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace_file = tmp_path / "trace.txt"
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"{{ printf 'ARGS=%s\\n' \"$*\"; printf 'BASE=%s\\n' \"${{ANTHROPIC_BASE_URL:-}}\"; "
                f"printf 'TOKEN=%s\\n' \"${{ANTHROPIC_AUTH_TOKEN:-}}\"; printf 'MODEL=%s\\n' "
                f"\"${{ANTHROPIC_MODEL:-}}\"; }} > \"{trace_file}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_BASE_URL"] = "https://token-plan-cn.xiaomimimo.com/v1"
    env["MIMO_ANTHROPIC_BASE_URL"] = "https://token-plan-cn.xiaomimimo.com/anthropic"

    script = REPO_ROOT / "claude-use-mimo-full.sh"
    subprocess.run(
        [str(script), "-p", "OK"],
        check=True,
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    trace = trace_file.read_text(encoding="utf-8")
    assert "ARGS=--permission-mode bypassPermissions --dangerously-skip-permissions -p OK" in trace
    assert "BASE=https://token-plan-cn.xiaomimimo.com/anthropic" in trace
    assert "TOKEN=mimo_test_key" in trace
    assert "MODEL=mimo-v2.5" in trace


def test_mimo_full_route_does_not_use_openai_v1_as_anthropic_base(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace_file = tmp_path / "trace.txt"
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf 'BASE=%s\\n' \"${{ANTHROPIC_BASE_URL:-}}\" > \"{trace_file}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_BASE_URL"] = "https://token-plan-cn.xiaomimimo.com/v1"

    script = REPO_ROOT / "claude-use-mimo-full.sh"
    subprocess.run(
        [str(script), "-p", "OK"],
        check=True,
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    trace = trace_file.read_text(encoding="utf-8")
    assert "BASE=https://token-plan-cn.xiaomimimo.com/anthropic" in trace
    assert "BASE=https://token-plan-cn.xiaomimimo.com/v1" not in trace


def test_mimo_model_normalization_accepts_title_case_input(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace_file = tmp_path / "trace.txt"
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf 'MODEL=%s\\n' \"${{ANTHROPIC_MODEL:-}}\" > \"{trace_file}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_MODEL"] = "MiMo-V2.5"

    script = REPO_ROOT / "claude-use-mimo-full.sh"
    subprocess.run(
        [str(script), "-p", "OK"],
        check=True,
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    trace = trace_file.read_text(encoding="utf-8")
    assert "MODEL=mimo-v2.5" in trace


# --- MiMo Pro route tests ---


def test_mimo_pro_provider_script_auth_and_defaults() -> None:
    text = _read("claude-use-mimo-pro-full.sh")

    assert 'if [ -z "${MIMO_API_KEY:-}" ]; then' in text
    assert 'export MIMO_BASE_URL="${MIMO_BASE_URL:-https://token-plan-cn.xiaomimimo.com/v1}"' in text
    assert (
        'export MIMO_ANTHROPIC_BASE_URL="${MIMO_ANTHROPIC_BASE_URL:-https://token-plan-cn.xiaomimimo.com/anthropic}"'
        in text
    )
    assert 'export ANTHROPIC_BASE_URL="$MIMO_ANTHROPIC_BASE_URL"' in text
    assert 'export ANTHROPIC_AUTH_TOKEN="$MIMO_API_KEY"' in text


def test_mimo_pro_model_alias_mapping() -> None:
    text = _read("claude-use-mimo-pro-full.sh")

    assert 'CANONICAL_MIMO_MODEL="mimo-v2.5-pro"' in text
    assert 'NORMALIZED_MIMO_MODEL="$(printf \'%s\' "$RAW_MIMO_MODEL" | tr \'[:upper:]\' \'[:lower:]\')"' in text
    assert 'export ANTHROPIC_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_DEFAULT_OPUS_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_DEFAULT_SONNET_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_DEFAULT_HAIKU_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export ANTHROPIC_SMALL_FAST_MODEL="$CANONICAL_MIMO_MODEL"' in text
    assert 'export CLAUDE_CODE_SUBAGENT_MODEL="$CANONICAL_MIMO_MODEL"' in text


def test_mimo_pro_full_access_flags_match_full_route_policy() -> None:
    mimo_pro = _read("claude-use-mimo-pro-full.sh")
    mimo = _read("claude-use-mimo-full.sh")
    deep_full = _read("claude-use-deepseek-flash-full.sh")

    expected_flags = 'exec claude --permission-mode bypassPermissions --dangerously-skip-permissions "$@"'
    assert expected_flags in mimo_pro
    assert expected_flags in mimo
    assert expected_flags in deep_full


def test_mimo_full_still_uses_v2_5() -> None:
    text = _read("claude-use-mimo-full.sh")
    assert 'CANONICAL_MIMO_MODEL="mimo-v2.5"' in text
    assert "mimo-v2.5-pro" not in text


def test_mimo_pro_uses_anthropic_endpoint_not_openai(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace_file = tmp_path / "trace.txt"
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf 'BASE=%s\\n' \"${{ANTHROPIC_BASE_URL:-}}\" > \"{trace_file}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env.pop("MIMO_MODEL", None)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_BASE_URL"] = "https://token-plan-cn.xiaomimimo.com/v1"

    script = REPO_ROOT / "claude-use-mimo-pro-full.sh"
    subprocess.run(
        [str(script), "-p", "OK"],
        check=True,
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    trace = trace_file.read_text(encoding="utf-8")
    assert "BASE=https://token-plan-cn.xiaomimimo.com/anthropic" in trace
    assert "BASE=https://token-plan-cn.xiaomimimo.com/v1" not in trace


def test_mimo_pro_route_invocation_propagates_auth_and_flags(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace_file = tmp_path / "trace.txt"
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"{{ printf 'ARGS=%s\\n' \"$*\"; printf 'BASE=%s\\n' \"${{ANTHROPIC_BASE_URL:-}}\"; "
                f"printf 'TOKEN=%s\\n' \"${{ANTHROPIC_AUTH_TOKEN:-}}\"; printf 'MODEL=%s\\n' "
                f"\"${{ANTHROPIC_MODEL:-}}\"; }} > \"{trace_file}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env.pop("MIMO_MODEL", None)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_BASE_URL"] = "https://token-plan-cn.xiaomimimo.com/v1"
    env["MIMO_ANTHROPIC_BASE_URL"] = "https://token-plan-cn.xiaomimimo.com/anthropic"

    script = REPO_ROOT / "claude-use-mimo-pro-full.sh"
    subprocess.run(
        [str(script), "-p", "OK"],
        check=True,
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    trace = trace_file.read_text(encoding="utf-8")
    assert "ARGS=--permission-mode bypassPermissions --dangerously-skip-permissions -p OK" in trace
    assert "BASE=https://token-plan-cn.xiaomimimo.com/anthropic" in trace
    assert "TOKEN=mimo_test_key" in trace
    assert "MODEL=mimo-v2.5-pro" in trace


def test_mimo_pro_model_normalization_accepts_title_case(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace_file = tmp_path / "trace.txt"
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf 'MODEL=%s\\n' \"${{ANTHROPIC_MODEL:-}}\" > \"{trace_file}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_MODEL"] = "MiMo-V2.5-Pro"

    script = REPO_ROOT / "claude-use-mimo-pro-full.sh"
    subprocess.run(
        [str(script), "-p", "OK"],
        check=True,
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    trace = trace_file.read_text(encoding="utf-8")
    assert "MODEL=mimo-v2.5-pro" in trace


def test_mimo_pro_rejects_unsupported_model(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_claude = bin_dir / "claude"
    fake_claude.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    fake_claude.chmod(0o755)

    env = os.environ.copy()
    env.pop("MIMO_MODEL", None)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["MIMO_API_KEY"] = "mimo_test_key"
    env["MIMO_MODEL"] = "mimo-v3.0"

    script = REPO_ROOT / "claude-use-mimo-pro-full.sh"
    result = subprocess.run(
        [str(script), "-p", "OK"],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unsupported MIMO_MODEL" in result.stderr or "unsupported MIMO_MODEL" in result.stdout
