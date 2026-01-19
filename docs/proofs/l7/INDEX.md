# L-7 Evidence Directory Index

## Purpose

This directory contains captured outputs demonstrating L-7 locator contract behavior
for all required scenarios, including END-TO-END evidence for both success paths.

## Evidence Files

| File | Scenario | What It Proves |
|------|----------|----------------|
| `01_reject_not_found.txt` | REJECT decision | REJECT always returns `discovery_status=authoritative_not_found` |
| `02_accept_ambiguous.txt` | ACCEPT + multiple matches | Wrapper correctly returns AMBIGUOUS when SHA256 matches multiple files |
| `03_expanded_success_unit.txt` | Expanded discovery (unit) | Unit test proves UNIQUE outcome algorithm is correct |
| `04_determinism.txt` | Determinism check | Identical inputs produce identical discovery_status and authoritative fields |
| `05_delta_only_success.txt` | **Delta-only success (E2E)** | Real ./brok-run invocation with authoritative_found via delta |
| `06_expanded_discovery_success.txt` | **Expanded success (E2E)** | Real ./brok-run invocation with authoritative_found via SHA256 match |

## Scenario Coverage

### 1. authoritative_not_found
- **File**: `01_reject_not_found.txt`
- **Trigger**: REJECT decision (no execution expected)
- **Output**: `discovery_status=authoritative_not_found`, `authoritative_stdout_raw_kv=null`

### 2. authoritative_ambiguous
- **File**: `02_accept_ambiguous.txt`
- **Trigger**: ACCEPT with multiple stdout.raw.kv files sharing same SHA256
- **Output**: `discovery_status=authoritative_ambiguous`, wrapper refuses to select

### 3. authoritative_found (Delta-Only) - END-TO-END
- **File**: `05_delta_only_success.txt`
- **Trigger**: Real ./brok-run invocation when l4_run directory does NOT exist
- **Method**: ./brok creates NEW l4_run directory with stdout.raw.kv in delta set
- **Output**: `discovery_status=authoritative_found`, paths and SHA256 populated
- **Key**: run_dir IS the l4_run directory (because it was newly created)

### 4. authoritative_found (Expanded Discovery) - END-TO-END
- **File**: `06_expanded_discovery_success.txt`
- **Trigger**: Real ./brok-run invocation when l4_run directory ALREADY exists
- **Method**: Delta-only fails (not in delta), expanded discovery finds unique SHA256 match
- **Output**: `discovery_status=authoritative_found`, paths and SHA256 populated
- **Key**: run_dir is m4_* (observability), authoritative_stdout_raw_kv points to l4_run_*

### 5. Unit Test Evidence (Supplemental)
- **File**: `03_expanded_success_unit.txt`
- **Purpose**: Proves the `_expanded_discovery()` algorithm is correct with controlled fixtures
- **Note**: Supplemental to the E2E evidence in `06_expanded_discovery_success.txt`

### 6. Determinism
- **File**: `04_determinism.txt`
- **Method**: Two consecutive runs with identical input
- **Output**: Identical `decision`, `discovery_status`, and `authoritative_stdout_raw_kv`

## Demo Procedure

### Reproducing Delta-Only Success (L-6 behavior)
```bash
# Ensure the l4_run directory does NOT exist
rm -rf artifacts/run/l4_run_run_3e707cb5d43d/

# Run brok-run - new directory will be in delta, delta-only finds it
./brok-run "cancel order"
# Observe: discovery_status=authoritative_found, run_dir=l4_run_*
```

### Reproducing Expanded Discovery Success (L-7 behavior)
```bash
# Ensure the l4_run directory EXISTS (run delta-only test first, or any previous run)
ls artifacts/run/l4_run_run_3e707cb5d43d/

# Run brok-run again - existing directory not in delta, expanded discovery finds it
./brok-run "cancel order"
# Observe: discovery_status=authoritative_found, run_dir=m4_*, authoritative_stdout_raw_kv=l4_run_*
```

## Notes

- Files 05 and 06 provide TRUE END-TO-END evidence (real ./brok-run invocations)
- "cancel order" is used because its stdout.raw.kv has a UNIQUE SHA256 hash
- "create payment" results in AMBIGUOUS because multiple runs produce identical output
- Unit test evidence (03) supplements E2E evidence with algorithm correctness proof

## Timestamp

Evidence captured during L-7 closure fixes.
