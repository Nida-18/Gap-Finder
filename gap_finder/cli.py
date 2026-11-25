import argparse
from .graph_builder import analyze_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="Find actively called functions with untested lines.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to target repository")
    parser.add_argument("--coverage", default="coverage.json", help="Path to coverage.json file")
    args = parser.parse_args()

    gaps = analyze_repository(args.repo, args.coverage)
    if not gaps:
        print("No untested active functions found.")
        return

    print(f"Found {len(gaps)} active functions with coverage gaps:\n")
    for g in gaps:
        print(
            f"- {g.qualified_name} ({g.file_path})\n"
            f"  Untested: {g.untested_lines}/{g.total_lines} lines {g.missing_line_numbers}\n"
            f"  Called by ({g.caller_count}): {', '.join(g.callers)}\n"
        )


if __name__ == "__main__":
    main()
