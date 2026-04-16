from pathlib import Path

import pandas as pd
from tabulate import tabulate


class TradeDashboard:
    def __init__(self, file_path: str = "trades.csv"):
        self.file_path = Path(file_path)
        self.df = pd.DataFrame()
        if self.file_path.exists():
            self.df = pd.read_csv(self.file_path)

    def run(self) -> None:
        if self.df.empty:
            print("No trade data yet. Run the bot until trades.csv has records.")
            return

        df = self.df.copy()
        pnl = df["pnl"].fillna(0.0)
        wins = df[pnl > 0]
        losses = df[pnl <= 0]

        total_trades = len(df)
        win_rate = (len(wins) / total_trades) * 100 if total_trades else 0.0
        avg_win = wins["pnl"].mean() if not wins.empty else 0.0
        avg_loss = abs(losses["pnl"].mean()) if not losses.empty else 0.0
        rr_ratio = (avg_win / avg_loss) if avg_loss else float("inf")
        expectancy = ((win_rate / 100.0) * avg_win) - ((1 - win_rate / 100.0) * avg_loss)
        gross_profit = wins["pnl"].sum() if not wins.empty else 0.0
        gross_loss = abs(losses["pnl"].sum()) if not losses.empty else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss else float("inf")

        cumulative = pnl.cumsum()
        peak = cumulative.cummax()
        drawdown = peak - cumulative
        max_drawdown = drawdown.max() if not drawdown.empty else 0.0

        loss_flags = (pnl <= 0).astype(int)
        groups = (loss_flags != loss_flags.shift()).cumsum()
        max_loss_streak = loss_flags.groupby(groups).cumsum().max() if not loss_flags.empty else 0

        summary = [
            ["Total Trades", total_trades],
            ["Win Rate", f"{win_rate:.2f}%"],
            ["R:R", f"{rr_ratio:.2f}"],
            ["Expectancy", f"{expectancy:.4f} USDT"],
            ["Profit Factor", f"{profit_factor:.2f}"],
            ["Net PnL", f"{pnl.sum():.4f} USDT"],
            ["Max Drawdown", f"{max_drawdown:.4f} USDT"],
            ["Max Loss Streak", int(max_loss_streak)],
        ]

        print("\n=== Global Performance ===")
        print(tabulate(summary, headers=["Metric", "Value"], tablefmt="grid"))

        if "score" in df.columns:
            score_view = (
                df.groupby("score", dropna=False)
                .agg(
                    trades=("pnl", "count"),
                    win_rate=("pnl", lambda s: (s > 0).mean() * 100),
                    pnl_sum=("pnl", "sum"),
                    pnl_mean=("pnl", "mean"),
                )
                .reset_index()
                .sort_values("score")
            )
            score_view["win_rate"] = score_view["win_rate"].map(lambda x: f"{x:.2f}%")
            score_view["pnl_sum"] = score_view["pnl_sum"].map(lambda x: f"{x:.4f}")
            score_view["pnl_mean"] = score_view["pnl_mean"].map(lambda x: f"{x:.4f}")
            print("\n=== Score Breakdown ===")
            print(tabulate(score_view, headers="keys", tablefmt="pretty", showindex=False))

        if "symbol" in df.columns:
            symbol_view = (
                df.groupby("symbol", dropna=False)
                .agg(
                    trades=("pnl", "count"),
                    pnl_sum=("pnl", "sum"),
                    win_rate=("pnl", lambda s: (s > 0).mean() * 100),
                )
                .reset_index()
                .sort_values("pnl_sum", ascending=False)
            )
            symbol_view["pnl_sum"] = symbol_view["pnl_sum"].map(lambda x: f"{x:.4f}")
            symbol_view["win_rate"] = symbol_view["win_rate"].map(lambda x: f"{x:.2f}%")
            print("\n=== Symbol Breakdown ===")
            print(tabulate(symbol_view, headers="keys", tablefmt="pretty", showindex=False))

        if "strategy_profile" in df.columns:
            profile_view = (
                df.groupby("strategy_profile", dropna=False)
                .agg(
                    trades=("pnl", "count"),
                    pnl_sum=("pnl", "sum"),
                    win_rate=("pnl", lambda s: (s > 0).mean() * 100),
                    avg_rr=("reward_risk_ratio", "mean"),
                    avg_mae_pct=("mae_pct", "mean"),
                    avg_mfe_pct=("mfe_pct", "mean"),
                )
                .reset_index()
                .sort_values("pnl_sum", ascending=False)
            )
            profile_view["pnl_sum"] = profile_view["pnl_sum"].map(lambda x: f"{x:.4f}")
            profile_view["win_rate"] = profile_view["win_rate"].map(lambda x: f"{x:.2f}%")
            profile_view["avg_rr"] = profile_view["avg_rr"].map(lambda x: f"{x:.2f}")
            profile_view["avg_mae_pct"] = profile_view["avg_mae_pct"].map(lambda x: f"{x * 100:.2f}%")
            profile_view["avg_mfe_pct"] = profile_view["avg_mfe_pct"].map(lambda x: f"{x * 100:.2f}%")
            print("\n=== Strategy Profiles ===")
            print(tabulate(profile_view, headers="keys", tablefmt="pretty", showindex=False))

        exit_view = (
            df.groupby("exit_reason", dropna=False)
            .agg(trades=("pnl", "count"), pnl_sum=("pnl", "sum"))
            .reset_index()
            .sort_values("trades", ascending=False)
        )
        exit_view["pnl_sum"] = exit_view["pnl_sum"].map(lambda x: f"{x:.4f}")
        print("\n=== Exit Reasons ===")
        print(tabulate(exit_view, headers="keys", tablefmt="pretty", showindex=False))

        print("\n=== Diagnostic ===")
        if total_trades < 20:
            print("Sample size is still small. Keep running dry-run to collect more trades.")
        elif expectancy > 0 and profit_factor >= 1.5:
            print("System currently shows positive edge in the collected sample.")
        elif expectancy > 0:
            print("System is slightly profitable, but the edge is still weak.")
        else:
            print("System is negative in the current sample. Tighten filters before live use.")


if __name__ == "__main__":
    TradeDashboard().run()
