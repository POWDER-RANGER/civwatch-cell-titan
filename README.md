# CIVWATCH CELL TITAN

**Defensive RF observability for [CIVINTELLIGENCE](https://github.com/POWDER-RANGER/CivilianIntelligence).**

Cell Titan is the specialized RF telemetry and evidence pillar. It supports cellular, Wi-Fi, D2D, and transport-domain observability, demo telemetry, optional ADB sensor collection, live events, and a hash-chained evidence trail.

> **Status:** 0.1.2 security baseline; loopback-first and fail-closed production posture.

## Role in the ecosystem

**CivilianIntelligence is the system of record.**

Cell Titan owns:

- sensor and RF telemetry
- evidence-chain creation and verification
- optional ADB discovery/capture
- live telemetry streaming

The hub can consume Titan health, telemetry, evidence, and the authenticated user-device observation envelope through a server-side integration rail.

### CIVINT observation contract

```text
GET /api/observations?n=100&domain=cellular
```

The envelope carries an explicit `live`, `demo`, `snapshot`, or `unavailable` state,
an `owner_scope: user_device` marker, bounded telemetry, evidence records, and
limitations. It reports observations rather than declaring that an IMSI catcher,
Stingray, or other specific interceptor was detected. Raw baseband contents are not
exposed by this API.

## Quick start

### One-click local Android setup

1. Install the current Android SDK Platform Tools so `adb` is available on your PATH.
2. On Android, enable **Developer options → USB debugging**, connect the phone by USB, unlock it, and accept the computer's RSA debugging prompt.
3. Double-click **START-TITAN.bat** on Windows, or run **START-TITAN.command / START-TITAN.sh** on macOS/Linux.

The launcher creates a private Python virtual environment, installs Titan's pinned dependencies, generates a local bearer credential, enables ADB for the local collector, starts Titan on `127.0.0.1:8000`, and opens the setup page. The browser receives only a loopback-bound session cookie; the long-lived bearer credential is never embedded in page JavaScript.

If Android is connected but still shows `unauthorized`, unlock the device and accept the RSA prompt, then click **Check ADB** followed by **Discover ADB**.

Android's official documentation confirms that ADB is part of Android SDK Platform Tools and that USB debugging plus explicit RSA authorization are required for an attached device to appear as an authorized `device`. citeturn770267search2turn770267search3

### Manual start

~~~bash
./launch.sh
pytest -q
~~~

## Authentication

Production or REQUIRE_AUTH=true requires TITAN_API_TOKEN and refuses to start without it.

~~~bash
export TITAN_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export REQUIRE_AUTH=true
./launch.sh
~~~

Do not place bearer credentials in the WebSocket URL.

## Route security

| Route class | Security boundary |
|---|---|
| GET /api/health | Operational metadata for discovery |
| GET /api/status | Loopback in explicit development; bearer off-box |
| GET /api/sensors | Loopback in explicit development; bearer off-box |
| GET /api/telemetry/recent | Loopback in explicit development; bearer off-box |
| GET /api/evidence/* | Loopback in explicit development; bearer off-box |
| POST /api/telemetry/* | Bearer-controlled |
| POST /api/sensors/* | Bearer + ADB_ENABLED=true |
| WS /ws/live | First-message JSON bearer handshake |

Bearer checks use constant-time comparison.

## Network policy

Default bind is loopback. Do **not** expose Titan on open-LAN HTTP.

Remote device access requires:

1. a configured bearer token
2. TLS or a VPN such as Tailscale

ADB collection remains disabled unless explicitly enabled.

## Integration with CIVINTELLIGENCE

Configure the hub with:

~~~dotenv
CELL_TITAN_BASE_URL=https://titan.internal.example
CELL_TITAN_API_TOKEN=<server-side-secret>
~~~

The token belongs on the hub/server side. It is never a browser setting.

## Evidence

Telemetry events can be sealed into the evidence chain. Verify locally with:

~~~bash
curl -s http://127.0.0.1:8000/api/evidence/verify
curl -s 'http://127.0.0.1:8000/api/evidence/tail?n=20'
~~~

## Related repositories

- [CivilianIntelligence](https://github.com/POWDER-RANGER/CivilianIntelligence) — system of record
- [Watchtower](https://github.com/POWDER-RANGER/civwatch-watchtower) — geospatial oversight pillar
- [CIVWATCH v3](https://github.com/POWDER-RANGER/civwatch-v3) — predecessor/reference RF dashboard
- [CIVWATCH](https://github.com/POWDER-RANGER/CIVWATCH) — legacy migration source

## License

MIT


---

## Public platform status — October 2026

**CIVINTELLIGENCE is live on the public web and its REST/API surface is active.**

**Public site:** https://civintelligence.onrender.com

The web platform is now the working reference implementation for the CIVWATCH ecosystem: the core application, public-data surfaces, evidence/provenance model, specialized pillars, and integration boundaries are being exercised through the deployed CIVINTELLIGENCE service.

### Applications are next

With the web application and REST contracts now active, the remaining client work is primarily **productization and platform packaging**, not rebuilding the intelligence platform from scratch. Native applications for the major target platforms are planned and will be coming soon.

The application layer can consume the same stable contracts already used by the web experience:

- **Android**
- **iOS**
- **Windows**
- **Linux**
- additional platform clients as the shared API contract matures

The existing Flutter client and service boundaries give the ecosystem a head start. Mobile/desktop applications can progressively adopt the established authentication, API, provenance, map, evidence, and desk contracts rather than duplicating backend intelligence.

### How quickly this came together

The current milestone is notable because the ecosystem moved from a multi-repository architecture and integration plan to a functioning public platform in a short development window. The difficult architectural work — ownership boundaries, public-data ingestion, REST contracts, evidence/provenance rules, Watchtower/Cell Titan integration, and the user-facing desk model — is already substantially established.

That means the next step should be treated as **client delivery on top of an operating platform**. The web application is the reference surface; native clients become additional presentation and interaction layers over the same CIVINTELLIGENCE contracts.

> **Build once at the platform layer. Deliver many clients at the edge.**

### Ecosystem rule

CIVINTELLIGENCE remains the system of record. Specialized repositories retain clear ownership of their domains, while clients consume stable public/service contracts. Legacy and predecessor repositories remain valuable migration/reference material but are not silently represented as unified production capabilities.

**Status discipline:** live means exposed and usable; available means implemented and integrated; in progress means actively being built; planned means not yet shipped. No synthetic or unavailable source is represented as live evidence.
