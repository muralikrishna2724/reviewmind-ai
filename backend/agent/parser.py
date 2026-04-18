"""Code parser using libcst to extract structure and detect patterns.

Detects:
- Mutable default arguments (e.g. def f(x=[]) or def f(x={}))
- Async functions missing try/except around await calls
- Direct ORM usage in route handlers (db.query(...))
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    import libcst as cst

    _LIBCST_AVAILABLE = True
except ImportError:
    _LIBCST_AVAILABLE = False


@dataclass
class ParsedCode:
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    detected_patterns: list[str] = field(default_factory=list)
    raw_diff: str = ""


# ── libcst visitors ──────────────────────────────────────────────────────────

if _LIBCST_AVAILABLE:

    class _PatternVisitor(cst.CSTVisitor):
        """Walks the CST and collects function names and detected patterns."""

        def __init__(self) -> None:
            self.functions: list[str] = []
            self.classes: list[str] = []
            self.patterns: list[str] = []
            self._in_async_func: bool = False
            self._async_has_try: bool = False
            self._async_func_name: str = ""

        # ── functions ────────────────────────────────────────────────────────

        def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
            name = node.name.value
            self.functions.append(name)

            # Check for mutable default arguments
            for param in node.params.params:
                if param.default is not None:
                    if isinstance(param.default, (cst.List, cst.Dict, cst.Set)):
                        self.patterns.append(
                            f"mutable-default-arg: parameter '{param.name.value}' "
                            f"in function '{name}' uses a mutable default value"
                        )

            # Track async functions for try/except check
            if node.asynchronous is not None:
                self._in_async_func = True
                self._async_has_try = False
                self._async_func_name = name
            return None

        def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
            if original_node.asynchronous is not None:
                if not self._async_has_try:
                    self.patterns.append(
                        f"missing-try-except-async: async function "
                        f"'{self._async_func_name}' does not wrap await calls in try/except"
                    )
                self._in_async_func = False

        def visit_Try(self, node: cst.Try) -> bool | None:
            if self._in_async_func:
                self._async_has_try = True
            return None

        # ── classes ──────────────────────────────────────────────────────────

        def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
            self.classes.append(node.name.value)
            return None

        # ── ORM detection ────────────────────────────────────────────────────

        def visit_Attribute(self, node: cst.Attribute) -> bool | None:
            # Detect db.query(...) pattern
            if (
                isinstance(node.value, cst.Name)
                and node.value.value == "db"
                and node.attr.value == "query"
            ):
                self.patterns.append(
                    "direct-orm-query: direct ORM query via db.query() detected in route handler — "
                    "use the repository layer instead"
                )
            return None


# ── public API ───────────────────────────────────────────────────────────────


def parse_code(raw: str) -> ParsedCode:
    """Parse raw Python code and return extracted structure + detected patterns.

    Falls back to regex-based detection if libcst is unavailable or parsing fails.
    """
    result = ParsedCode(raw_diff=raw)

    if _LIBCST_AVAILABLE:
        try:
            tree = cst.parse_module(raw)
            visitor = _PatternVisitor()
            tree.visit(visitor)
            result.functions = visitor.functions
            result.classes = visitor.classes
            result.detected_patterns = visitor.patterns
            return result
        except Exception:
            pass  # fall through to regex fallback

    # ── regex fallback ───────────────────────────────────────────────────────
    result.functions = re.findall(r"def\s+(\w+)\s*\(", raw)
    result.classes = re.findall(r"class\s+(\w+)", raw)

    patterns: list[str] = []

    # Mutable default args
    for m in re.finditer(r"def\s+(\w+)\s*\([^)]*=\s*(\[\]|\{\}|\[\s*\]|\{\s*\})", raw):
        patterns.append(
            f"mutable-default-arg: function '{m.group(1)}' uses a mutable default argument"
        )

    # Async missing try/except (simple heuristic)
    async_funcs = re.findall(r"async\s+def\s+(\w+)", raw)
    for fn in async_funcs:
        # Find the function body and check for try:
        fn_pattern = rf"async\s+def\s+{re.escape(fn)}.*?(?=\nasync\s+def|\ndef\s|\Z)"
        fn_match = re.search(fn_pattern, raw, re.DOTALL)
        if fn_match and "try:" not in fn_match.group(0):
            patterns.append(
                f"missing-try-except-async: async function '{fn}' does not wrap await calls in try/except"
            )

    # Direct ORM
    if re.search(r"\bdb\.query\s*\(", raw):
        patterns.append(
            "direct-orm-query: direct ORM query via db.query() detected — use the repository layer instead"
        )

    result.detected_patterns = patterns
    return result
