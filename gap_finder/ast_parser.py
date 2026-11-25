import ast
from pathlib import Path
from .models import FunctionInfo


def _extract_calls(func_node: ast.AST) -> tuple[list[str], list[str]]:
    """Return (general_calls, self_or_cls_calls) inside a function body."""
    calls: list[str] = []
    self_calls: list[str] = []

    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                calls.append(target.id)
            elif isinstance(target, ast.Attribute):
                if isinstance(target.value, ast.Name) and target.value.id in ("self", "cls"):
                    self_calls.append(target.attr)
                else:
                    calls.append(target.attr)

    return calls, self_calls


def _visit_defs(
    parent: ast.AST,
    prefix: str,
    class_name: str,
    py_file: Path,
    found: list[FunctionInfo],
) -> None:
    """Recursively collect top-level functions, class methods, and nested functions."""
    for child in ast.iter_child_nodes(parent):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qname = f"{prefix}.{child.name}"
            calls, self_calls = _extract_calls(child)
            found.append(
                FunctionInfo(
                    qualified_name=qname,
                    file_path=str(py_file),
                    def_line=child.lineno,
                    body_start=child.body[0].lineno,  # Skip `def` line
                    end_lineno=child.end_lineno or child.lineno,
                    class_name=class_name,
                    calls=calls,
                    self_calls=self_calls,
                )
            )
            _visit_defs(child, qname, "", py_file, found)
        elif isinstance(child, ast.ClassDef):
            cname = f"{prefix}.{child.name}"
            _visit_defs(child, cname, cname, py_file, found)


def parse_file(py_file: Path, module_qualifier: str) -> list[FunctionInfo]:
    """Safely parse a single Python file into FunctionInfo objects."""
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except (SyntaxError, RecursionError, ValueError, OSError):
        return []

    found: list[FunctionInfo] = []
    _visit_defs(tree, module_qualifier, "", py_file, found)
    return found


def parse_repository(repo: Path, ignore_dirs: tuple[str, ...] = (".venv", "venv", "__pycache__", ".git")) -> list[FunctionInfo]:
    """Walk an entire repository and extract all functions."""
    all_functions: list[FunctionInfo] = []

    for py_file in sorted(repo.rglob("*.py")):
        if not py_file.resolve().is_relative_to(repo):
            continue
        if any(part in ignore_dirs for part in py_file.parts):
            continue
        if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
            continue

        rel = py_file.relative_to(repo)
        module_qualifier = str(rel).replace("/", ".").removesuffix(".py")
        all_functions.extend(parse_file(py_file, module_qualifier))

    # Keep the latest definition if overloaded/redefined
    latest = {f.qualified_name: f for f in all_functions}
    return list(latest.values())
