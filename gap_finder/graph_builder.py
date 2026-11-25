from pathlib import Path
from .ast_parser import parse_repository
from .coverage_reader import compute_function_coverage, load_coverage_report
from .models import CoverageGap, FunctionInfo


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def build_call_graph(functions: list[FunctionInfo]) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    """
    Build directed edges (caller -> callee) and a reverse map of {callee: [callers]}.
    """
    by_qname = {f.qualified_name: f for f in functions}
    by_short_name: dict[str, list[FunctionInfo]] = {}
    for f in functions:
        short = f.qualified_name.rsplit(".", 1)[-1]
        by_short_name.setdefault(short, []).append(f)

    edges: list[tuple[str, str]] = []
    callers_map: dict[str, list[str]] = {f.qualified_name: [] for f in functions}

    for f in functions:
        targets: set[str] = set()

        for name in set(f.self_calls):
            own_method = f"{f.class_name}.{name}"
            if f.class_name and own_method in by_qname:
                targets.add(own_method)
            elif not _is_dunder(name):
                targets.update(t.qualified_name for t in by_short_name.get(name, []))

        for name in set(f.calls):
            if not _is_dunder(name):
                targets.update(t.qualified_name for t in by_short_name.get(name, []))

        targets.discard(f.qualified_name)  # Ignore direct self-recursion

        for target in sorted(targets):
            edges.append((f.qualified_name, target))
            callers_map[target].append(f.qualified_name)

    return edges, callers_map


def analyze_repository(repo_path: str, coverage_file: str = "coverage.json") -> list[CoverageGap]:
    """Find functions that have untested lines AND are actively called by other code."""
    repo = Path(repo_path).resolve()
    cov_path = Path(coverage_file)
    if not cov_path.is_absolute():
        cov_path = repo / cov_path

    functions = parse_repository(repo)
    coverage_data = load_coverage_report(cov_path)
    _, callers_map = build_call_graph(functions)

    gaps: list[CoverageGap] = []
    for f in functions:
        callers = callers_map.get(f.qualified_name, [])
        if not callers:
            continue  # Skip dead/uncalled functions

        untested_count, total_lines, missing_lines = compute_function_coverage(f, repo, coverage_data)
        if untested_count > 0:
            rel_path = str(Path(f.file_path).relative_to(repo))
            gaps.append(
                CoverageGap(
                    qualified_name=f.qualified_name,
                    file_path=rel_path,
                    untested_lines=untested_count,
                    total_lines=total_lines,
                    missing_line_numbers=missing_lines,
                    caller_count=len(callers),
                    callers=callers,
                )
            )

    # Sort by highest caller count first, then by most untested lines
    gaps.sort(key=lambda g: (g.caller_count, g.untested_lines), reverse=True)
    return gaps
