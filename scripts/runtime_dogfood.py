"""Runtime Dogfood Runner — exercise WorkflowRuntime against quant templates.

Simulation only. No real trading, no real API calls.
"""
from __future__ import annotations

from core.workflow_runtime import WorkflowRuntime
from automation.workflow_templates import TEMPLATES


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _print_task_graph(template: dict) -> None:
    tasks = template.get("tasks", [])
    print(f"  Task count: {len(tasks)}")
    for t in tasks:
        deps = t.get("deps", [])
        dep_str = f" <- {deps}" if deps else ""
        print(f"    {t['id']}{dep_str}")


def run_template(name: str, max_workers: int = 5) -> dict:
    """Run a single template through WorkflowRuntime and print summary."""
    _print_section(f"RUNNING: {name}")
    template = TEMPLATES[name]

    print(f"\n  Description: {template.get('description', 'N/A')}")
    print(f"  Mode: {template.get('mode', 'DAG')}")
    print("\n  --- Task Graph ---")
    _print_task_graph(template)

    rt = WorkflowRuntime(max_workers=max_workers, mode=template.get("mode", "DAG"))
    load_result = rt.load_workflow(template["tasks"], workflow_id=name)
    print(f"\n  Load: {load_result}")

    if not load_result.get("valid"):
        print(f"  BLOCKED: safety violations: {load_result.get('violations')}")
        return {"template": name, "load_result": load_result, "run_result": None, "status": None}

    run_result = rt.run()

    print(f"\n  --- Execution ---")
    print(f"  Steps: {run_result['steps']}")
    print(f"  Total tasks: {run_result['total_tasks']}")
    print(f"  Completed: {run_result['completed']}")
    print(f"  Is complete: {run_result['is_complete']}")

    print(f"\n  --- Budget ---")
    print(f"  Status: {run_result['budget_status']}")

    print(f"\n  --- Circuit Breaker ---")
    print(f"  State: {run_result['circuit_state']}")

    print(f"\n  --- Observability ---")
    obs = run_result["observability_summary"]
    print(f"  Total events: {obs['total']}")
    print(f"  Event counts: {obs['counts']}")

    full_status = rt.status()
    print(f"\n  --- Full Status ---")
    print(f"  Status counts: {full_status['status_counts']}")
    print(f"  Steps taken: {full_status['steps_taken']}")
    print(f"  Execution log length: {full_status['execution_log_length']}")
    print(f"  Safety violations: {full_status['safety_violations']}")
    print(f"  Budget summary: {full_status['budget']}")
    print(f"  Circuit breaker summary: {full_status['circuit_breaker']}")

    return {
        "template": name,
        "load_result": load_result,
        "run_result": run_result,
        "status": full_status,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  RUNTIME DOGFOOD — Quant Template Runner")
    print("=" * 60)

    results = {}

    for tpl_name in ["SIGNAL_SCAN_PIPELINE", "SAFE_READONLY_AUDIT"]:
        results[tpl_name] = run_template(tpl_name, max_workers=5)

    _print_section("DOGFOOD SUMMARY")
    for name, res in results.items():
        run = res.get("run_result")
        if run:
            print(f"  {name}: {run['completed']}/{run['total_tasks']} tasks, "
                  f"complete={run['is_complete']}, budget={run['budget_status']}, "
                  f"circuit={run['circuit_state']}")
        else:
            print(f"  {name}: FAILED TO LOAD — {res.get('load_result')}")

    print()
