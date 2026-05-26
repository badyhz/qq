"""SIGNAL_SCAN_PIPELINE template — quant signal scanning and classification."""
SIGNAL_SCAN_PIPELINE = {
    "name": "SIGNAL_SCAN_PIPELINE",
    "description": "Scan market data, generate signals, classify, and produce trade candidates.",
    "mode": "DAG",
    "inputs": {
        "universe": {"type": "list[str]", "required": True, "description": "Symbols to scan"},
        "timeframe": {"type": "str", "required": True, "description": "Candle timeframe (1m, 5m, 1h)"},
    },
    "outputs": {
        "signals": {"type": "list[dict]", "description": "Generated signals"},
        "candidates": {"type": "list[dict]", "description": "Classified trade candidates"},
    },
    "parallel_policy": {
        "mode": "DAG",
        "max_agents": 5,
        "rules": [
            "Independent symbol scans: parallel",
            "Signal classification: parallel per symbol",
            "Aggregation: sequential after all scans complete",
        ],
    },
    "tasks": [
        {"id": "fetch_market_data", "deps": []},
        {"id": "compute_indicators", "deps": ["fetch_market_data"]},
        {"id": "generate_signals", "deps": ["compute_indicators"]},
        {"id": "classify_signals", "deps": ["generate_signals"]},
        {"id": "risk_filter", "deps": ["classify_signals"]},
        {"id": "aggregate_candidates", "deps": ["risk_filter"]},
    ],
    "validation_checklist": [
        "Universe symbols are valid Binance pairs",
        "Timeframe is in allowed set",
        "No frozen files accessed",
        "Indicators computed without external API calls",
        "Signals classified before risk filter",
    ],
    "stop_conditions": [
        "Invalid symbol in universe",
        "Indicator computation failure",
        "All signals filtered out",
    ],
    "anti_patterns": [
        "Skip risk filter",
        "Submit orders from scan results",
        "Access frozen files during scan",
    ],
    "safety_policy": {
        "allowed_categories": ["READONLY", "AUDIT", "SIMULATION"],
        "blocked_categories": ["SUBMIT", "CANCEL", "FLATTEN", "LIVE_EXECUTION"],
    },
}
