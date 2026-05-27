# T1162 - Untracked Freeze Ledger: File State Taxonomy

## States

### NEW

**Definition:** File appears in `git status` as untracked for the first time.
No prior classification record exists in the ledger.

**Transition rules:**
- NEW -> STALE: if unmodified for N days.
- NEW -> FROZEN: if operator explicitly freezes.
- NEW -> DUPLICATE: if content hash matches another file.
- NEW -> ORPHAN: if no module/import/config references it after scan.
- NEW -> QUARANTINED: if flagged for removal by operator.

---

### STALE

**Definition:** File has been in NEW state and remains unmodified for N consecutive
days (default N=30). Indicates abandonment or neglect.

**Transition rules:**
- STALE -> QUARANTINED: if operator escalates.
- STALE -> FROZEN: if operator explicitly freezes.
- STALE -> NEW: if file is modified again (reset).

---

### FROZEN

**Definition:** File is explicitly locked by operator decision. No automated or
manual modifications permitted without a new review cycle.

**Transition rules:**
- FROZEN -> NEW: only if operator explicitly unfreezes with recorded reason.
- FROZEN -> QUARANTINED: only if operator overrides with recorded reason.

---

### DUPLICATE

**Definition:** Content hash (SHA-256) of the file matches another file already
tracked or present in the ledger. One file is designated canonical.

**Transition rules:**
- DUPLICATE -> QUARANTINED: if operator decides duplicate should be removed.
- DUPLICATE -> NEW: if the canonical file is deleted and this file is promoted.

---

### ORPHAN

**Definition:** No import statement, configuration entry, or module reference
points to this file. It is structurally disconnected from the codebase.

**Transition rules:**
- ORPHAN -> QUARANTINED: if operator confirms it is unused.
- ORPHAN -> NEW: if a new reference is added.

---

### QUARANTINED

**Definition:** Terminal state. File is flagged for removal or special handling.
No further automated transitions. Requires human action to leave this state.

**Transition rules:**
- QUARANTINED -> (none): terminal. Only human can remove file or change state manually.
