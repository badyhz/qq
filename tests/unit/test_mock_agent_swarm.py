"""Tests for MockAgentSwarm."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.mock_agent_swarm import MockAgentSwarm, SwarmAgent, MockAdapter


def test_swarm_creation_5_agents():
    swarm = MockAgentSwarm(size=5)
    assert len(swarm.list_agents()) == 5
    assert all(a.status == "idle" for a in swarm.list_agents())


def test_swarm_creation_10_agents():
    swarm = MockAgentSwarm(size=10, adapter_type="claude")
    agents = swarm.list_agents()
    assert len(agents) == 10
    assert all(a.adapter_type == "claude" for a in agents)


def test_all_idle_initially():
    swarm = MockAgentSwarm(size=8)
    assert len(swarm.available_agents()) == 8


def test_dispatch_assigns_to_agent():
    swarm = MockAgentSwarm(size=3)
    agent = swarm.dispatch("T1", prompt="do something")
    assert agent is not None
    assert agent.status == "busy"
    assert agent.current_task == "T1"
    assert len(swarm.available_agents()) == 2


def test_complete_releases_agent():
    swarm = MockAgentSwarm(size=3)
    agent = swarm.dispatch("T1")
    swarm.complete(agent.agent_id, "T1")
    assert agent.status == "idle"
    assert agent.current_task is None
    assert agent.tasks_completed == 1
    assert len(swarm.available_agents()) == 3


def test_dispatch_full_swarm_returns_none():
    swarm = MockAgentSwarm(size=2)
    swarm.dispatch("T1")
    swarm.dispatch("T2")
    result = swarm.dispatch("T3")
    assert result is None


def test_scale_up():
    swarm = MockAgentSwarm(size=3)
    swarm.scale(6)
    assert len(swarm.list_agents()) == 6


def test_scale_down():
    swarm = MockAgentSwarm(size=5)
    swarm.scale(2)
    assert len(swarm.list_agents()) == 2


def test_autopilot_completes_all_tasks():
    swarm = MockAgentSwarm(size=3)
    tasks = [{"id": f"T{i}"} for i in range(5)]
    log = swarm.autopilot(tasks)
    assert len(log) == 5
    assert all(e["status"] == "completed" for e in log)
    # All agents should be idle after autopilot
    assert all(a.status == "idle" for a in swarm.list_agents())


def test_status_report():
    swarm = MockAgentSwarm(size=4)
    s = swarm.status()
    assert s["total_agents"] == 4
    assert s["idle"] == 4
    assert s["busy"] == 0
    assert s["total_tasks_completed"] == 0

    swarm.dispatch("T1")
    s2 = swarm.status()
    assert s2["busy"] == 1
    assert s2["idle"] == 3
