"""Transport request/response schema validation.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SchemaViolation:
    field: str
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    valid: bool
    violations: List[SchemaViolation] = field(default_factory=list)

    def errors(self) -> List[SchemaViolation]:
        return [v for v in self.violations if v.severity == "error"]

    def warnings(self) -> List[SchemaViolation]:
        return [v for v in self.violations if v.severity == "warning"]


@dataclass
class RequestSchema:
    """Schema for validating transport requests."""
    required_headers: List[str] = field(default_factory=list)
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH"])
    max_body_size_bytes: int = 1_048_576
    required_body_fields: List[str] = field(default_factory=list)
    url_pattern: str | None = None


@dataclass
class ResponseSchema:
    """Schema for validating transport responses."""
    required_fields: List[str] = field(default_factory=list)
    allowed_status_codes: List[int] = field(default_factory=lambda: list(range(200, 600)))
    max_body_size_bytes: int = 10_485_760


class TransportSchemaValidator:
    """Validates requests and responses against schemas."""

    def validate_request(
        self,
        method: str,
        url: str,
        headers: dict | None,
        body: dict | None,
        schema: RequestSchema,
    ) -> ValidationResult:
        violations: List[SchemaViolation] = []

        if method not in schema.allowed_methods:
            violations.append(SchemaViolation(
                field="method",
                message=f"method {method} not in allowed: {schema.allowed_methods}",
            ))

        for header in schema.required_headers:
            if not headers or header not in headers:
                violations.append(SchemaViolation(
                    field=f"headers.{header}",
                    message=f"required header '{header}' missing",
                ))

        if schema.required_body_fields and body:
            for field_name in schema.required_body_fields:
                if field_name not in body:
                    violations.append(SchemaViolation(
                        field=f"body.{field_name}",
                        message=f"required body field '{field_name}' missing",
                    ))

        if body and schema.max_body_size_bytes:
            import json
            size = len(json.dumps(body, default=str).encode())
            if size > schema.max_body_size_bytes:
                violations.append(SchemaViolation(
                    field="body",
                    message=f"body size {size} exceeds max {schema.max_body_size_bytes}",
                ))

        return ValidationResult(valid=len(violations) == 0, violations=violations)

    def validate_response(
        self,
        status_code: int,
        body: Any,
        schema: ResponseSchema,
    ) -> ValidationResult:
        violations: List[SchemaViolation] = []

        if status_code not in schema.allowed_status_codes:
            violations.append(SchemaViolation(
                field="status_code",
                message=f"status {status_code} not in allowed codes",
            ))

        if isinstance(body, dict):
            for field_name in schema.required_fields:
                if field_name not in body:
                    violations.append(SchemaViolation(
                        field=f"body.{field_name}",
                        message=f"required field '{field_name}' missing from response",
                    ))

        return ValidationResult(valid=len(violations) == 0, violations=violations)
