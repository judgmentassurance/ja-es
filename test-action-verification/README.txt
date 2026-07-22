Each subdirectory is schema-valid, hash-valid and chain-valid, but MUST fail verify.py.
The failures establish that recommendation, execution and the sealed permitted action set agree.

Run:
  python verify.py test-action-verification/action-01-executed-action-not-permitted
  python verify.py test-action-verification/action-02-recommendation-execution-mismatch
  python verify.py test-action-verification/action-03-permitted-set-substituted
