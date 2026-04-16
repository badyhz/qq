import csv
from datetime import datetime
from pathlib import Path


class TradeLogger:
    def __init__(self, config: dict):
        self.config = config
        self.file_path = Path(config.get("paths", {}).get("trades_csv", "trades.csv"))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = [
            "trade_id",
            "symbol",
            "mode",
            "side",
            "strategy_profile",
            "entry_price",
            "exit_price",
            "stop_price",
            "take_profit_price",
            "quantity",
            "notional",
            "gross_pnl",
            "fees_paid",
            "pnl",
            "return_pct",
            "score",
            "zscore",
            "vwap",
            "vwap_dev",
            "atr",
            "volume_ratio",
            "reward_risk_ratio",
            "estimated_loss_at_stop",
            "estimated_gain_at_target",
            "mae_price_distance",
            "mfe_price_distance",
            "mae_pct",
            "mfe_pct",
            "entry_time",
            "exit_time",
            "duration_sec",
            "exit_reason",
            "notes",
        ]
        self._ensure_file()

    def _ensure_file(self) -> None:
        if self.file_path.exists():
            return
        with self.file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
            writer.writeheader()

    def log_trade(self, trade: dict) -> None:
        row = {key: self._normalize(trade.get(key)) for key in self.fieldnames}
        with self.file_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
            writer.writerow(row)

    def _normalize(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, float):
            return round(value, 8)
        return value
