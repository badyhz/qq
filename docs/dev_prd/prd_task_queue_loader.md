# PRD Task Queue Loader — T866

## Purpose

Load task queue data from markdown text strings. Pure module — no I/O, no timestamps, no random.

## API

### `load_prd_task_queue_from_markdown(markdown_text: str) -> List[PrdTask]`

Parse markdown text and return deduplicated list of `PrdTask` objects.

Supported formats:
- `- T865: PRD task loader spec`
- `T865: PRD task loader spec`
- `- T786-T789: description — completed` (range expansion)
- `| T865 | title | status |` (table rows)

Defaults for missing fields:
- status: `NOT_STARTED` (unless `completed` detected)
- allowed_files: `[]`
- dependencies: `[]`
- acceptance_commands: `[]`
- risk_level: `MEDIUM`
- notes: `["loaded_from_markdown"]`

Deduplication: first occurrence wins.

### `extract_task_ids_from_markdown(markdown_text: str) -> List[str]`

Return unique task IDs in order of first appearance.

### `find_task_section(markdown_text: str, task_id: str) -> str`

Return the `##` section containing the given task_id. Empty string if not found.

### `task_queue_loader_summary(tasks: List[PrdTask]) -> Dict[str, Any]`

Return summary with total, task_ids list, status_counts, risk_counts.
