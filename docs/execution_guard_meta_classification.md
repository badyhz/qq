# Execution Guard Meta-Classification

Classification schema for all scripts in the guard ecosystem.

---

## 1. TRUE_GUARDED_SCRIPT

A script that:
- Imports from `core.execution_guards`
- Calls `assert_dry_run_required` (or similar) in `main()` CLI entry
- Has a matching guard test file
- **Counts toward Phase2 guarded total**

---

## 2. META_GUARD_TOOLING

A script that:
- Imports from `core.execution_guards`
- Does **NOT** call `assert_dry_run_required` in `main()`
- Uses guard modules for reporting, schema, or analysis purposes
- Does **NOT** count toward Phase2 guarded total
- Example: `generate_execution_guard_status_report.py`

---

## 3. GUARD_REPORT_GENERATOR

Subcategory of **META_GUARD_TOOLING**:
- Generates status reports about guard state
- Reads guard schema, builds reports
- No execution gating behavior
- Example: `generate_execution_guard_status_report.py`

---

## 4. GUARD_SCHEMA

Core module that defines guard schema/validation:
- `core/execution_guard_schema.py`
- Part of Phase0 infrastructure
- Not a "guarded script" -- it **IS** the guard

---

## 5. GUARD_TEST_ONLY

Test files that test guard infrastructure:
- `tests/unit/test_execution_guards.py`
- `tests/unit/test_execution_guard_schema.py`
- `tests/unit/test_execution_guard_contract.py`
- Part of Phase0 test baseline
- Not "guarded scripts" -- they **TEST** the guard

---

## 6. ORPHAN_TEST

A guard test file with no matching guarded script:
- May reference deleted/renamed scripts
- Should be investigated and resolved
- Does **NOT** count toward Phase2 guarded total

---

## 7. NOT_GUARDED

Any script without guard import or guard call in `main()`:
- Not part of Phase2 yet
- May be SAFE candidate, NEEDS_REVIEW, or NOT_ELIGIBLE

---

## Special Case: `generate_execution_guard_status_report.py`

- Phase0 deliverable (guard report generator)
- Imports `normalize_execution_mode` for report building
- Does **NOT** call `assert_dry_run_required` in `main()`
- Is **NOT** a Phase2 guarded script
- **Classified as: META_GUARD_TOOLING**

---

## Classification Decision Tree

```
Does the script import core.execution_guards?
├─ NO  → NOT_GUARDED
└─ YES
    ├─ Is it a test file?
    │   ├─ YES → Does it have a matching guarded script?
    │   │         ├─ YES → GUARD_TEST_ONLY
    │   │         └─ NO  → ORPHAN_TEST
    │   └─ NO
    │       ├─ Is it core/execution_guard_schema.py?
    │       │   └─ YES → GUARD_SCHEMA
    │       └─ NO
    │           ├─ Does main() call assert_dry_run_required?
    │           │   ├─ YES → TRUE_GUARDED_SCRIPT
    │           │   └─ NO
    │           │       ├─ Does it generate reports?
    │           │       │   └─ YES → GUARD_REPORT_GENERATOR
    │           │       └─ NO  → META_GUARD_TOOLING
```
