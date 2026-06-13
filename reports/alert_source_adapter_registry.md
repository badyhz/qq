# Alert Source Adapter Registry

**Total adapters:** 5

## By Priority

- **HIGH:** earnings, binance_futures
- **MEDIUM:** stock_price, macd_rebound
- **LOW:** system_heartbeat

## Adapter Details

### earnings

- **Type:** event_driven
- **Data source:** local_schedule
- **Network required:** False
- **Priority:** HIGH
- **Dedup window:** 60 min
- **Description:** Earnings calendar event alerts from local schedule data
- **Integrated:** True
- **Dry-run compatible:** True
- **Governance tracked:** True

### stock_price

- **Type:** threshold_monitor
- **Data source:** public_market_data
- **Network required:** True
- **Priority:** MEDIUM
- **Dedup window:** 5 min
- **Description:** Stock price threshold breach alerts from public market data
- **Integrated:** True
- **Dry-run compatible:** True
- **Governance tracked:** True

### macd_rebound

- **Type:** signal_generator
- **Data source:** computed_indicators
- **Network required:** False
- **Priority:** MEDIUM
- **Dedup window:** 15 min
- **Description:** MACD rebound signal alerts from computed technical indicators
- **Integrated:** True
- **Dry-run compatible:** True
- **Governance tracked:** True

### binance_futures

- **Type:** market_scanner
- **Data source:** public_binance_api
- **Network required:** True
- **Priority:** HIGH
- **Dedup window:** 5 min
- **Description:** Binance futures market scanner alerts from public API data
- **Integrated:** True
- **Dry-run compatible:** True
- **Governance tracked:** True

### system_heartbeat

- **Type:** health_monitor
- **Data source:** internal_metrics
- **Network required:** False
- **Priority:** LOW
- **Dedup window:** 1 min
- **Description:** System heartbeat and health monitoring alerts
- **Integrated:** True
- **Dry-run compatible:** True
- **Governance tracked:** True
