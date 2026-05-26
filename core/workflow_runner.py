"""Workflow Runner — connects agent_factory, governance_state, and workflow_templates.

Simulation only. No real agent execution.
"""
from __future__ import annotations

from core.agent_factory import AgentFactory, ExecutionMode, Task, TaskStatus
from core.governance_state import GovernanceStateMachine, State
from automation.workflow_templates import TEMPLATES, get_template

# Template parallel_policy.mode -> ExecutionMode enum
_MODE_MAP: dict[str, ExecutionMode] = {
    "DAG": ExecutionMode.DAG,
    "QUEUE": ExecutionMode.QUEUE,
    "CLOSEOUT": ExecutionMode.CLOSEOUT,
}


class WorkflowRunner:
    def __init__(self, template_name: str):
        self.template = get_template(template_name)
        self.factory = AgentFactory(mode=self._resolve_mode())
        self.state_machine = GovernanceStateMachine()
        self.tasks_built = False

    def _resolve_mode(self) -> ExecutionMode:
        mode_str = self.template["parallel_policy"]["mode"]
        return _MODE_MAP[mode_str]

    def build_from_tasks(self, task_specs: list[dict]) -> None:
        """Build workflow from task specifications."""
        for spec in task_specs:
            task_id = spec["id"]
            deps = spec.get("deps", [])

            # Register in both systems
            self.factory.register(Task(id=task_id, deps=deps))
            self.state_machine.register(task_id, deps)

        self.tasks_built = True

    def build_from_template(self) -> None:
        """Build workflow from template defaults (mock tasks)."""
        mock_tasks = self._generate_mock_tasks()
        self.build_from_tasks(mock_tasks)

    def _generate_mock_tasks(self) -> list[dict]:
        """Generate mock tasks based on template type."""
        name = self.template["name"]
        if name == "SAFE_READONLY_AUDIT":
            return [
                {"id": "scan_candidates", "deps": []},
                {"id": "check_frozen", "deps": ["scan_candidates"]},
                {"id": "classify_imports", "deps": ["scan_candidates"]},
                {"id": "risk_assessment", "deps": ["classify_imports"]},
                {"id": "batch_recommendation", "deps": ["risk_assessment", "check_frozen"]},
            ]
        elif name == "GUARD_INJECTION_BATCH":
            return [
                {"id": "inject_scripts", "deps": []},
                {"id": "create_tests", "deps": ["inject_scripts"]},
                {"id": "run_targeted_tests", "deps": ["create_tests"]},
                {"id": "run_regression", "deps": ["run_targeted_tests"]},
                {"id": "sync_docs", "deps": ["run_regression"]},
            ]
        elif name == "DOCS_SYNC_WAVE":
            return [
                {"id": "audit_staleness", "deps": []},
                {"id": "update_matrix", "deps": ["audit_staleness"]},
                {"id": "update_dashboard", "deps": ["audit_staleness"]},
                {"id": "update_metrics", "deps": ["audit_staleness"]},
                {"id": "verify_consistency", "deps": ["update_matrix", "update_dashboard", "update_metrics"]},
            ]
        elif name == "ENGINEERING_CLOSEOUT":
            return [
                {"id": "verify_clean_tree", "deps": []},
                {"id": "classify_dirty", "deps": ["verify_clean_tree"]},
                {"id": "check_frozen", "deps": ["classify_dirty"]},
                {"id": "stage", "deps": ["check_frozen"]},
                {"id": "commit", "deps": ["stage"]},
                {"id": "tag", "deps": ["commit"]},
                {"id": "verify", "deps": ["tag"]},
            ]
        return []

    def plan(self) -> dict:
        """Compute execution plan."""
        if not self.tasks_built:
            raise RuntimeError("No tasks built. Call build_from_tasks() or build_from_template() first.")

        plan = self.factory.plan()
        ready = self.state_machine.resolve_ready()

        return {
            "template": self.template["name"],
            "mode": plan.mode.value,
            "waves": plan.waves,
            "ready": ready,
            "blocked": plan.blocked,
            "total_tasks": len(self.factory.tasks),
            "validation_rules": self.template["validation_checklist"],
            "stop_conditions": self.template["stop_conditions"],
        }

    def simulate_execution(self) -> list[dict]:
        """Simulate full execution progression."""
        results = []
        completed = set()

        while True:
            ready = [tid for tid, t in self.factory.tasks.items()
                     if t.is_ready(completed)]
            if not ready:
                break

            for task_id in ready:
                task = self.factory.tasks[task_id]
                # Simulate: all tasks PASS
                self.factory.execute_task(task_id, TaskStatus.PASS, result=f"{task_id} done")
                self.state_machine.transition(task_id, State.READY, "deps met")
                self.state_machine.transition(task_id, State.RUNNING, "started")
                self.state_machine.transition(task_id, State.PASS, "completed")
                completed.add(task_id)

                results.append({
                    "task": task_id,
                    "status": "PASS",
                    "completed_count": len(completed),
                })

        return results

    def summary(self) -> dict:
        """Full workflow summary."""
        plan = self.plan()
        execution = self.simulate_execution()

        return {
            "template": self.template["name"],
            "mode": plan["mode"],
            "tasks_total": plan["total_tasks"],
            "tasks_executed": len(execution),
            "execution_log": execution,
            "state_summary": self.state_machine.state_summary(),
            "validation_rules": plan["validation_rules"],
        }
