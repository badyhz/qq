# Runtime Governance Read-Only Approval Form (T844)

## Purpose

Static manual approval form data for the runtime governance read-only layer.
No approval execution logic -- pure data structure only.

## Files

- `core/runtime_governance_readonly_approval_form.py` -- dataclass + 3 pure functions
- `tests/unit/test_runtime_governance_readonly_approval_form.py` -- 6 tests

## Dataclass

`RuntimeGovernanceReadOnlyApprovalForm(frozen=True)` with fields:
- `form_id`, `required_checks`, `approval_statement`, `explicit_non_authorizations`, `signer_role`, `notes`

## Functions

| Function | Returns |
|---|---|
| `build_readonly_approval_form()` | `RuntimeGovernanceReadOnlyApprovalForm` |
| `readonly_approval_form_to_dict(form)` | `Dict` |
| `readonly_approval_form_to_markdown(form)` | `str` |

## Properties

- Pure, deterministic, no I/O, no timestamps, no random.
- Frozen dataclass -- immutable after construction.
