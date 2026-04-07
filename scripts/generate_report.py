#!/usr/bin/env python3
"""Generate analysis report for a subject.

Usage:
    # From existing analysis results
    python scripts/generate_report.py sub-bfa00d26

    # Run fresh analysis on real data and generate report
    python scripts/generate_report.py --analyze data/sample/sub-01/anat/sub-01_T1w_real.nii.gz --age 60 --sex M

    # With FLAIR
    python scripts/generate_report.py --analyze data/sample/sub-01/anat/sub-01_T1w_real.nii.gz \
        --flair data/sample/sub-01/anat/sub-01_FLAIR.nii.gz --age 60 --sex M
"""

import json
import sys
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Synapse-D analysis report")
    parser.add_argument("subject_id", nargs="?", help="Existing subject ID")
    parser.add_argument("--analyze", help="T1w NIfTI path for fresh analysis")
    parser.add_argument("--flair", help="FLAIR NIfTI path")
    parser.add_argument("--swi", help="SWI NIfTI path")
    parser.add_argument("--age", type=float, help="Chronological age")
    parser.add_argument("--sex", default="M", help="Sex (M/F)")
    parser.add_argument("--output", help="Output HTML path")
    parser.add_argument("--open", action="store_true", default=True, help="Open in browser")
    args = parser.parse_args()

    if args.analyze:
        # Run fresh analysis
        print("Running analysis pipeline...")
        from synapse_d.api.tasks import run_pipeline

        t1 = Path(args.analyze)
        flair = Path(args.flair) if args.flair else None
        swi = Path(args.swi) if args.swi else None

        result = run_pipeline(t1, args.age, args.sex, flair, swi)
        subject_id = result.get("subject_id", t1.name.split("_")[0])

    elif args.subject_id:
        # Load existing results
        subject_id = args.subject_id
        from synapse_d.config import settings
        result_file = settings.output_dir / subject_id / "latest_result.json"
        if result_file.exists():
            result = json.loads(result_file.read_text())
        else:
            print(f"No results found for {subject_id}")
            print(f"Run: python scripts/generate_report.py --analyze <t1_path> --age <age>")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # Generate report
    from synapse_d.report.generator import generate_report

    html = generate_report(result, subject_id)

    # Save
    output = args.output or f"reports/{subject_id}_report.html"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print(f"\nReport generated: {output_path}")
    print(f"Size: {len(html) / 1024:.1f} KB")

    if args.open:
        webbrowser.open(f"file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
