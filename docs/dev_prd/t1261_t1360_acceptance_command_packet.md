# T1261-T1360 Acceptance Command Packet

## Pytest Commands by Test Group

### Governance Model Tests

```bash
python3 -m pytest tests/unit/test_frozen_backlog_review_model.py -v
python3 -m pytest tests/unit/test_medium_operational_model.py -v
python3 -m pytest tests/unit/test_verification_script_model.py -v
python3 -m pytest tests/unit/test_human_approval_model.py -v
```

### Frozen Backlog Tests

```bash
python3 -m pytest tests/unit/test_frozen_backlog_review_packet.py -v
```

### Medium Operational Tests

```bash
python3 -m pytest tests/unit/test_medium_operational_packet.py -v
```

### Human Approval Tests

```bash
python3 -m pytest tests/unit/test_human_approval_evidence_packet.py -v
```

### Full Acceptance Suite

```bash
python3 -m pytest tests/unit/ -v -k "t1261_t1360"
```

## Import Verification Commands

```bash
python3 -c "from models.frozen_backlog_review_packet import FrozenBacklogReviewPacket"
python3 -c "from models.medium_operational_packet import MediumOperationalPacket"
python3 -c "from models.verification_script_packet import VerificationScriptPacket"
python3 -c "from models.human_approval_evidence_packet import HumanApprovalEvidencePacket"
python3 -c "from models.governance_summary_packet import GovernanceSummaryPacket"
python3 -c "from models.acceptance_command_packet import AcceptanceCommandPacket"
python3 -c "from models.safety_boundary_packet import SafetyBoundaryPacket"
python3 -c "from models.next_wave_recommendation import NextWaveRecommendation"
python3 -c "from models.final_closeout_report import FinalCloseoutReport"
```

## Expected Results

- All pytest runs: PASSED
- All import verifications: no ImportError
