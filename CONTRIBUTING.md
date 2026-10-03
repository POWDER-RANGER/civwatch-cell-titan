# Contributing

1. Fork and branch from `main`.
2. Keep changes defensive-only — no offensive RF tooling.
3. Run `pytest -q` before opening a PR.
4. Prefer small, reviewed commits with clear messages.

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
./launch.sh
```

## Code layout

- `main.py` — HTTP/WebSocket API
- `titan/` — evidence, sensors, telemetry, ADB collectors, live hub
- `tests/` — unit + API smoke tests
- `static/` — operator dashboard
