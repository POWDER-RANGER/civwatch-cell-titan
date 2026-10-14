"""ADB setup layer: executable resolution, device-state parsing, setup diagnosis.

Everything in this package is pure (no process spawning at import time) and
takes its I/O through injectable callables, so the same code paths run in the
mocked scenario suite (Layer A) and against real ADB (Layers B/C).
"""
