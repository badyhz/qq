# No-Submit Release Gate Credential Policy

Task: T1184

## Rules

### No API Key Access

Code must not read, parse, or reference API key values.

### No Secret Reading

Code must not read secret tokens from files, env vars, or config.

### No Env Var Extraction

Code must not call os.environ or os.getenv for credential-related variables.
