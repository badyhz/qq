# Offline Research Stack FAQ

## General

### Q: What is the offline research stack?
A: A complete offline-only quantitative research operating system for multi-strategy backtesting, quality gating, artifact browsing, comparison analytics, and human review workflows.

### Q: Is it safe to run?
A: Yes. All components are offline only, advisory only, and require human review. release_hold = HOLD prevents any live/testnet/runtime activation.

### Q: Can I use it for live trading?
A: No. The offline research stack is advisory only. No component authorizes live trading.

### Q: What does release_hold = HOLD mean?
A: It is the master safety control. While HOLD, no live trading, testnet submission, runtime integration, or planner integration can occur.

## Pipeline

### Q: How do I run the full pipeline?
A: See `docs/runbooks/run_full_offline_research_stack.md` for the complete sequence.

### Q: How long does the pipeline take?
A: Depends on search_budget and chunk_size. Budget=120 takes ~5-10 minutes. Budget=500 takes ~30-60 minutes.

### Q: Can I run stages independently?
A: Yes. Each stage has its own runbook in `docs/runbooks/`.

### Q: What if a stage fails?
A: Check the error output, see the relevant recovery doc in `docs/recovery/`, and re-run the stage.

## Experiments

### Q: How many experiments are available?
A: 20 curated experiments in the experiment catalog.

### Q: Can I add new experiments?
A: Yes. Follow `docs/checklists/new_experiment_intake_checklist.md`. All experiments must be offline/advisory only.

### Q: What makes an experiment valid?
A: Must have all required fields, all 9 safety flags, release_hold=HOLD, advisory_only=true, human_review_required=true, no forbidden commands or strings.

## Safety

### Q: What are forbidden commands?
A: submit_order, cancel_order, flatten_position, place_order, testnet_submit, live_trading, runtime_start, planner_run, exchange_connect, binance_client.

### Q: What are forbidden imports?
A: requests, httpx, aiohttp, urllib, websocket, binance, ccxt, and any live/testnet/runtime/planner modules.

### Q: What if I accidentally stage an untracked file?
A: `git reset HEAD <file>` to unstage. See `docs/recovery/bad_commit_recovery.md`.

### Q: Can I change release_hold?
A: Only with explicit human approval. Never change it automatically.

## Testing

### Q: How do I run tests?
A: `PYTHONPATH=. .venv/bin/pytest -q`

### Q: What if tests fail?
A: See `docs/recovery/failed_full_suite_recovery.md` and `docs/operator_manuals/offline_research_stack_troubleshooting.md`.

### Q: How do I test specific components?
A: Use targeted pytest with the test file pattern. See `docs/operator_manuals/offline_research_stack_command_reference.md`.

## Output

### Q: Where are outputs stored?
A: In `/tmp/` subdirectories. Configurable via --output-dir.

### Q: Are outputs permanent?
A: No. `/tmp/` is ephemeral. Save important outputs to persistent storage.

### Q: Can I compare outputs from different runs?
A: Yes. Use `scripts/build_research_comparison_analytics.py` with --bundle flags.
