# Runtime Governance Safety Boundaries

## Frozen Boundaries

The following are frozen and require explicit human authorization to modify:

- live trading
- order submission
- exchange clients
- API keys/secrets
- planner integration
- account state mutation
- real network execution
- runtime execution path

## Allowed Zones

Agents may modify:

- docs/dev_prd/*
- new pure core governance modules when explicitly assigned
- new unit tests when explicitly assigned
- static docs for task outputs

## Forbidden Operations

Agents must never:

- touching credentials
- placing/canceling orders
- connecting to live exchange
- changing submit scripts
- changing live runner
- changing planner executor
- reading full large logs

## Change Authorization

Any modification to frozen boundaries requires explicit human approval. Agents must not infer approval from task context.

## Failure Protocol

If a task seems to require forbidden operation, stop and report PARTIAL.
