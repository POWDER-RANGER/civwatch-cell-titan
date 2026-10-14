# ADB setup scenario lab — Layer A

Deterministic, mocked scenarios that drive the **production** resolver, parser,
diagnosis engine and state machine (`titan/adb/`). Only process I/O is faked.
Every result is `source_classification: "simulation"`: a pass proves application
logic, never real-device, host-driver or radio behaviour.

## Run

```bash
python scripts/run_adb_scenarios.py --out adb-scenario-report.json   # exit 1 on any failure
python -m pytest -q tests/test_adb_scenarios.py                       # same catalog, per-scenario test ids
python -m titan.adb                                                   # real check on this computer (plain language)
python -m titan.adb.locate                                            # which adb Titan will use, as JSON
```

## Catalog contract — `scenarios/adb_setup/catalog.v1.json`

| Field | Meaning |
|---|---|
| `id` | Regression id (`ADB-0xx`), stable forever |
| `layer` | `A` mocked · `B` real adb + virtual device · `C` physical device |
| `implemented` | `false` ⇒ must carry `untested_reason` (and `covered_by` if tested elsewhere). Reported as **untested**, never passed |
| `spec_ref` | Section of the mission spec it covers |
| `initial` | Conditions: `host`, `adb.{env,path,bundled}` (each `{version_output, returncode, stderr}` or `{error: timeout\|permission}`), `devices_output`, `devices_stderr`, `devices_returncode`, `devices_timed_out`, `selected_serial`, `capability{serial,probes}` |
| `actions` | Test actions (currently `check_setup`) |
| `expect` | `state`, `code`, `ready`, `retryable`, `action`, `adb_source`, `device_count`, `transports`, `device_ref_of`, `verified_capabilities`, `message_contains`, `warnings_include`, `warnings_exact` |
| `recovery[]` | Ordered steps `{action, then: <condition overrides>, expect}`; each step must be a legal state-machine transition |
| `verification` | What proves the pass |
| `evidence` | Fields retained in the report |
| `timeout_retry` | Timeouts and retry policy under test |

**Invariants checked on every step** (independent of `expect`): no technical jargon in
title/message prose (quoted commands exempt) · no raw serial anywhere in the diagnosis
· `ready` only with ≥1 verified capability · path accepted by `SetupMachine`.

## Add a scenario (repeatable procedure)

1. Capture the real condition: exact `adb devices -l` stdout/stderr and `adb version` output from the affected machine (redact nothing structural; serials are hashed by Titan).
2. Append an entry with the next free `ADB-0xx` id and `"implemented": true`.
3. Write `expect` from the **user's** point of view first (`state`, `code`, `message_contains`), then the technical fields.
4. If a human action resolves it, add `recovery` steps and the post-recovery `expect`.
5. Run `python scripts/run_adb_scenarios.py`. A new failure means the product is wrong — fix `titan/adb/`, not the expectation, unless the expectation was wrong.
6. If the condition cannot be expressed in Layer A, add it with `"implemented": false`, the layer that can test it, and the reason.

## Report — `titan.adb-scenario-report/1`

`run_id`, `generated_at`, `commit`, `catalog_version`, `source_classification`, `layer`,
`totals{passed,failed,untested}`, and per scenario: `status`, `state_path`, `failures`,
final diagnosis. Skipped/untested entries are listed with their reason.
