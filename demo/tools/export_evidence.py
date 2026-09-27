"""Export a standalone static evidence bundle. Reads core files; writes only demo/."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

DEMO = Path(__file__).resolve().parents[1]
ROOT = DEMO.parent
COPY_ROOT = DEMO / "evidence"
SOURCES = [
    ("runs/rc-001/evidence.json", "runs/rc-001/report-v2.md"),
    ("runs/rc-002/evidence-rc002.json", "runs/rc-002/report-rc-002.md"),
    ("runs/rc-002/evidence-rc003.json", "runs/rc-002/report-rc-003.md"),
]
copied = {}


def copy_source(relative):
    source = ROOT / relative
    destination = COPY_ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    copied[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    return destination.relative_to(DEMO).as_posix()


findings = []
for evidence_path, report_path in SOURCES:
    evidence = json.loads((ROOT / evidence_path).read_text())
    finding = {
        "id": evidence["finding_id"],
        "requirement": evidence["requirement"]["id"],
        "acceptedAt": evidence["acceptance"]["timestamp"],
        "evidence": copy_source(evidence_path),
        "report": copy_source(report_path),
        "manifest": copy_source(evidence["acceptance"]["protected_manifest"]),
        "executions": {},
    }
    copy_source(evidence["regression"]["test_artifact"])
    for phase, reference in evidence["executions"].items():
        if not reference:
            continue
        directory = Path(reference["artifact_dir"])
        record = json.loads((ROOT / directory / "execution.json").read_text())
        paths = {name: copy_source((directory / name).as_posix()) for name in [
            "execution.json", "junit.xml", "stdout.txt", "stderr.txt",
            "environment.json", "application-snapshot.json",
        ]}
        finding["executions"][phase] = {
            "record": record, "json": paths["execution.json"],
            "junit": paths["junit.xml"], "stdout": paths["stdout.txt"],
        }
    findings.append(finding)

for path in ["docs/application-contract.md", "docs/source-notes.md", "docs/evaluation.md"]:
    copy_source(path)

sessions = DEMO / "assets" / "sessions"
sessions.mkdir(parents=True, exist_ok=True)
for source in sorted((ROOT / "bob_sessions").glob("*.png")):
    shutil.copyfile(source, sessions / source.name)

commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
bundle = {"sourceCommit": commit, "findings": findings}
(DEMO / "assets" / "evidence.js").write_text(
    "// Generated from repository records by tools/export_evidence.py.\n"
    "window.RC_EVIDENCE = " + json.dumps(bundle, ensure_ascii=False, indent=2) + ";\n"
)
(COPY_ROOT / "source-manifest.json").write_text(json.dumps({
    "source_commit": commit,
    "note": "Byte-for-byte presentation copies. Original runs remain unchanged. Historical manifests apply to their contemporaneous Git checkpoints.",
    "files": copied,
}, indent=2) + "\n")
print(f"Exported {len(findings)} findings, {len(copied)} source artifacts, and {len(list(sessions.glob('*.png')))} screenshots.")
