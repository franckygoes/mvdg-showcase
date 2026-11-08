#!/usr/bin/env python3
"""Verify the public MVDG showcase without external dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "README.md",
    "NOTICE.md",
    "MANIFEST.sha256",
    "assets/mvdg-social-card.png",
    "assets/mvdg-coherence.svg",
    "docs/METHOD_OVERVIEW.md",
    "docs/DEMONSTRATED_CASE.md",
    "docs/AXIOM_RELATION.md",
    "docs/PUBLIC_BOUNDARY.md",
    "examples/synthetic_case.json",
    "verification/mvdg_showcase_report.json",
)

FORBIDDEN_PATTERNS = (
    re.compile("/" + "Users" + "/", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]", re.IGNORECASE),
)


def fail(message: str) -> None:
    print(f"MVDG_SHOWCASE_CHECK=FAIL reason={message}")
    raise SystemExit(1)


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        fail("invalid_png")
    return struct.unpack(">II", header[16:24])


def verify_manifest(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        target = ROOT / relative
        if not target.is_file():
            fail(f"manifest_missing:{relative}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            fail(f"manifest_mismatch:{relative}")


def main() -> int:
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(f"missing_file:{relative}")

    width, height = png_dimensions(ROOT / "assets/mvdg-social-card.png")
    if (width, height) != (1200, 630):
        fail(f"social_card_dimensions:{width}x{height}")

    verify_manifest(ROOT / "MANIFEST.sha256")

    synthetic = json.loads((ROOT / "examples/synthetic_case.json").read_text(encoding="utf-8"))
    if synthetic.get("nature") != "synthetic":
        fail("example_not_synthetic")
    findings = synthetic.get("findings", [])
    if [item.get("status") for item in findings] != ["PASS", "FAIL", "REVIEW"]:
        fail("unexpected_finding_statuses")
    if synthetic.get("decision") != "HUMAN_REVIEW":
        fail("missing_human_review")

    report = json.loads((ROOT / "verification/mvdg_showcase_report.json").read_text(encoding="utf-8"))
    metrics = report.get("public_metrics", {})
    expected = {
        "source_files_reviewed": 9,
        "controlled_reports": 9,
        "documented_corrections": 3,
        "exact_third_party_matches": "7/9",
    }
    if metrics != expected:
        fail("public_metrics_changed")
    if report.get("license_selected") is not False:
        fail("license_state_changed")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".build" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".json", ".py", ".svg", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                fail(f"forbidden_pattern:{path.relative_to(ROOT)}")

    digest = hashlib.sha256((ROOT / "assets/mvdg-social-card.png").read_bytes()).hexdigest()
    if len(digest) != 64:
        fail("invalid_digest")

    print(
        "MVDG_SHOWCASE_CHECK=PASS "
        f"files={len(REQUIRED)} synthetic_findings={len(findings)} public_metrics={len(metrics)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
