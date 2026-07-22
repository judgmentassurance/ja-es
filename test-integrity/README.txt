Integrity-invalid records. Each is SCHEMA-VALID but fails hash or chain verification.
These exist because JSON Schema cannot detect tampering: it checks shape, not truth.
Verify with verify.py, not with a schema validator alone.
