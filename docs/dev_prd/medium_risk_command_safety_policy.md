# Medium-Risk Command Safety Policy (T1176)

## Purpose

Prevent unsafe command execution patterns in medium-risk scripts.

## Rules

### R1: No subprocess with shell=True

All `subprocess` calls must use `shell=False` (the default). This
prevents shell injection attacks.

```python
# FORBIDDEN
subprocess.run(cmd, shell=True)

# REQUIRED
subprocess.run(["cmd", "arg1", "arg2"], shell=False)
```

### R2: No eval/exec

Medium-risk scripts must not use `eval()` or `exec()` to execute
dynamic code. All logic must be statically defined.

### R3: No dynamic import

Medium-risk scripts must not use `importlib.import_module()` or
`__import__()` with variable module names. All imports must be
static import statements.

### R4: Sanitize all inputs

Any user-provided input (CLI args, config values, file paths) must
be validated before use. Use allowlists, not blocklists.

## Enforcement

- Code review: manual check during review
- Static analysis: grep for forbidden patterns
- Promotion checklist: T1179 includes command safety verification
