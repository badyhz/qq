# Human Review Gate Decision Taxonomy

## Decision Categories

### APPROVE

**Definition:** Human explicitly authorizes the proposed action to proceed.

**Criteria:**
- All required evidence items verified
- No forbidden approvals violated
- Human reviewer has sufficient context
- Action aligns with current project state and constraints

### REJECT

**Definition:** Human denies the proposed action. Action must not proceed.

**Criteria:**
- Evidence insufficient or contradictory
- Action violates safety constraints
- Action premature given current project state
- Risk assessment does not support proceeding

### ESCALATE

**Definition:** Human forwards the decision to a higher authority level.

**Criteria:**
- Decision exceeds current reviewer's authority
- Risk level requires higher-tier approval
- Novel situation without precedent
- Conflicting evidence needs arbitration

### DEFER

**Definition:** Human postpones the decision to a later time or context.

**Criteria:**
- Insufficient information currently available
- Waiting on dependency or prerequisite
- Decision not time-critical
- Additional analysis needed before deciding

### CONDITIONAL_APPROVE

**Definition:** Human authorizes the action subject to specific conditions being met first.

**Criteria:**
- Action is directionally correct but needs guardrails
- Specific preconditions must be documented
- Conditions are verifiable and auditable
- Approval expires if conditions not met within defined scope
