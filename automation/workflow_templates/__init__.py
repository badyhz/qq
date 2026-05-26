"""Workflow Templates — reusable engineering patterns."""
from automation.workflow_templates.safe_readonly_audit import SAFE_READONLY_AUDIT
from automation.workflow_templates.guard_injection_batch import GUARD_INJECTION_BATCH
from automation.workflow_templates.docs_sync_wave import DOCS_SYNC_WAVE
from automation.workflow_templates.engineering_closeout import ENGINEERING_CLOSEOUT
from automation.workflow_templates.signal_scan_pipeline import SIGNAL_SCAN_PIPELINE
from automation.workflow_templates.execution_guard_docs_sync import EXECUTION_GUARD_DOCS_SYNC
from automation.workflow_templates.quant_closeout_pipeline import QUANT_CLOSEOUT_PIPELINE

TEMPLATES = {
    "SAFE_READONLY_AUDIT": SAFE_READONLY_AUDIT,
    "GUARD_INJECTION_BATCH": GUARD_INJECTION_BATCH,
    "DOCS_SYNC_WAVE": DOCS_SYNC_WAVE,
    "ENGINEERING_CLOSEOUT": ENGINEERING_CLOSEOUT,
    "SIGNAL_SCAN_PIPELINE": SIGNAL_SCAN_PIPELINE,
    "EXECUTION_GUARD_DOCS_SYNC": EXECUTION_GUARD_DOCS_SYNC,
    "QUANT_CLOSEOUT_PIPELINE": QUANT_CLOSEOUT_PIPELINE,
}


def get_template(name: str) -> dict:
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template: {name}. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[name]
