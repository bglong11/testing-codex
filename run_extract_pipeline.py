#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_extract_pipeline.py

Convenience wrapper that executes Step 1 → Step 2 → Step 3 of the ESIA pipeline in order.
Only a source PDF is required; all derived directories and filenames are based on the PDF name
and a shared timestamp so the generated markdown, CSVs, and verification report stay grouped.

By default Step 2/3 inherit the LLM configuration found in `.env` (and overrides such as
`LLM_PROVIDER_STEP2`). Use `--step2-provider`/`--step3-provider` to override when needed.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from step1_pdf_to_markdown import convert_pdf_to_markdown


def print_header(title: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}\n")


def sanitize_name(name: str) -> str:
    """Create a filesystem-friendly version of the PDF stem."""
    sanitized = re.sub(r"[^\w\-]+", "_", name.strip())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "document"


def prepare_clean_pdf(pdf_path: Path, dest_dir: Path) -> Path:
    """Copy/rename the original PDF into the destination directory with a clean name."""
    clean_stem = sanitize_name(pdf_path.stem)
    suffix = pdf_path.suffix.lower()
    clean_pdf_name = f"{clean_stem}{suffix}"
    clean_pdf_path = dest_dir / clean_pdf_name
    if clean_pdf_path.exists():
        return clean_pdf_path
    shutil.copy2(pdf_path, clean_pdf_path)
    return clean_pdf_path


def run_command(cmd: list[str], stage: str) -> None:
    """Execute a subprocess and raise if it fails."""
    print(f"\n→ {stage}: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{stage} failed (exit code {result.returncode})")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full ESIA extraction+analysis pipeline for a single PDF."
    )
    parser.add_argument("pdf_path", type=Path, help="Path to the PDF to process.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("pipeline_runs"),
        help="Root directory where the pipeline folders will be created.",
    )
    parser.add_argument(
        "--step2-provider",
        type=str,
        choices=["openai", "ollama", "anthropic", "gemini"],
        help="Override the provider used for Step 2 (fact extraction).",
    )
    parser.add_argument(
        "--step3-provider",
        type=str,
        choices=["openai", "ollama", "anthropic", "gemini"],
        help="Override the provider used for Step 3 (fact analysis).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    pdf_path = args.pdf_path

    if not pdf_path.exists():
        print(f"✗ PDF not found: {pdf_path}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_stem = sanitize_name(pdf_path.stem)
    pipeline_root = args.output_root / pdf_stem
    if pipeline_root.exists():
        pipeline_root = args.output_root / f"{pdf_stem}_{timestamp}"
    pipeline_root.mkdir(parents=True, exist_ok=True)

    print_header("RUNNING ESIA PIPELINE")
    print(f"PDF Source: {pdf_path}")
    print(f"Pipeline Root: {pipeline_root}")
    print(f"Clean Stem: {pdf_stem}")

    markdown_dir = pipeline_root
    try:
        clean_pdf_path = prepare_clean_pdf(pdf_path, pipeline_root)
        print(f"Clean PDF copied to: {clean_pdf_path}")
        markdown_path, _ = convert_pdf_to_markdown(clean_pdf_path, markdown_dir=markdown_dir)
        target_markdown = pipeline_root / f"{pdf_stem}_{timestamp}.md"
        if markdown_path != target_markdown:
            markdown_path.replace(target_markdown)
            markdown_path = target_markdown
    except Exception as exc:
        print(f"✗ Step 1 failed: {exc}")
        sys.exit(1)

    step2_output = pipeline_root / "step2_output"
    step2_output.mkdir(parents=True, exist_ok=True)
    step2_cmd = [
        sys.executable,
        "step2_extract_facts.py",
        "--pipeline-root",
        str(pipeline_root),
    ]
    if args.step2_provider:
        step2_cmd.extend(["--provider", args.step2_provider])

    try:
        run_command(step2_cmd, "Step 2 (Fact Extraction)")
    except RuntimeError as exc:
        print(f"✗ {exc}")
        sys.exit(1)

    step3_cmd = [
        sys.executable,
        "step3_analyze_facts.py",
        str(step2_output),
        "--pipeline-root",
        str(pipeline_root),
    ]
    if args.step3_provider:
        step3_cmd.extend(["--provider", args.step3_provider])

    try:
        run_command(step3_cmd, "Step 3 (Fact Analysis)")
    except RuntimeError as exc:
        print(f"✗ {exc}")
        sys.exit(1)

    print_header("PIPELINE COMPLETE")
    print(f" Pipeline root: {pipeline_root}")
    print(f"  • PDF:      {clean_pdf_path.name}")
    print(f"  • Markdown: {markdown_path.name}")
    print(f" Step 2 Outputs:  {step2_output}")
    print(" Step 3 Report:  located inside the Step 2 output directory with the new naming convention.")


if __name__ == "__main__":
    main()
