#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


SECRET_ENV_KEYS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "MINIO_SECRET_KEY",
    "SMTP_PASSWORD",
    "AI_OPENAI_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "PLAID_SECRET",
    "PLAID_WEBHOOK_SECRET",
]

PLACEHOLDER_RE = re.compile(
    r"^$|^change-me$|^changeme$|^replace-me$|^<.+>$|^your[-_].+$|^example$",
    re.IGNORECASE,
)

SENSITIVE_VALUE_PATTERNS = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "stripe_secret": re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "playwright-report",
    "test-results",
    "perf-artifacts",
    "tmp",
}

IGNORED_PATH_FRAGMENTS = [
    "docs/",
    "backend/app/tests/",
    "frontend/e2e/",
]


@dataclass(slots=True)
class Finding:
    type: str
    severity: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"type": self.type, "severity": self.severity, "path": self.path, "message": self.message}


def parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.match(value))


def should_skip(path: Path) -> bool:
    posix = path.as_posix()
    return any(fragment in posix for fragment in IGNORED_PATH_FRAGMENTS)


def scan_files(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in file_path.parts):
            continue
        if should_skip(file_path):
            continue
        if file_path.name.startswith(".env") and file_path.name != ".env.example":
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue

        for name, pattern in SENSITIVE_VALUE_PATTERNS.items():
            match = pattern.search(content)
            if not match:
                continue
            findings.append(
                Finding(
                    type="embedded_secret_pattern",
                    severity="critical",
                    path=file_path.as_posix(),
                    message=f"Matched sensitive pattern '{name}'",
                )
            )
            break
    return findings


def build_markdown_report(report: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append("# Secret Hygiene Audit Report")
    lines.append("")
    lines.append(f"- Root: `{report['root']}`")
    lines.append(f"- Env file: `{report['env_file']}`")
    lines.append(f"- Status: **{report['status']}**")
    lines.append("")
    lines.append("## Env Key Checks")
    for item in report["env_key_checks"]:
        lines.append(f"- `{item['key']}`: {item['status']} ({item['note']})")
    lines.append("")
    lines.append("## Findings")
    findings = report["findings"]
    if not findings:
        lines.append("- No critical embedded-secret findings.")
    else:
        for finding in findings:
            lines.append(f"- [{finding['severity']}] `{finding['path']}`: {finding['message']}")
    lines.append("")
    lines.append("## Checklist")
    lines.append("- Keep `.env` and `.env.production` untracked.")
    lines.append("- Use CI/secret-manager injected values for production keys.")
    lines.append("- Rotate any key immediately if exposed in logs or commits.")
    lines.append("- Run this audit before release tagging.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate secret-hygiene audit artifacts.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--env-file", default=".env.example")
    parser.add_argument("--out-json", default="secret-hygiene-report.json")
    parser.add_argument("--out-md", default="secret-hygiene-report.md")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    env_file = (root / args.env_file).resolve()
    if not env_file.exists():
        raise FileNotFoundError(f"Env file not found: {env_file}")

    env_data = parse_env_file(env_file)
    env_checks: list[dict[str, str]] = []
    findings: list[Finding] = []

    for key in SECRET_ENV_KEYS:
        if key not in env_data:
            env_checks.append({"key": key, "status": "missing", "note": "add key to template"})
            findings.append(Finding("env_missing_key", "high", env_file.as_posix(), f"Missing env key: {key}"))
            continue
        value = env_data[key]
        if is_placeholder(value):
            env_checks.append({"key": key, "status": "ok", "note": "placeholder/empty"})
            continue
        pattern_name = next((name for name, pattern in SENSITIVE_VALUE_PATTERNS.items() if pattern.search(value)), None)
        if pattern_name:
            env_checks.append({"key": key, "status": "critical", "note": f"matched {pattern_name}"})
            findings.append(
                Finding(
                    type="env_template_secret_value",
                    severity="critical",
                    path=env_file.as_posix(),
                    message=f"{key} appears to contain a real secret value",
                )
            )
        else:
            env_checks.append({"key": key, "status": "warn", "note": "non-placeholder value"})

    findings.extend(scan_files(root))
    finding_dicts = [f.as_dict() for f in findings]
    has_critical = any(f["severity"] == "critical" for f in finding_dicts)
    status = "FAIL" if has_critical else "PASS"

    report: dict[str, object] = {
        "root": root.as_posix(),
        "env_file": env_file.as_posix(),
        "status": status,
        "env_key_checks": env_checks,
        "findings": finding_dicts,
    }

    Path(args.out_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path(args.out_md).write_text(build_markdown_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if has_critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
