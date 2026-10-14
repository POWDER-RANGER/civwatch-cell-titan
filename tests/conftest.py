"""Set deterministic local-only test settings before application imports."""
import os
from pathlib import Path

os.environ["CELL_TITAN_ENV"] = "development"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["TITAN_API_TOKEN"] = ""
os.environ["ALLOW_UNAUTHENTICATED_LOOPBACK"] = "true"
os.environ["ADB_ENABLED"] = "true"
os.environ["AUTO_DEMO"] = "false"
os.environ["EVIDENCE_DIR"] = str(Path("/tmp/titan-test-evidence"))
