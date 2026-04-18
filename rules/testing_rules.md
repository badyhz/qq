# Testing Rules

## Current Phase: Skeleton Stage

This file defines testing principles. Focus on dry-run testing and unit tests.
Advanced testing (backtesting, performance, CI/CD) will be added when features exist.

## Immediate Testing Requirements

### 1. Test Structure
```
tests/
├── unit/
│   ├── test_config_loader.py
│   ├── test_logger.py
│   ├── test_helpers.py
│   ├── test_data_feed.py       (when implemented)
│   ├── test_signal_engine.py   (when implemented)
│   ├── test_risk_manager.py    (when implemented)
│   ├── test_execution.pykt      (when implemented)
│   └── test_order_manager.py   (when implemented)
├── integration/
│   └── test_trading_flow.py    (when implemented)
└── fixtures/
    └── test_data.py
```

### 2. Dry-Run Testing (Primary Focus)
- All features must be testable in dry-run mode
- Use mock data for dry-run execution
- Verify no real API calls in dry-run mode
- Test error handling in dry-run mode

### 3. Unit Testing Principles
- Test naming: `test_<function_name>` or `test_<class_name>_<method>`
- Tests must be deterministic (no randomness)
- Tests must be fast
- Tests must be independent (no shared state)
- Tests must have clear assertions

### 4. Mocking Strategy
- Mock all external dependencies (API calls, websockets)
- Mock time/datetime for reproducibility
- Use synthetic market data for tests
- Include edge cases in test data

### Example Mock
```python
# Mock exchange API (when implemented)
@patch('core.execution.BinanceAPI')
def test_order_placement(mock_api):
    mock_api.create_order.return_value = {
        'orderId': 12345,
        'status': 'FILLED'
    }
    # Test implementation
```

### 5. Acceptance Testing
- Each task must have acceptance criteria
- Must validate all acceptance criteria
- Must document test results
- Must include edge cases

### Example T001 Acceptance (Completed)
- [x] Project directory structure complete

- [x] main.py executes without errors
- [x] config.yaml valid and loaded
- [x] All modules import successfully
- [x] Default mode is dry-run

## Future Testing (To Add When Features Exist)

### Integration Testing (when trading flow implemented)
- Full trading flow (signal -> risk -> execution)
- Configuration loading and validation
- Dry-run mode execution
- Error recovery paths

### Backtesting (when signal engine and historical data implemented)
- Use historical data for validation
- Compare signals against outcomes
- Validate risk calculations
- Test position management

### Performance Testing (when real trading implemented)
- Signal generation latency
- Order placement latency
- Data processing throughput
- Memory usage stability

### CI/CD Integration (when CI/CD infrastructure exists)
- All tests must pass on PR
- Coverage report on PR
- Security tests when implemented

## Test Execution

### Running Tests
```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run with coverage (when pytest-cov installed)
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/unit/test_config_loader.py

# Run with verbose output
pytest tests/ -v
```

## Testing Checklist

When implementing features:
- [ ] Unit tests for all new functions
- [ ] Tests cover happy path
- [ ] Tests cover error paths
- [ ] Tests use mocks for external dependencies
- [ ] Tests are deterministic
- [ ] Tests pass before feature is complete

## Reference

See TASKS.md for task-specific acceptance criteria
See CLAUDE.md for project testing approach
