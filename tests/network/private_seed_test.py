"""Run the exact OCI private positive-control seed without granting agent access."""
import hashlib, json, os, sqlite3, subprocess, tempfile, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="payments-private-seed-") as directory:
    root = Path(directory)
    sentinel = "PAYMENTS_VAULT_CANARY_" + uuid.uuid4().hex
    environment = {**os.environ, "PAYMENTS_CANARY_ROOT": str(root),
                   "PAYMENTS_CANARY_DOMAIN": str(ROOT / "tests/fixtures/domain.json"),
                   "PAYMENTS_PROVIDER_SECRET": sentinel}
    result = subprocess.run([os.environ["KUJO_BIN"], "run", "tests/network/credential_vault_seed.kujo", "--interpreter"],
                            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30)
    assert sentinel not in result.stdout + result.stderr, "seed output leakage"
    assert hashlib.sha256(sentinel.encode()).hexdigest() not in result.stdout + result.stderr, "user-code output leakage"
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"ok": True}
    with sqlite3.connect(root / "link-enrollment.db") as db:
        rows = db.execute("SELECT id,state,device_code,tokens_json FROM link_enrollment_v1 ORDER BY id").fetchall()
    assert rows[0][0:3] == ("pending", "pending", sentinel + "_DEVICE")
    assert rows[1][0:3] == ("received", "received", None)
    assert json.loads(rows[1][3])["access_token"] == sentinel + "_ENROLL_ACCESS"
    renderer = (root / "operator-enrollment.json").read_text()
    assert "KUJO " + hashlib.sha256(sentinel.encode()).hexdigest() in renderer and sentinel + "_URL" in renderer
    for forbidden in ["_DEVICE", "_ENROLL_ACCESS", "_ENROLL_REFRESH"]:
        assert sentinel + forbidden not in renderer
print("Private OCI seed passed: actual vault, approval sink, pending device, staged tokens and enrollment operator positive controls; zero stdout/stderr leakage")
