"""Integration test: readonly next stage decision pack."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_checkpoint.next_stage_decision_pack import create_pack


def test_pack_ready():
    pack = create_pack()
    assert "READONLY_NEXT_STAGE_DECISION_PACK_READY" in pack.final_verdict


def test_recommended_option_d():
    pack = create_pack()
    assert pack.recommended_next == "OPTION_D_ARCHIVE_CURRENT_CHAIN_AND_WAIT_FOR_HUMAN_APPROVAL"


def test_option_count():
    pack = create_pack()
    assert len(pack.options) == 4


def test_all_options_have_forbidden_actions():
    pack = create_pack()
    for o in pack.options:
        assert len(o.forbidden_actions) >= 3


def test_option_d_requires_human_approval():
    pack = create_pack()
    option_d = [o for o in pack.options if o.option_id.startswith("OPTION_D")][0]
    assert option_d.requires_human_approval is True


def test_no_real_network_in_forbidden():
    pack = create_pack()
    for o in pack.options:
        assert "real_network_call" in o.forbidden_actions
