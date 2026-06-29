import argparse
import json
from pathlib import Path

from transformer import (
    merge_partials,
    parse_ats_json,
    parse_recruiter_csv,
    parse_recruiter_notes,
    project_profile,
    profile_to_default_output,
)


def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        raise RuntimeError(f"Failed to load config {path}: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description="Candidate profile transformer CLI")
    parser.add_argument("--csv", help="Path to recruiter CSV export")
    parser.add_argument("--ats", help="Path to ATS JSON file")
    parser.add_argument("--notes", help="Path to recruiter notes TXT file")
    parser.add_argument("--config", help="Path to projection config JSON")
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument("--print", action="store_true", help="Print output to stdout")
    args = parser.parse_args()

    source_records = []
    if args.csv:
        source_records.append(parse_recruiter_csv(args.csv))
    if args.ats:
        source_records.append(parse_ats_json(args.ats))
    if args.notes:
        source_records.append(parse_recruiter_notes(args.notes))

    if not source_records:
        raise SystemExit("No input sources provided. Add --csv, --ats, or --notes.")

    canonical = merge_partials(source_records)

    if args.config:
        config = load_config(args.config)
        output = project_profile(canonical, config)
    else:
        output = profile_to_default_output(canonical)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(output, handle, indent=2)

    if args.print or not args.output:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
