# CELL TITAN — status

**Version:** 0.1.2 (auth boundary)
**Updated:** 2026-10-03

## Shipped

- [x] Bearer token on write + ADB routes
- [x] ADB disabled by default
- [x] Default bind 127.0.0.1
- [x] WS token handshake via first JSON message (token never appears in URL)
- [x] Auth tests
- [x] Remote telemetry/evidence reads require bearer auth; loopback development remains available when explicitly enabled

## Client policy

Localhost / emulator only until TLS (or Tailscale) is in front of Titan for remote devices.
