# Architectural Change Notes — S19

## Authorized Touch Summary

S19 spec strictly enforces preservation of all legacy systems. Only one additive change was authorized:

### 1. `WorkCapability._handle_status` Extension
- **Change:** Supported optional payload parameters `include_activity: bool` (default False) and `activity_limit: int` (default 2).
- **Reasoning:** Disallows frontend components from reading database tables or bypassing orchestrators, keeping backend capabilities clean and decoupled.
- **Impact:** Legacies are preserved with byte-for-byte identical status payload delivery when omitted.
