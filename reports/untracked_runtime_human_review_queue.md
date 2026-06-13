# Untracked Runtime Human Review Queue

**Files requiring human review:** 2

### core/live_runner.py
- **Reason:** Orchestration gateway: delegates to execution_engine, has run_testnet_order_smoke with order params; safe only if engine is noop
- **Recommendation:** Queue for human review before any integration

### scripts/run_remediation_shadow_only_loop.py
- **Reason:** Executes arbitrary shell commands via subprocess.run(shell=True), command injection surface
- **Recommendation:** Queue for human review before any integration
