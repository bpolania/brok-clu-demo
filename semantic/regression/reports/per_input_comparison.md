# Per-Input Comparison Report

**DERIVED, NON-AUTHORITATIVE**

> This report is derived, observational, and non-authoritative. It detects byte-level changes in observed outputs only. It makes no semantic claims.

Generated: 20260107T235630Z

---

## Comparison Results

| Input ID | Input String | Status | Baseline SHA-256 | Current SHA-256 |
|----------|--------------|--------|------------------|-----------------|
| demo_input_01 | `restart alpha subsystem gracefully` | REGRESSION | `7bbc7911582de27e...` | `20f2473a5a7e0ff8...` |
| demo_input_02 | `graceful restart of alpha` | REGRESSION | `6fb6bacbd648e427...` | `618f73b4cd690e2f...` |
| demo_input_03 | `please restart the alpha subsystem in graceful mode` | REGRESSION | `c09db45880f4ee41...` | `083594d5fa80ef95...` |

---

## Notes

Byte-level change detected between baseline and current `stdout.raw.kv`. No further analysis is performed.

---

*Phase S-3: Optional Semantic Regression Gate*
