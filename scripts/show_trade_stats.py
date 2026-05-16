import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard import print_trade_summary


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("trades.csv")
    print_trade_summary(csv_path)


if __name__ == "__main__":
    main()
