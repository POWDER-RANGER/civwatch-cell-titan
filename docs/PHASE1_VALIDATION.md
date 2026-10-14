# Phase 1 — Operational validation runbook

**Phase:** Cell Titan observation contract live in production and consumed by CIVINTELLIGENCE
**Updated:** 2026-10-13
**Owner:** operator (merges and Render settings are manual; each merge deploys production)

## Definition of done

The phase is complete only when every gate below has evidence. Deployment state alone is not completion.

| # | Gate | Evidence required | Status |
|---|------|-------------------|--------|
| G1 | Cell Titan CI green on `main` | GitHub Actions run, Python 3.11 + 3.12 | PR #10 green; pending merge |
| G2 | Render runs current Titan | `smoke_deploy.py --expect-version 0.1.3` → all PASS | pending |
| G3 | Production contract reachable with credentials | `smoke_deploy.py` token checks PASS | pending |
| G4 | Portal deploy branch contains the Titan UI | CivilianIntelligence PR #63 merged into `deploy/render-public-web` | pending |
| G5 | Portal consumes the contract server-side | `/titan` shows ONLINE, v0.1.3, evidence verified, no banner | pending |
| G6 | Branches converged | CivilianIntelligence PR #64 merged into `main`; compare shows 0/0 | pending |
| G7 | One authorized physical-device observation | `device_acceptance.py` → `ACCEPTED 5/5`, report saved | pending — needs operator + phone |

## Measured state at time of writing

| Probe | Result | Meaning |
|-------|--------|---------|
| `civwatch-cell-titan` `/api/health` | 200 in 0.5s, `version 0.1.2`, `env production`, `auth_required true` | Service up, but old build |
| `civwatch-cell-titan` `/api/observations` | **404** | PR #9 contract never deployed |
| Titan CI on `main` | **failing since 2026-10-05** | Blocked deploys of PR #9 |
| `civintelligence` `/api/health` | 200 after **32s**, `uptimeSeconds 8` | Free-tier cold start confirmed |
| `deploy/render-public-web` vs `main` | **diverged**: main 3 ahead, 11 behind | PR #62 merged to `main` cannot reach production |

## Root causes found and fixed

