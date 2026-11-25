from dataclasses import asdict
from mcp.server.fastmcp import FastMCP
from .graph_builder import analyze_repository

mcp = FastMCP("Gap-Finder")


@mcp.tool()
def get_active_coverage_gaps(repo_path: str = ".", coverage_file: str = "coverage.json") -> list[dict]:
    """
    Scan a Python repository's call graph and coverage report to find functions
    with untested lines that are called by other functions in the codebase.
    """
    gaps = analyze_repository(repo_path, coverage_file)
    return [asdict(g) for g in gaps]


if __name__ == "__main__":
    mcp.run()
