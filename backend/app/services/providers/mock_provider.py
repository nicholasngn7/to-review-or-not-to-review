"""Deterministic mock review provider.

Produces credible, repeatable findings for each reviewer persona from a
`ParsedDiff` using simple heuristics. There is no AI/LLM here -- given the same
diff and persona, the output is always identical.

This is the default provider so the whole app runs locally with no credentials
or paid API calls. A real provider (Bedrock / OpenAI / Anthropic) implements the
same `ReviewProvider` interface and slots in behind `REVIEW_PROVIDER`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

from app.models.diff import DiffFile, ParsedDiff
from app.models.enums import FindingSeverity, ReviewerPersona, RiskLevel
from app.models.review import HunkReference, PersonaReview, ReviewFinding
from app.personas.registry import get_persona_spec

from .base import ReviewProvider

# ---- File classification ---------------------------------------------------

FRONTEND_EXTS = (".tsx", ".ts", ".jsx", ".js", ".css", ".scss", ".html")
BACKEND_EXTS = (".py",)
CONFIG_EXTS = (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env")
CONFIG_NAMES = ("dockerfile", "makefile", "requirements.txt")


def file_path_of(file: DiffFile) -> Optional[str]:
    """Best display path for a file (new path preferred)."""
    return file.new_path or file.old_path


def _ext(path: Optional[str]) -> str:
    if not path:
        return ""
    return os.path.splitext(path)[1].lower()


def is_test_file(path: Optional[str]) -> bool:
    if not path:
        return False
    p = path.lower()
    base = os.path.basename(p)
    return (
        "test" in base
        or "spec" in base
        or "/tests/" in p
        or p.startswith("tests/")
        or "__tests__" in p
    )


def is_frontend_file(path: Optional[str]) -> bool:
    return _ext(path) in FRONTEND_EXTS


def is_backend_file(path: Optional[str]) -> bool:
    return _ext(path) in BACKEND_EXTS


def is_config_file(path: Optional[str]) -> bool:
    if not path:
        return False
    base = os.path.basename(path).lower()
    return _ext(path) in CONFIG_EXTS or base in CONFIG_NAMES


# ---- Line scanning ----------------------------------------------------------


@dataclass(frozen=True)
class LineRef:
    """An added or removed line together with where it lives in the diff."""

    file_path: Optional[str]
    hunk_index: int
    header: str
    line_no: Optional[int]
    content: str

    def hunk_reference(self) -> HunkReference:
        return HunkReference(
            hunk_index=self.hunk_index, header=self.header, line=self.line_no
        )


def _collect_lines(parsed: ParsedDiff, kind: str) -> list[LineRef]:
    """Flatten all lines of a given kind ('added'/'removed') with context."""
    refs: list[LineRef] = []
    for file in parsed.files:
        path = file_path_of(file)
        for hunk_index, hunk in enumerate(file.hunks):
            for line in hunk.lines:
                if line.kind != kind:
                    continue
                line_no = line.new_line_no if kind == "added" else line.old_line_no
                refs.append(
                    LineRef(
                        file_path=path,
                        hunk_index=hunk_index,
                        header=hunk.header,
                        line_no=line_no,
                        content=line.content,
                    )
                )
    return refs


# Security term -> (severity, human label). Lowercased substring match unless the
# term itself is case-sensitive code (eval(, innerHTML, etc.).
_SECURITY_TERMS: dict[str, tuple[FindingSeverity, str]] = {
    "password": (FindingSeverity.MEDIUM, "password reference"),
    "secret": (FindingSeverity.MEDIUM, "secret reference"),
    "token": (FindingSeverity.MEDIUM, "token reference"),
    "apikey": (FindingSeverity.MEDIUM, "API key reference"),
    "api_key": (FindingSeverity.MEDIUM, "API key reference"),
    "privatekey": (FindingSeverity.HIGH, "private key reference"),
    "private_key": (FindingSeverity.HIGH, "private key reference"),
    "eval(": (FindingSeverity.HIGH, "use of eval()"),
    "innerhtml": (FindingSeverity.MEDIUM, "innerHTML assignment"),
    "subprocess": (FindingSeverity.MEDIUM, "subprocess usage"),
    "shell=true": (FindingSeverity.HIGH, "shell=True usage"),
    "http://": (FindingSeverity.LOW, "insecure http:// URL"),
}

_SEVERITY_ORDER = {
    FindingSeverity.INFO: 0,
    FindingSeverity.LOW: 1,
    FindingSeverity.MEDIUM: 2,
    FindingSeverity.HIGH: 3,
}


def _persona_risk(findings: list[ReviewFinding]) -> RiskLevel:
    if not findings:
        return RiskLevel.LOW
    top = max(_SEVERITY_ORDER[f.severity] for f in findings)
    if top >= _SEVERITY_ORDER[FindingSeverity.HIGH]:
        return RiskLevel.HIGH
    if top >= _SEVERITY_ORDER[FindingSeverity.MEDIUM]:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _persona_summary(
    persona: ReviewerPersona, findings: list[ReviewFinding]
) -> str:
    label = get_persona_spec(persona).display_name
    if not findings:
        return f"No concerns from the {label} reviewer."
    highs = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
    mediums = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
    parts = [f"{len(findings)} finding(s)"]
    if highs:
        parts.append(f"{highs} high")
    if mediums:
        parts.append(f"{mediums} medium")
    return f"{label} reviewer raised " + ", ".join(parts) + "."


class _MockDiffSession:
    """Holds per-diff state and produces deterministic findings per persona."""

    def __init__(self, parsed: ParsedDiff) -> None:
        self.parsed = parsed
        self.added = _collect_lines(parsed, "added")
        self.removed = _collect_lines(parsed, "removed")
        self._counters: dict[str, int] = {}

    def findings_for(self, persona: ReviewerPersona) -> list[ReviewFinding]:
        handlers: dict[ReviewerPersona, Callable[[], list[ReviewFinding]]] = {
            ReviewerPersona.ARCHITECT: self._architect,
            ReviewerPersona.QA: self._qa,
            ReviewerPersona.SECURITY: self._security,
            ReviewerPersona.FRONTEND: self._frontend,
            ReviewerPersona.BACKEND: self._backend,
            ReviewerPersona.SRE: self._sre,
            ReviewerPersona.PRODUCT: self._product,
        }
        return handlers[persona]()

    # -- helpers --
    def _finding(
        self,
        persona: ReviewerPersona,
        severity: FindingSeverity,
        title: str,
        explanation: str,
        recommendation: str,
        *,
        file_path: Optional[str] = None,
        hunk_reference: Optional[HunkReference] = None,
        confidence: Optional[float] = None,
    ) -> ReviewFinding:
        n = self._counters.get(persona.value, 0) + 1
        self._counters[persona.value] = n
        return ReviewFinding(
            id=f"{persona.value}-{n}",
            reviewer=persona,
            severity=severity,
            title=title,
            explanation=explanation,
            recommendation=recommendation,
            file_path=file_path,
            hunk_reference=hunk_reference,
            confidence=confidence,
        )

    def _changed_categories(self) -> set[str]:
        cats: set[str] = set()
        for file in self.parsed.files:
            path = file_path_of(file)
            if is_test_file(path):
                cats.add("test")
            elif is_frontend_file(path):
                cats.add("frontend")
            elif is_backend_file(path):
                cats.add("backend")
            elif is_config_file(path):
                cats.add("config")
        return cats

    # -- personas --
    def _architect(self) -> list[ReviewFinding]:
        p = ReviewerPersona.ARCHITECT
        out: list[ReviewFinding] = []
        stats = self.parsed.stats
        total_changes = stats.added_lines + stats.removed_lines

        if total_changes > 150:
            out.append(
                self._finding(
                    p,
                    FindingSeverity.MEDIUM,
                    "Large change set",
                    f"This MR touches {total_changes} lines across "
                    f"{stats.files_changed} file(s), which is large to review in "
                    "one pass.",
                    "Consider splitting into smaller, independently reviewable MRs.",
                    confidence=0.6,
                )
            )

        if stats.files_changed >= 8:
            out.append(
                self._finding(
                    p,
                    FindingSeverity.MEDIUM,
                    "Many files changed",
                    f"{stats.files_changed} files are changed in a single MR.",
                    "Group related changes and split unrelated ones for clearer review.",
                    confidence=0.55,
                )
            )

        cats = self._changed_categories()
        if "frontend" in cats and "backend" in cats:
            out.append(
                self._finding(
                    p,
                    FindingSeverity.MEDIUM,
                    "Change spans frontend and backend",
                    "Both frontend and backend files change together, which can "
                    "couple deployments and complicate rollback.",
                    "Confirm the boundary/contract is intentional and consider "
                    "sequencing the changes.",
                    confidence=0.5,
                )
            )

        if len(cats - {"test"}) >= 3:
            out.append(
                self._finding(
                    p,
                    FindingSeverity.LOW,
                    "MR mixes multiple concerns",
                    f"Changes touch several areas ({', '.join(sorted(cats))}).",
                    "Keep MRs focused on a single concern where practical.",
                    confidence=0.45,
                )
            )

        return out

    def _qa(self) -> list[ReviewFinding]:
        p = ReviewerPersona.QA
        out: list[ReviewFinding] = []

        test_files_changed = any(
            is_test_file(file_path_of(f)) for f in self.parsed.files
        )

        # Deleted tests are a clear regression-risk signal.
        for file in self.parsed.files:
            path = file_path_of(file)
            if file.change_type == "deleted" and is_test_file(path):
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.HIGH,
                        "Test file deleted",
                        f"The test file '{path}' was deleted, reducing regression "
                        "coverage.",
                        "Confirm the tests are obsolete or migrate them before merging.",
                        file_path=path,
                        confidence=0.8,
                    )
                )

        prod_code_files = [
            file_path_of(f)
            for f in self.parsed.files
            if f.hunks
            and not is_test_file(file_path_of(f))
            and (
                is_backend_file(file_path_of(f)) or is_frontend_file(file_path_of(f))
            )
        ]

        if prod_code_files and not test_files_changed:
            prod_added = sum(
                1
                for ln in self.added
                if not is_test_file(ln.file_path)
                and (
                    is_backend_file(ln.file_path) or is_frontend_file(ln.file_path)
                )
            )
            severity = (
                FindingSeverity.HIGH if prod_added > 120 else FindingSeverity.MEDIUM
            )
            out.append(
                self._finding(
                    p,
                    severity,
                    "Production code changed without test updates",
                    f"{len(prod_code_files)} production file(s) changed but no test "
                    "files were added or modified, so regression risk is unvalidated.",
                    "Add or update tests covering the changed logic and edge cases.",
                    file_path=prod_code_files[0],
                    confidence=0.65,
                )
            )

        return out

    def _security(self) -> list[ReviewFinding]:
        p = ReviewerPersona.SECURITY
        out: list[ReviewFinding] = []
        seen: set[tuple[str, Optional[str], Optional[int]]] = set()

        for ref in self.added:
            lowered = ref.content.lower()
            for term, (severity, label) in _SECURITY_TERMS.items():
                if term not in lowered:
                    continue
                key = (term, ref.file_path, ref.line_no)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    self._finding(
                        p,
                        severity,
                        f"Possible {label}",
                        f"An added line appears to contain a {label}. This may be a "
                        "false positive, but is worth a closer look.",
                        "Review this line: avoid committing secrets, and prefer "
                        "safe APIs / environment configuration where applicable.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.45,
                    )
                )
        return out

    def _frontend(self) -> list[ReviewFinding]:
        p = ReviewerPersona.FRONTEND
        out: list[ReviewFinding] = []

        frontend_added = [ln for ln in self.added if is_frontend_file(ln.file_path)]

        for ref in frontend_added:
            lowered = ref.content.lower()
            if "innerhtml" in lowered:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.MEDIUM,
                        "Direct innerHTML usage",
                        "Setting innerHTML can introduce XSS and bypasses React's "
                        "rendering model.",
                        "Render via JSX/state, or sanitize input if raw HTML is "
                        "truly required.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.6,
                    )
                )
            if (
                "document.getelementbyid" in lowered
                or "document.queryselector" in lowered
                or ".appendchild(" in lowered
            ):
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.LOW,
                        "Direct DOM manipulation",
                        "Direct DOM access can fight React's virtual DOM and hurt "
                        "maintainability.",
                        "Prefer refs and declarative state over imperative DOM calls.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.5,
                    )
                )
            if "useeffect" in lowered:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.INFO,
                        "useEffect change",
                        "An effect was added or changed; effects are a common source "
                        "of subtle bugs.",
                        "Verify the dependency array and cleanup are correct.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.4,
                    )
                )
            if "<img" in lowered and "alt=" not in lowered:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.LOW,
                        "Image without alt text",
                        "An <img> was added without an alt attribute, which hurts "
                        "accessibility.",
                        "Add a descriptive alt attribute (or alt=\"\" if decorative).",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.55,
                    )
                )

        # Large component change (per frontend file).
        per_file_added: dict[Optional[str], int] = {}
        for ln in frontend_added:
            per_file_added[ln.file_path] = per_file_added.get(ln.file_path, 0) + 1
        for path, count in per_file_added.items():
            if count > 80:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.LOW,
                        "Large component change",
                        f"'{path}' adds {count} lines; large components are harder to "
                        "review and maintain.",
                        "Consider extracting subcomponents or hooks to clarify "
                        "responsibilities.",
                        file_path=path,
                        confidence=0.45,
                    )
                )

        return out

    def _backend(self) -> list[ReviewFinding]:
        p = ReviewerPersona.BACKEND
        out: list[ReviewFinding] = []

        backend_added = [ln for ln in self.added if is_backend_file(ln.file_path)]

        for ref in backend_added:
            content = ref.content
            lowered = content.lower()
            stripped = content.strip()

            if "except exception" in lowered or stripped == "except:":
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.MEDIUM,
                        "Broad exception handler",
                        "Catching the base Exception (or a bare except) can hide "
                        "real errors.",
                        "Catch specific exceptions and re-raise or log unexpected ones.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.6,
                    )
                )
            if "todo" in lowered or "fixme" in lowered:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.LOW,
                        "TODO/FIXME in code",
                        "A TODO/FIXME was added, signalling unfinished work.",
                        "Resolve before merge or link a tracked follow-up issue.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.5,
                    )
                )
            if any(
                kw in content for kw in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ")
            ) and any(tok in content for tok in ("+", "%", 'f"', "f'", ".format(")):
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.HIGH,
                        "Possible SQL string construction",
                        "A SQL statement appears to be built via string formatting, "
                        "which risks SQL injection.",
                        "Use parameterized queries / bound parameters instead.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.55,
                    )
                )
            if "@app." in content or "@router." in content:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.INFO,
                        "API handler changed",
                        "A route/handler was added or changed.",
                        "Confirm request inputs are validated with typed models and "
                        "errors are explicit.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.4,
                    )
                )

        return out

    def _sre(self) -> list[ReviewFinding]:
        p = ReviewerPersona.SRE
        out: list[ReviewFinding] = []

        # Removed logging anywhere.
        for ref in self.removed:
            lowered = ref.content.lower()
            if any(
                marker in lowered
                for marker in ("logger.", "logging.", "log.", "console.log")
            ):
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.MEDIUM,
                        "Logging removed",
                        "A log statement was removed, which can reduce on-call "
                        "visibility.",
                        "Keep observability for important paths, or replace with "
                        "structured logging.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.5,
                    )
                )

        # Network calls without a timeout.
        for ref in self.added:
            content = ref.content
            lowered = content.lower()
            if any(
                call in lowered
                for call in (
                    "requests.get(",
                    "requests.post(",
                    "urlopen(",
                    "httpx.get(",
                    "httpx.post(",
                    "fetch(",
                )
            ) and "timeout" not in lowered:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.MEDIUM,
                        "Network call without timeout",
                        "An outbound network call appears to have no timeout, risking "
                        "hangs under failure.",
                        "Set an explicit timeout and consider retry/backoff handling.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.5,
                    )
                )

        # Swallowed exceptions: an added `except ...:` immediately followed by `pass`.
        for file in self.parsed.files:
            path = file_path_of(file)
            for hunk_index, hunk in enumerate(file.hunks):
                added_seq = [ln for ln in hunk.lines if ln.kind == "added"]
                for idx, line in enumerate(added_seq[:-1]):
                    if line.content.strip().startswith("except") and added_seq[
                        idx + 1
                    ].content.strip() == "pass":
                        out.append(
                            self._finding(
                                p,
                                FindingSeverity.MEDIUM,
                                "Swallowed exception",
                                "An exception handler appears to silently pass, hiding "
                                "failures from operators.",
                                "Log the error (with context) or handle it explicitly.",
                                file_path=path,
                                hunk_reference=HunkReference(
                                    hunk_index=hunk_index,
                                    header=hunk.header,
                                    line=line.new_line_no,
                                ),
                                confidence=0.55,
                            )
                        )

        return out

    def _product(self) -> list[ReviewFinding]:
        p = ReviewerPersona.PRODUCT
        out: list[ReviewFinding] = []

        for ref in self.added:
            content = ref.content
            lowered = content.lower()

            if "todo" in lowered or "fixme" in lowered:
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.LOW,
                        "Unfinished work marker",
                        "A TODO/FIXME may indicate incomplete behavior or future "
                        "support burden.",
                        "Capture the intent in docs or a tracked issue with clear "
                        "acceptance criteria.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.4,
                    )
                )

            if is_frontend_file(ref.file_path) and any(
                marker in lowered
                for marker in ("placeholder=", "aria-label", "label", "title=")
            ):
                out.append(
                    self._finding(
                        p,
                        FindingSeverity.INFO,
                        "User-facing text changed",
                        "User-facing copy/labels appear to change; wording affects UX "
                        "and support.",
                        "Confirm wording with product and update docs/tests if needed.",
                        file_path=ref.file_path,
                        hunk_reference=ref.hunk_reference(),
                        confidence=0.35,
                    )
                )

        return out


class MockReviewProvider(ReviewProvider):
    """Deterministic, offline `ReviewProvider` backed by heuristics."""

    name = "mock"

    def review(
        self,
        parsed_diff: ParsedDiff,
        selected_personas: list[ReviewerPersona],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> list[PersonaReview]:
        session = _MockDiffSession(parsed_diff)
        reviews: list[PersonaReview] = []
        for persona in selected_personas:
            findings = session.findings_for(persona)
            reviews.append(
                PersonaReview(
                    persona=persona,
                    risk_level=_persona_risk(findings),
                    summary=_persona_summary(persona, findings),
                    findings=findings,
                )
            )
        return reviews
