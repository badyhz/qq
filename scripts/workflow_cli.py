#!/usr/bin/env python3
"""Workflow CLI — runtime integration for workflow templates.

Supports:
  --workflow NAME  Load and run a workflow template via WorkflowRunner
  --mode MODE      Standalone mode demo (queue/dag/closeout)

No real agent execution — simulation only.
"""
from __future__ import annotations

import argparse
import os
import sys

from core.execution_guards import assert_dry_run_required, normalize_execution_mode
from core.agent_factory import AgentFactory, ExecutionMode, Task, TaskStatus
from core.workflow_loader import load_workflow, normalize_workflow_name
from core.workflow_runner import WorkflowRunner


MOCK_TASKS = {
    "queue": [
        Task(id="T001", deps=[], result="batch1 inject"),
        Task(id="T002", deps=["T001"], result="batch1 test"),
        Task(id="T003", deps=["T002"], result="batch1 docs sync"),
        Task(id="T004", deps=["T003"], result="batch2 inject"),
        Task(id="T005", deps=["T004"], result="batch2 test"),
    ],
    "dag": [
        Task(id="T676", deps=[], result="batch7 inject"),
        Task(id="T677", deps=[], result="docs preflight"),
        Task(id="T678", deps=[], result="milestone analysis"),
        Task(id="T679", deps=[], result="batch8 audit"),
        Task(id="T680", deps=[], result="tracker update"),
        Task(id="T681", deps=["T676"], result="post-batch7 docs sync"),
        Task(id="T682", deps=["T679"], result="batch8 inject"),
    ],
    "closeout": [
        Task(id="verify_clean_tree", deps=[]),
        Task(id="classify_dirty", deps=["verify_clean_tree"]),
        Task(id="check_frozen", deps=["classify_dirty"]),
        Task(id="stage", deps=["check_frozen"]),
        Task(id="commit", deps=["stage"]),
        Task(id="tag", deps=["commit"]),
        Task(id="verify", deps=["tag"]),
    ],
}


def print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_plan(plan) -> None:
    print(f"Mode: {plan.mode.value}")
    print(f"Waves: {len(plan.waves)}")
    print(f"Ready: {plan.ready}")
    print(f"Blocked: {plan.blocked}")
    print()

    for i, wave in enumerate(plan.waves, 1):
        print(f"  Wave {i}: {wave}")
    print()


def simulate_execution(factory: AgentFactory, plan) -> None:
    print("--- Simulation ---\n")

    for i, wave in enumerate(plan.waves, 1):
        print(f"Wave {i}:")
        for task_id in wave:
            task = factory.tasks[task_id]
            print(f"  [{task_id}] {task.result or 'executing...'} -> PASS")
            factory.execute_task(task_id, TaskStatus.PASS, result=f"{task_id} done")
        print()

    summary = factory.state_summary()
    print(f"Completed: {summary['completed']}/{summary['total']}")
    print(f"Status: {summary['status_counts']}")


def run_workflow_by_name(name: str) -> None:
    """Load a workflow template by name and run it through WorkflowRunner."""
    normalized = normalize_workflow_name(name)
    print_header(f"WORKFLOW: {normalized}")

    # Load template
    template = load_workflow(name)
    print(f"Template: {template.get('name', normalized)}")
    print(f"Description: {template.get('description', 'N/A')}")
    print()

    # Build runner and execute
    runner = WorkflowRunner(template["name"])
    runner.build_from_template()

    plan = runner.plan()
    print(f"Mode: {plan['mode']}")
    print(f"Tasks: {plan['total_tasks']}")
    print(f"Waves: {len(plan['waves'])}")
    print(f"Ready: {plan['ready']}")
    print(f"Blocked: {plan['blocked']}")
    print()

    for i, wave in enumerate(plan["waves"], 1):
        print(f"  Wave {i}: {wave}")
    print()

    print("--- Simulation ---\n")
    execution = runner.simulate_execution()
    for entry in execution:
        print(f"  [{entry['task']}] PASS ({entry['completed_count']} done)")
    print()

    summary = runner.summary()
    print(f"Completed: {summary['tasks_executed']}/{summary['tasks_total']}")
    print(f"Status: {summary['state_summary']['counts']}")


def mode_queue() -> None:
    print_header("QUEUE MODE — Sequential Batch Execution")

    factory = AgentFactory(mode=ExecutionMode.QUEUE)
    for task in MOCK_TASKS["queue"]:
        factory.register(task)

    plan = factory.plan()
    print_plan(plan)
    simulate_execution(factory, plan)

    print("\n--- Queue Rules ---")
    print("  - One task per wave")
    print("  - Sequential dependency chain")
    print("  - Each step validates before next")


def mode_dag() -> None:
    print_header("DAG MODE — Parallel Independent Tasks")

    factory = AgentFactory(mode=ExecutionMode.DAG)
    for task in MOCK_TASKS["dag"]:
        factory.register(task)

    plan = factory.plan()
    print_plan(plan)
    simulate_execution(factory, plan)

    print("\n--- DAG Rules ---")
    print("  - Maximize parallelism per wave")
    print("  - Independent tasks run together")
    print("  - Dependent tasks wait for deps")


def mode_closeout() -> None:
    print_header("CLOSEOUT MODE — Phase Closure Verification")

    factory = AgentFactory(mode=ExecutionMode.CLOSEOUT)
    for task in MOCK_TASKS["closeout"]:
        factory.register(task)

    plan = factory.plan()
    print_plan(plan)
    simulate_execution(factory, plan)

    print("\n--- Closeout Rules ---")
    print("  - Sequential verification steps")
    print("  - Each step must pass before next")
    print("  - Final verify confirms integrity")


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser(description="Workflow CLI — runtime integration")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--workflow",
        help="Workflow template name to load and run",
    )
    group.add_argument(
        "--mode",
        choices=["queue", "dag", "closeout"],
        help="Standalone mode to demonstrate",
    )
    args = parser.parse_args()

    if args.workflow:
        run_workflow_by_name(args.workflow)
    elif args.mode == "queue":
        mode_queue()
    elif args.mode == "dag":
        mode_dag()
    elif args.mode == "closeout":
        mode_closeout()


if __name__ == "__main__":
    main()
