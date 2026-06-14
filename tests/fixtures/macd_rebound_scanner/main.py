"""MACD rebound scanner entry point (fixture)."""
import argparse
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
if __name__ == "__main__":
    main()
