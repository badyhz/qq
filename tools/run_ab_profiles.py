import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("baseline", "aggressive")


def main() -> int:
    max_loops = os.environ.get("QQ_MAX_LOOPS", "300")
    loop_interval = os.environ.get("QQ_LOOP_INTERVAL_SECONDS", "0.05")
    heartbeat = os.environ.get("QQ_HEARTBEAT_INTERVAL_SECONDS", "30")

    print("A/B profile runner")
    print(f"project={ROOT}")
    print(f"max_loops={max_loops} loop_interval={loop_interval} heartbeat={heartbeat}")

    for profile in PROFILES:
        env = os.environ.copy()
        env["QQ_STRATEGY_PROFILE"] = profile
        env["QQ_MAX_LOOPS"] = max_loops
        env["QQ_LOOP_INTERVAL_SECONDS"] = loop_interval
        env["QQ_HEARTBEAT_INTERVAL_SECONDS"] = heartbeat
        print(f"\n=== Running profile: {profile} ===")
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=ROOT,
            env=env,
            check=False,
        )
        print(f"profile={profile} exit_code={result.returncode}")
        if result.returncode != 0:
            return result.returncode

    print("\nDone. Review generated files such as trades_baseline.csv and trades_aggressive.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
