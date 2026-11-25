from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    qualified_name: str
    file_path: str
    def_line: int
    body_start: int
    end_lineno: int
    class_name: str = ""
    calls: list[str] = field(default_factory=list)
    self_calls: list[str] = field(default_factory=list)


@dataclass
class CoverageGap:
    qualified_name: str
    file_path: str
    untested_lines: int
    total_lines: int
    missing_line_numbers: list[int]
    caller_count: int
    callers: list[str]
