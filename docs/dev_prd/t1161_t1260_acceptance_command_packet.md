# T1161-T1260 Acceptance Command Packet

## Pytest Commands by Test Group

### Governance Model Tests

```bash
python3 -m pytest tests/unit/test_governance_summary_packet.py -v
python3 -m pytest tests/unit/test_governance_acceptance_command.py -v
python3 -m pytest tests/unit/test_governance_safety_boundary.py -v
```

### Freeze Inventory Tests

```bash
python3 -m pytest tests/unit/test_untracked_freeze_packet.py -v
python3 -m pytest tests/unit/test_medium_risk_review_packet.py -v
```

### Release Gate Tests

```bash
python3 -m pytest tests/unit/test_no_submit_release_gate.py -v
```

### Full Acceptance Suite

```bash
python3 -m pytest tests/unit/ -v -k "t1161_t1260"
```

## Import Verification Commands

```bash
python3 -c "from models.governance_summary_packet import GovernanceSummaryPacket"
python3 -c "from models.acceptance_command_packet import AcceptanceCommandPacket"
python3 -c "from models.safety_boundary_packet import SafetyBoundaryPacket"
python3 -c "from models.untracked_freeze_packet import UntrackedFreezePacket"
python3 -c "from models.medium_risk_review_packet import MediumRiskReviewPacket"
python3 -c "from models.no_submit_release_gate_packet import NoSubmitReleaseGatePacket"
python3 -c "from models.next_wave_recommendation import NextWaveRecommendation"
python3 -c "from models.final_closeout_report import FinalCloseoutReport"
```

## Expected Results

- All pytest runs: PASSED
- All import verifications: no ImportError
