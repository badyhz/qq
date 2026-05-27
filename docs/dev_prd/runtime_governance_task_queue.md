# Runtime Governance Task Queue

## Task Queue Format

Each task includes:

- task_id: unique identifier
- title: brief description
- status: completed / in_progress / NOT_STARTED / HUMAN_REVIEW_REQUIRED
- allowed files: explicit file list
- dependencies: prerequisite tasks
- acceptance command: verification command
- risk level: low / medium / high / critical
- notes: additional context

## Completed Ranges

- T786-T789: governance failure reporting stack — completed
- T790-T793: governance support stack — completed
- T794-T797: runtime governance pre-live audit layer — completed
- T798-T825: runtime governance expansion and closeout — completed
- T826-T857: read-only integration design layer — completed

## Current Phase

- T858-T864: PRD control plane setup — in_progress

## Next Proposed Queue (NOT_STARTED / HUMAN_REVIEW_REQUIRED)

- T865: PRD-driven task loader spec
- T866: PRD task queue validator
- T867: agent prompt generator from PRD
- T868: PRD acceptance command registry
- T869: PRD safety boundary checker
- T870: PRD execution report parser
- T871: PRD queue closeout packet
- T872: PRD control plane final status report

**Important:** Do not authorize T865-T872 execution in this task. Only document them as future tasks.