1. **Titan CI red (fixed in Titan PR #10).** Tests reloaded `titan.config` with `importlib.reload`, creating a second settings object. `titan.auth` read the new one, `main` held the old one, and module-level `os.environ` writes leaked across files during pytest collection. Settings now reload in place; tests isolate per test. 40 tests pass in any order.
2. **Portal deploy branch divergence (fixed in CivilianIntelligence PR #63/#64).** Render tracks `deploy/render-public-web`; feature work merges to `main`. One reconciled branch is opened against both so they converge.
3. **UNREACHABLE on cold start (fixed in PR #63/#64).** Portal fetch timeout was 5s; a sleeping Free-tier Titan takes 30–60s to wake. The page now classifies the failure, shows WAKING, and retries every 10s for up to 8 attempts.
4. **Missing contract masked as healthy (fixed in PR #63/#64).** The portal reported healthy when evidence verified even if `/api/observations` failed. Healthy now requires both.

## Execution order

### Step 1 — Merge Titan PR #10 (G1)

Merge `fix/test-isolation-green-ci` into `main`. Confirm the CI run on `main` is green.

### Step 2 — Confirm Titan deployed (G2, G3)

`render.yaml` sets `autoDeployTrigger: commit`, but the live service did not deploy commits made after 2026-10-05. In the Render dashboard for `civwatch-cell-titan`:

- Check **Settings → Build & Deploy → Auto-Deploy**. If it is "After CI checks pass", the red CI explains the gap; it will deploy now. If it is "Off", deploy `main` manually.
- Confirm **Environment** has `TITAN_API_TOKEN` set (the service refuses to boot without it in production).

Then, from a clone of the Titan repo, with the production token in the environment (never on the command line):

```bash
export TITAN_API_TOKEN='<production token>'
python scripts/smoke_deploy.py https://civwatch-cell-titan.onrender.com --expect-version 0.1.3
```

Expected: every line `PASS`, exit code 0. The script waits up to 120s for a cold start. `version matches` failing means the old build is still serving.

### Step 3 — Portal credentials

On the Render service `civintelligence`, **Environment**:

| Variable | Value |
|----------|-------|
| `CELL_TITAN_BASE_URL` | `https://civwatch-cell-titan.onrender.com` (no trailing slash, no path) |
| `CELL_TITAN_API_TOKEN` | exactly the same value as Titan's `TITAN_API_TOKEN` |

The token is read server-side only and never sent to the browser.

### Step 4 — Merge CivilianIntelligence PR #63 (G4)

PR #63 targets `deploy/render-public-web`, which auto-deploys the portal. Wait for the Render deploy to finish.

### Step 5 — Verify `/titan` (G5)

Open `https://civintelligence.onrender.com/titan`. If Titan was asleep you will see **WAKING** with an attempt counter; it should resolve within about a minute without a manual refresh.

Expected final state: badge **ONLINE**, version **v0.1.3**, **observations: unavailable**, **evidence verified**, no banner.

`observations: unavailable` with 0 samples is the **correct** production result: the production Titan has no attached device and does no server-side discovery.

If a banner remains, it names the cause:

| Banner | Cause | Fix |
|--------|-------|-----|
| "not configured on this deployment" | `CELL_TITAN_BASE_URL` empty | Step 3 |
| "rejected this portal's server credentials" | token mismatch | Step 3, make both tokens identical |
| "running a build without the observation contract" | Titan still on 0.1.2 | Step 2 |
| "did not respond after 8 attempts" | Titan down, or URL wrong | Check Titan logs and the URL |
| "evidence chain verification failed" | tampered or corrupted chain | Investigate before trusting any record |

### Step 6 — Merge CivilianIntelligence PR #64 (G6)

Same head branch, base `main`. Afterwards `deploy/render-public-web...main` should compare as identical.

Recommended: point the Render service at `main` and retire `deploy/render-public-web` so feature merges and production cannot diverge again.

### Step 7 — Physical-device acceptance (G7)

This runs on your own computer against a **local** Titan. The local collector writes to the local evidence chain; there is no path from a local Titan to the production Titan yet (see Known limitations), so this observation will not appear on the public `/titan` page. That is by design, not a failure.

1. Install Android SDK Platform Tools so `adb` is on PATH.
2. On the phone: **Developer options → USB debugging**. Connect by USB, unlock, accept the RSA prompt.
3. Run `START-TITAN.bat` (Windows) or `START-TITAN.sh` / `START-TITAN.command`. The browser opens `http://127.0.0.1:8000`.
4. Click **Connect & Capture**.
5. In the Titan folder:

```bash
python scripts/device_acceptance.py --report acceptance-2026-10-XX.json
```

Expected: `ACCEPTED: 5/5`. The script reads the token from the launcher's `.env`.

Acceptance requires a `telemetry_adb` evidence record, which only the ADB capture route writes. Samples POSTed through the API, even ones claiming `source: adb`, cannot pass. Verified with a negative test and with a simulated device driving the real discover/capture routes.

The report lists which fields **this** phone exposed per domain (for example `operator`, `rsrp_dbm`, `rssi_dbm`, `freq_mhz`), with serials redacted. Keep it as the hardware-truth record for the capability registry. Absent fields are expected and vary by Android version, modem, carrier, and permissions.

## Known limitations (carried into the next phase)

| Limitation | Effect | Next step |
|------------|--------|-----------|
| No submission path from a local Titan to the system of record | Real device observations never reach production `/titan` | Implement the "explicit user action" submission the envelope already declares (`privacy.public_submission`) |
| `state: live` means "any non-demo sample" | An API-submitted sample is labelled `live` like an ADB capture | Add per-sample `collection_method` and derive `state` from it |
| Render Free has no persistent disk | Production evidence chain resets on every restart or spin-down (observed: chain length 1) | Persistent disk or external store before treating production evidence as durable |
| Render Free spin-down | First visitor waits up to ~60s | Now handled in the UI; a paid instance or keep-warm pinger removes the wait |
| Postgres SSL-mode warning in portal logs | Not investigated in this phase | Review `DATABASE_URL` `sslmode` |
| ALPR map, record search, God's Eye | Outside Cell Titan scope; not re-audited here | Separate production smoke pass |

## Tooling added in this phase

| Tool | Purpose |
|------|---------|
| `scripts/smoke_deploy.py` | Post-deploy validation of any Titan instance; cold-start tolerant; `--expect-version` proves which build is live. Runs in CI against a production-mode boot. |
| `scripts/device_acceptance.py` | Physical-device acceptance against a local Titan; produces a redacted JSON report. |
| CI production boot | Asserts production refuses to start without a token, then boots production config and runs the smoke check. |
| Portal diagnosis | `/titan` names the exact failure: unconfigured, waking, credentials, outdated build, or unverified evidence. |
