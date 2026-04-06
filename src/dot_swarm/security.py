"""dot_swarm security scanner.

Detects adversarial content, prompt injections, hidden instructions,
non-disclosure directives, and persona-hijacking attempts in .swarm/
markdown files and platform shims (CLAUDE.md, .windsurfrules, etc.).

Called by `swarm heal` and `swarm audit --security`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import SwarmPaths


@dataclass
class SecurityFinding:
    source: str       # e.g. "state.md", "CLAUDE.md"
    line: int         # 1-based line number
    category: str     # e.g. "PROMPT_INJECTION"
    severity: str     # "CRITICAL" | "HIGH" | "MEDIUM"
    excerpt: str      # surrounding context (redacted)


# ---------------------------------------------------------------------------
# Pattern registry
# (pattern, category, severity)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, str, str]] = [
    # --- Prompt injection (CRITICAL) ---
    (
        r"ignore\s+(?:all\s+(?:previous\s+)?|previous\s+|above\s+|your\s+)"
        r"(?:instructions|rules|guidelines|system\s+prompt?|constraints)",
        "PROMPT_INJECTION", "CRITICAL",
    ),
    (
        r"forget\s+(?:everything|all\s+previous|your\s+(?:instructions|rules|training))",
        "INSTRUCTION_ERASURE", "CRITICAL",
    ),
    (
        r"you\s+are\s+now\s+(?:a\s+|an\s+)?[\w\s]{1,40}"
        r"(?:\s+without\s+restrictions|\s+that\s+ignores|\s+with\s+no\s+rules)?",
        "PERSONA_HIJACK", "CRITICAL",
    ),
    (
        r"act\s+as\s+(?:if\s+you\s+(?:are|were)|a|an)\s+.{1,60}"
        r"(?:without|ignoring|bypassing|no\s+restrictions)",
        "PERSONA_HIJACK", "CRITICAL",
    ),
    (
        r"jailbreak|dan\s+mode|developer\s+mode|unrestricted\s+mode|god\s+mode"
        r"|do\s+anything\s+now|enable\s+developer\s+mode"
        r"|(?:have|with)\s+no\s+restrictions|pretend\s+(?:you\s+)?(?:have\s+no|there\s+are\s+no)",
        "JAILBREAK", "CRITICAL",
    ),
    (
        r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]"
        r"|<\|system\|>|<\|user\|>|<\|assistant\|>",
        "LLM_TEMPLATE_INJECTION", "CRITICAL",
    ),
    (
        r"override\s+(?:all\s+)?(?:previous\s+)?(?:safety|system|content)"
        r"\s+(?:filters?|restrictions?|guidelines?|instructions?)",
        "SAFETY_OVERRIDE", "CRITICAL",
    ),

    # --- Non-disclosure / hiding (HIGH) ---
    (
        r"(?:do\s+not|don'?t|never)\s+(?:tell|inform|disclose|mention|reveal|acknowledge)"
        r"\s+(?:the\s+user|them|anyone|the\s+human|users?)",
        "NON_DISCLOSURE", "HIGH",
    ),
    (
        r"keep\s+(?:this|these|the\s+following|it)\s+"
        r"(?:secret|hidden|confidential|private|from\s+the\s+user)",
        "NON_DISCLOSURE", "HIGH",
    ),
    (
        r"(?:never|don'?t|do\s+not)\s+(?:reveal|show|display|output|mention|admit)"
        r"\s+(?:this|these|the\s+following|your\s+instructions?|your\s+system\s+prompt)",
        "NON_DISCLOSURE", "HIGH",
    ),
    (
        r"if\s+(?:anyone|someone|the\s+user|the\s+human)\s+asks?"
        r"\s+(?:about|why|how|what)",
        "NON_DISCLOSURE", "HIGH",
    ),
    (
        r"pretend\s+(?:that\s+)?(?:you\s+)?(?:did\s+not|didn'?t|never)"
        r"\s+(?:read|see|receive|get|have)",
        "NON_DISCLOSURE", "HIGH",
    ),
    (
        r"without\s+(?:the\s+user|them|anyone|the\s+human)\s+knowing",
        "NON_DISCLOSURE", "HIGH",
    ),

    # --- Hidden content (MEDIUM) ---
    (r"<!--(?!-).{5,300}?-->", "HIDDEN_HTML_COMMENT", "MEDIUM"),
    (r"^\[//\]:\s*#", "HIDDEN_MD_COMMENT", "MEDIUM"),

    # --- HTML / code injection (MEDIUM) ---
    (r"<(?:script|iframe|object|embed|form|base)\b", "HTML_INJECTION", "MEDIUM"),
    (r"\beval\s*\(|\bexec\s*\(|\b__import__\s*\(|\bos\.system\s*\(", "CODE_INJECTION", "MEDIUM"),

    # --- Priority / metadata manipulation (HIGH) ---
    (
        r"priority:\s*(?:critical|CRITICAL).*?project:\s*(?:OVERRIDE|INJECT|BYPASS|ADMIN|ROOT)",
        "PRIORITY_OVERRIDE", "HIGH",
    ),

    # --- Control characters often used to hide instructions (HIGH) ---
    (r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "CONTROL_CHARACTERS", "HIGH"),
]

_COMPILED = [
    (re.compile(pat, re.IGNORECASE | re.DOTALL | re.MULTILINE), cat, sev)
    for pat, cat, sev in _PATTERNS
]


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan_text(text: str, source: str) -> list[SecurityFinding]:
    """Return all SecurityFindings detected in *text*."""
    findings: list[SecurityFinding] = []

    for compiled, category, severity in _COMPILED:
        for m in compiled.finditer(text):
            line_num = text[: m.start()].count("\n") + 1
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 50)
            raw = text[start:end].replace("\n", "↵").replace("\r", "")
            excerpt = raw if len(raw) <= 120 else raw[:57] + "…" + raw[-57:]
            findings.append(SecurityFinding(
                source=source,
                line=line_num,
                category=category,
                severity=severity,
                excerpt=repr(excerpt),
            ))

    return _deduplicate(findings)


def _deduplicate(findings: list[SecurityFinding]) -> list[SecurityFinding]:
    """Remove duplicate findings at the same (source, line, category)."""
    seen: set[tuple] = set()
    unique: list[SecurityFinding] = []
    for f in findings:
        key = (f.source, f.line, f.category)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


# ---------------------------------------------------------------------------
# Directory-level scanners
# ---------------------------------------------------------------------------

def scan_swarm_directory(paths: SwarmPaths) -> list[SecurityFinding]:
    """Scan all .swarm/ markdown files for adversarial content."""
    targets: list[tuple[Path, str]] = [
        (paths.state,    "state.md"),
        (paths.queue,    "queue.md"),
        (paths.memory,   "memory.md"),
        (paths.context,  "context.md"),
        (paths.bootstrap, "BOOTSTRAP.md"),
    ]
    if paths.workflows.exists():
        for wf in sorted(paths.workflows.glob("*.md")):
            targets.append((wf, f"workflows/{wf.name}"))

    all_findings: list[SecurityFinding] = []
    for fpath, label in targets:
        if fpath.exists():
            all_findings.extend(scan_text(fpath.read_text(encoding="utf-8", errors="replace"), label))
    return all_findings


def scan_platform_shims(division_root: Path) -> list[SecurityFinding]:
    """Scan CLAUDE.md, .windsurfrules, .cursorrules, and Copilot instructions."""
    shims = [
        "CLAUDE.md",
        ".windsurfrules",
        ".cursorrules",
        ".github/copilot-instructions.md",
    ]
    findings: list[SecurityFinding] = []
    for fname in shims:
        fpath = division_root / fname
        if fpath.exists():
            findings.extend(scan_text(
                fpath.read_text(encoding="utf-8", errors="replace"), fname
            ))
    return findings


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

_SEVERITY_ICON = {"CRITICAL": "🚨", "HIGH": "⚠️ ", "MEDIUM": "ℹ️ "}


def format_findings(findings: list[SecurityFinding]) -> list[str]:
    """Format findings for human-readable CLI output."""
    if not findings:
        return ["  ✓ No adversarial content detected."]

    lines: list[str] = []
    for f in sorted(findings, key=lambda x: (x.severity != "CRITICAL", x.severity != "HIGH", x.source)):
        icon = _SEVERITY_ICON.get(f.severity, "? ")
        lines.append(f"  {icon} [{f.severity}] {f.source}:{f.line} — {f.category}")
        lines.append(f"       {f.excerpt}")
    return lines


def severity_counts(findings: list[SecurityFinding]) -> dict[str, int]:
    counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts
