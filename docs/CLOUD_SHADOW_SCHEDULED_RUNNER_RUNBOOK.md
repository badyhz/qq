# Cloud Shadow Scheduled Runner Runbook

## Purpose

This runbook documents the Tencent Cloud scheduled shadow collection runner.
It is only for shadow / paper sample collection.

It is not testnet.
It is not live trading.
It is not automatic trading.
It does not read secrets.
It does not access private endpoints.
It does not place, amend, or cancel orders.

## Paths

- Server project path: `/opt/quant-shadow/qq`
- Wrapper path: `scripts/run_cloud_shadow_collection_once.sh`
- Systemd service path: `/etc/systemd/system/quant-shadow-collection.service`
- Systemd timer path: `/etc/systemd/system/quant-shadow-collection.timer`
- Cloud log path: `/opt/quant-shadow/qq/logs/cloud_shadow`
- Report path: `/opt/quant-shadow/qq/reports/strategies`

## Schedule

- Current cadence: hourly
- Runner type: systemd timer triggering a one-shot service
- Expected flow: lifecycle -> update-only -> sample gate -> operator status

Do not change the cadence without a separate operator decision.

## Check Timer Status

```bash
ssh tx-macd
systemctl status quant-shadow-collection.timer --no-pager -l
systemctl list-timers --all | grep quant-shadow || true
```

Expected healthy state:

- `quant-shadow-collection.timer` is active
- next trigger is scheduled
- previous trigger is recent

## Check Service Logs

```bash
ssh tx-macd
systemctl status quant-shadow-collection.service --no-pager -l
journalctl -u quant-shadow-collection.service --since "24 hours ago" --no-pager | tail -500
```

Expected healthy state:

- one-shot service exits with `status=0/SUCCESS`
- latest run includes `Cloud Shadow Collection End`
- lifecycle, update-only, and sample gate steps report PASS

Note: `systemctl status` can return a non-zero shell exit for an inactive one-shot service even when the displayed service result is `status=0/SUCCESS`. Judge the service by the displayed status and journal contents.

## Check Cloud Logs

```bash
ssh tx-macd
cd /opt/quant-shadow/qq

find logs/cloud_shadow -type f -name "shadow_collection_*.log" -mtime -1 | sort
find logs/cloud_shadow -type f -name "shadow_collection_*.log" -mtime -1 | wc -l
grep -R "Cloud Shadow Collection End" logs/cloud_shadow/*.log | tail -40
grep -R "Traceback\|ERROR\|FAILED\|Exception" logs/cloud_shadow/*.log | tail -100 || true
```

Expected healthy state:

- hourly logs continue to appear
- each completed run has `Cloud Shadow Collection End`
- failure marker grep is empty

## Check Operator Status

```bash
ssh tx-macd
cd /opt/quant-shadow/qq
. .venv/bin/activate
python3 scripts/print_shadow_operator_status.py
```

Expected shadow-only state:

- `sample_status` remains sample-driven
- `testnet_gate_status` remains blocked until enough closed clean samples exist
- `scorecard_status` remains OBSERVE_ONLY until a separate manual review allows a change

## Check Reports

```bash
ssh tx-macd
cd /opt/quant-shadow/qq
find reports -type f | sort | tail -120
```

Daily report files are overwritten during same-day hourly runs. This is expected.
Use `logs/cloud_shadow/shadow_collection_*.log` and `journalctl -u quant-shadow-collection.service` for run history.

## Stop Timer

Use this only for operator-controlled maintenance or incident response.

```bash
ssh tx-macd
sudo systemctl stop quant-shadow-collection.timer
systemctl status quant-shadow-collection.timer --no-pager -l
```

Stopping the timer prevents future scheduled runs. It does not stop a run that has already completed.

## Restore Timer

```bash
ssh tx-macd
sudo systemctl start quant-shadow-collection.timer
systemctl status quant-shadow-collection.timer --no-pager -l
systemctl list-timers --all | grep quant-shadow || true
```

Do not redesign systemd units, add cron, add a daemon, or expose a web console as part of routine recovery.

## Safety Boundaries

Allowed:

- public readonly market data
- shadow lifecycle execution
- paper position updates
- sample gate checks
- local reports and cloud logs

Forbidden without a separate explicit approval:

- reading secrets or `.env`
- using private exchange endpoints
- testnet
- live trading
- order placement
- order cancellation
- account synchronization
- webhook or Feishu real send
- public web console
- nginx or `0.0.0.0` binding
- strategy threshold relaxation
- sample gate or scorecard promotion changes

## Closed Sample Standards

Use `closed_clean_positions` as the main strategy-validation sample counter.

- `0-9`: collect only; do not judge strategy quality
- `10+`: initial review may start, but testnet is still not allowed
- `30+`: human review may discuss whether testnet gate review is appropriate

`closed_clean_positions = 0` can still be operationally healthy. It means the system is collecting open shadow samples but has not produced closed clean samples yet.

## Operator Conclusion

When the timer is active, logs are continuous, failed runs are zero, sample gate is blocked, and scorecards are OBSERVE_ONLY, the correct action is to continue scheduled shadow collection and wait for closed samples.
