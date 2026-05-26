#!/usr/bin/env python3
"""Workflow Status — render workflow runtime state.

Shows task states, dependencies, worker allocation, completion %.
"""
from __future__ import annotations

import argparse
import os
import sys

from core.execution_guards import assert_dry_run_required, normalize_execution_mode
from core.agent_factory import ExecutionMode


# Mock workflow data for demonstration
DEMO_WORKFLOWS = {
    "guard_batch": {
        "tasks": [
            {"id": "inject_scripts", "deps": []},
            {"id": "create_tests", "deps": ["inject_scripts"]},
            {"id": "run_targeted_tests", "deps": ["create_tests"]},
            {"id": "run_regression", "deps": ["run_targeted_tests"]},
            {"id": "sync_docs", "deps": ["run_regression"]},
        ],
        "completed": ["inject_scripts", "create_tests"],
        "running": ["run_targeted_tests"],
    },
    "docs_sync": {
        "tasks": [
            {"id": "audit_staleness", "deps": []},
            {"id": "update_matrix", "deps": ["audit_staleness"]},
            {"id": "update_dashboard", "deps": ["audit_staleness"]},
            {"id": "update_metrics", "deps": ["audit_staleness"]},
            {"id": "verify_consistency", "deps": ["update_matrix", "update_dashboard", "update_metrics"]},
        ],
        "completed": ["audit_staleness", "update_matrix", "update_dashboard"],
        "running": ["update_metrics"],
    },
    "closeout": {
        "tasks": [
            {"id": "verify_clean_tree", "deps": []},
            {"id": "classify_dirty", "deps": ["verify_clean_tree"]},
            {"id": "check_frozen", "deps": ["classify_dirty"]},
            {"id": "stage", "deps": ["check_frozen"]},
            {"id": "commit", "deps": ["stage"]},
            {"id": "tag", "deps": ["commit"]},
            {"id": "verify", "deps": ["tag"]},
        ],
        "completed": ["verify_clean_tree", "classify_dirty", "check_frozen"],
        "running": ["stage"],
    },
}


def render_state(state: str) -> str:
    icons = {
        "COMPLETED": "[PASS]",
        "RUNNING":  "[....]",
        "READY":    "[WAIT]",
        "BLOCKED":  "[    ]",
    }
    return icons.get(state, "[????]")


def render_workflow(name: str, workflow: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  WORKFLOW: {name.upper()}")
    print(f"{'='*60}\n")

    tasks = workflow["tasks"]
    completed = set(workflow["completed"])
    running = set(workflow["running"])

    # Determine states
    task_states = {}
    for task in tasks:
        tid = task["id"]
        if tid in completed:
            task_states[tid] = "COMPLETED"
        elif tid in running:
            task_states[tid] = "RUNNING"
        else:
            # Check if deps are met
            deps_met = all(d in completed for d in task["deps"])
            task_states[tid] = "READY" if deps_met else "BLOCKED"

    # Render task list
    print("  Tasks:")
    for task in tasks:
        tid = task["id"]
        state = task_states[tid]
        deps_str = f" (deps: {', '.join(task['deps'])})" if task["deps"] else ""
        print(f"    {render_state(state)} {tid}{deps_str}")

    # Render dependency graph
    print("\n  Dependency Graph:")
    for task in tasks:
        tid = task["id"]
        if task["deps"]:
            for dep in task["deps"]:
                print(f"    {dep} --> {tid}")
        else:
            print(f"    [ENTRY] --> {tid}")

    # Worker allocation
    print("\n  Worker Allocation:")
    running_tasks = list(running)
    for i, tid in enumerate(running_tasks[:5], 1):
        print(f"    W{i}: {tid} [RUNNING]")
    idle_count = max(0, 5 - len(running_tasks))
    if idle_count > 0:
        print(f"    W{len(running_tasks)+1}-W5: IDLE ({idle_count} slots)")

    # Completion %
    total = len(tasks)
    done = len(completed)
    pct = (done / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * done / total) if total > 0 else 0
    bar = "#" * filled + "." * (bar_len - filled)
    print(f"\n  Progress: [{bar}] {done}/{total} ({pct:.0f}%)")

    # Summary
    ready = sum(1 for s in task_states.values() if s == "READY")
    blocked = sum(1 for s in task_states.values() if s == "BLOCKED")
    print(f"\n  Summary: {done} completed, {len(running)} running, {ready} ready, {blocked} blocked")
    print()


def main():
    raw_mode = os.environ.get("QQ_RUNTIME_MODE")
    if raw_mode is None:
        raise ValueError("QQ_RUNTIME_MODE not set")
    mode = normalize_execution_mode(raw_mode)
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser(description="Workflow Status — runtime visualization")
    parser.add_argument(
        "--workflow",
        choices=list(DEMO_WORKFLOWS.keys()),
        help="Workflow to visualize",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all demo workflows",
    )
    args = parser.parse_args()

    if args.all:
        for name, wf in DEMO_WORKFLOWS.items():
            render_workflow(name, wf)
    elif args.workflow:
        render_workflow(args.workflow, DEMO_WORKFLOWS[args.workflow])
    else:
        print("Specify --workflow NAME or --all")


if __name__ == "__main__":
    main()
