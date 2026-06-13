# Logging Configuration

## Log Levels

- DEBUG: Full pipeline trace
- INFO: Step completion (default)
- WARNING: Malformed input, missing optional data
- ERROR: Pipeline failure

## Log Locations

- Pipeline logs: `logs/pipeline.log`
- Alert logs: `logs/alerts.log`
- Safety logs: `logs/safety.log`

## Rotation

Manual rotation recommended. No automatic log deletion.
