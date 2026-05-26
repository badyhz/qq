import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.execution_guards import assert_dry_run_required, normalize_execution_mode
from dashboard import print_trade_summary


def main() -> None:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("trades.csv")
    print_trade_summary(csv_path)


if __name__ == "__main__":
    main()
