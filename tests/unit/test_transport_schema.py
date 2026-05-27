"""T781 — Transport schema validator tests."""

import pytest
from core.transport_schema import (
    TransportSchemaValidator, RequestSchema, ResponseSchema,
    SchemaViolation, ValidationResult,
)


@pytest.fixture
def validator():
    return TransportSchemaValidator()


def test_valid_request(validator):
    schema = RequestSchema(required_headers=["Authorization"])
    result = validator.validate_request(
        "POST", "https://api.test.com",
        {"Authorization": "Bearer tok"}, {"data": "value"},
        schema,
    )
    assert result.valid


def test_invalid_method(validator):
    schema = RequestSchema(allowed_methods=["GET"])
    result = validator.validate_request("POST", "https://api.test.com", {}, None, schema)
    assert not result.valid
    assert any("method" in v.field for v in result.violations)


def test_missing_required_header(validator):
    schema = RequestSchema(required_headers=["Authorization", "X-Request-ID"])
    result = validator.validate_request("GET", "https://api.test.com", {}, None, schema)
    assert not result.valid
    assert len(result.errors()) == 2


def test_missing_body_field(validator):
    schema = RequestSchema(required_body_fields=["symbol", "side"])
    result = validator.validate_request(
        "POST", "https://api.test.com", {},
        {"symbol": "BTCUSDT"}, schema,
    )
    assert not result.valid
    assert any("side" in v.message for v in result.violations)


def test_body_too_large(validator):
    schema = RequestSchema(max_body_size_bytes=10)
    result = validator.validate_request(
        "POST", "https://api.test.com", {},
        {"data": "x" * 100}, schema,
    )
    assert not result.valid


def test_valid_response(validator):
    schema = ResponseSchema(required_fields=["id", "status"])
    result = validator.validate_response(200, {"id": "123", "status": "ok"}, schema)
    assert result.valid


def test_invalid_status_code(validator):
    schema = ResponseSchema(allowed_status_codes=[200, 201])
    result = validator.validate_response(500, {}, schema)
    assert not result.valid


def test_missing_response_field(validator):
    schema = ResponseSchema(required_fields=["id", "result"])
    result = validator.validate_response(200, {"id": "123"}, schema)
    assert not result.valid
    assert any("result" in v.message for v in result.violations)


def test_warnings_vs_errors(validator):
    result = ValidationResult(
        valid=False,
        violations=[
            SchemaViolation("field1", "error msg", "error"),
            SchemaViolation("field2", "warn msg", "warning"),
        ],
    )
    assert len(result.errors()) == 1
    assert len(result.warnings()) == 1
