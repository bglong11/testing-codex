#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 2: Fact Extraction and Factsheet Generation
Extracts facts from markdown and generates categorized factsheet

Usage:
    python step2_extract_facts.py <input.md | markdown_directory> <output_dir> [--provider PROVIDER]
    python step2_extract_facts.py markdown_outputs/your_test_20250101_120000.md ./pipeline_test_openai
    python step2_extract_facts.py markdown_outputs/your_test_20250101_120000.md ./pipeline_test_gemini --provider gemini
    python step2_extract_facts.py markdown_outputs/your_test_20250101_120000.md ./pipeline_test_ollama --provider ollama
    python step2_extract_facts.py markdown_outputs ./pipeline_directory_openai --provider openai
    python step2_extract_facts.py ./pipeline_runs/your_project --pipeline-root

Supported providers: openai, ollama, anthropic, gemini
"""

import sys
import io
import os
import json
import re
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from llm_config import ensure_provider_credentials, get_model_for_provider, resolve_provider_for_step

# Configure UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def print_header(title):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def print_step(step_num, title):
    """Print a step header."""
    print(f"\n[{step_num}] {title}")
    print("-" * 80)


def print_success(msg):
    """Print success message."""
    print(f"  ✓ {msg}")


def print_error(msg):
    """Print error message."""
    print(f"  ✗ {msg}")


def print_info(msg):
    """Print info message."""
    print(f"  → {msg}")


PDF_TIMESTAMP_PATTERN = re.compile(r"(?P<pdf_name>.+)_(?P<timestamp>\d{8}_\d{6})$")


def extract_pdf_metadata_from_markdown(markdown_path: Path) -> tuple[str, str]:
    """Return the original PDF stem and markdown timestamp derived from the markdown filename."""
    stem = markdown_path.stem
    match = PDF_TIMESTAMP_PATTERN.match(stem)
    if match:
        return match.group("pdf_name"), match.group("timestamp")
    return stem, ""


def parse_arguments():
    """Parse command-line arguments using argparse."""

    parser = argparse.ArgumentParser(
        description="Step 2: Fact Extraction and Factsheet Generation.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python %(prog)s markdown_outputs/your_test.md ./pipeline_test_openai
  python %(prog)s markdown_outputs/your_test.md ./pipeline_test_gemini --provider gemini
  python %(prog)s markdown_outputs/your_test.md ./pipeline_test_ollama --provider ollama
  python %(prog)s ./pipeline_runs/your_project --pipeline-root
  python %(prog)s markdown_outputs/your_test.md ./pipeline_test_openai --provider openai
        """
    )

    parser.add_argument(
        "markdown_path",
        type=Path,
        nargs="?",
        help="Path to a markdown file produced by Step 1."
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        help="Directory to save the output files."
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "ollama", "anthropic", "gemini"],
        help="Override the LLM provider specified in the .env file."
    )
    parser.add_argument(
        "--pipeline-root",
        type=Path,
        help="Pipeline run directory that contains the markdown and will host step2_output."
    )

    return parser.parse_args()



def main():
    """Run fact extraction and factsheet generation."""

    print_header("STEP 2: FACT EXTRACTION & FACTSHEET GENERATION")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load .env file first and prefer values defined there over any pre-existing env vars
    load_dotenv(override=True)

    # Parse command-line arguments
    args = parse_arguments()
    pipeline_root = args.pipeline_root
    markdown_path = args.markdown_path
    output_dir = args.output_dir
    provider = args.provider

    if pipeline_root:
        pipeline_root = pipeline_root.resolve()
        if not pipeline_root.exists():
            print_error(f"Pipeline root not found: {pipeline_root}")
            return False

        markdown_candidates = sorted(
            [p for p in pipeline_root.glob("*.md") if p.is_file()],
            key=lambda p: p.stat().st_mtime
        )
        if not markdown_candidates and not markdown_path:
            print_error(f"No markdown files (*.md) found in {pipeline_root}")
            return False

        if not markdown_path:
            markdown_path = markdown_candidates[-1]
        if len(markdown_candidates) > 1:
            print_info(f"Multiple markdown files detected; using latest: {markdown_path.name}")
        if not output_dir:
            output_dir = pipeline_root / "step2_output"
        print_info(f"Pipeline root mode: markdown={markdown_path}, output={output_dir}")
    else:
        if not markdown_path or not output_dir:
            print_error("Markdown path and output directory must be provided when --pipeline-root is not used.")
            return False

    try:
        llm_provider = resolve_provider_for_step("step2", provider)
    except ValueError as exc:
        print_error(str(exc))
        return False

    if markdown_path:
        markdown_path = markdown_path.resolve()

    try:
        ensure_provider_credentials(llm_provider)
    except ValueError as exc:
        print_error(str(exc))
        return False

    if provider:
        print_success(f"LLM Provider override for Step 2: {llm_provider.upper()}")

    if not markdown_path.exists():
        print_error(f"Markdown path not found: {markdown_path}")
        return False

    if markdown_path.is_dir():
        markdown_files = sorted(
            [p for p in markdown_path.glob("*.md") if p.is_file()]
        )
        if not markdown_files:
            print_error(f"No markdown files (*.md) found in {markdown_path}")
            return False
        print_success(f"Found {len(markdown_files)} markdown files in {markdown_path}")
        for md_file in markdown_files:
            print_info(f"  {md_file} ({md_file.stat().st_size / 1024:.1f} KB)")
    else:
        markdown_files = [markdown_path]
        print_success(f"Found markdown: {markdown_path}")
        print_info(f"File size: {markdown_path.stat().st_size / 1024:.1f} KB")

    total_markdown_size = sum(f.stat().st_size for f in markdown_files)
    single_input_mode = len(markdown_files) == 1

    # ========================================================================
    # PHASE 1: CREATE OUTPUT DIRECTORY
    # ========================================================================

    print_step(1, "CREATING OUTPUT DIRECTORY")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print_success(f"Output directory ready: {output_dir.absolute()}")
    except Exception as e:
        print_error(f"Failed to create output directory: {e}")
        return False

    # ========================================================================
    # PHASE 2: FACT EXTRACTION & FACTSHEET GENERATION
    # ========================================================================

    print_step(2, "EXTRACTING FACTS & GENERATING FACTSHEET")

    llm_model = get_model_for_provider(llm_provider)
    print_info(f"LLM Provider: {llm_provider.upper()} ({llm_model})")
    if single_input_mode:
        print_info(f"Input Markdown: {markdown_files[0]}")
    else:
        print_info(f"Input Markdown Directory: {markdown_path} ({len(markdown_files)} files)")
    print_info(f"Output Directory: {output_dir}")
    print_info(f"\nStarting esia_extractor.py...")

    env = os.environ.copy()
    env["LLM_PROVIDER"] = llm_provider
    if llm_provider == "ollama":
        env.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

    processed_output_dirs = []

    try:
        for idx, markdown_file in enumerate(markdown_files, start=1):
            doc_output_dir = output_dir if single_input_mode else output_dir / markdown_file.stem
            doc_output_dir.mkdir(parents=True, exist_ok=True)
            pdf_name, markdown_timestamp = extract_pdf_metadata_from_markdown(markdown_file)
            metadata_path = doc_output_dir / "pipeline_metadata.json"
            metadata = {
                "source_markdown": str(markdown_file.resolve()),
                "source_pdf_name": pdf_name,
                "markdown_timestamp": markdown_timestamp,
                "generated_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
            }
            try:
                with open(metadata_path, "w", encoding="utf-8") as metadata_file:
                    json.dump(metadata, metadata_file, ensure_ascii=False, indent=2)
            except Exception as exc:
                print_error(f"Failed to write metadata for {markdown_file.name}: {exc}")
                return False
            print_info(f"\nProcessing file {idx}/{len(markdown_files)}: {markdown_file.name}")
            print_info(f"  Destination: {doc_output_dir}")

            result = subprocess.run(
                [sys.executable, "esia_extractor.py", str(markdown_file), str(doc_output_dir)],
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
                env=env  # Pass environment variables including LLM_PROVIDER
            )

            print(result.stdout)

            if result.returncode != 0:
                print_error(f"Extraction failed for {markdown_file} with return code {result.returncode}")
                if result.stderr:
                    print(f"STDERR:\n{result.stderr}")
                return False

            processed_output_dirs.append(doc_output_dir)

        print_success("Fact extraction and factsheet generation completed")

    except subprocess.TimeoutExpired:
        print_error("Extraction timeout (exceeded 30 minutes)")
        print_info("The document is very large or the LLM provider is slow.")
        print_info("Consider using a local LLM (Ollama) or splitting the document.")
        return False
    except Exception as e:
        print_error(f"Subprocess execution failed: {e}")
        return False

    # ========================================================================
    # PHASE 3: VERIFY OUTPUT FILES
    # ========================================================================

    def verify_output_files(output_dir_path: Path):
        expected_files = [
            "esia_mentions.csv",
            "esia_consolidated.csv",
            "esia_replacement_plan.csv",
            "project_factsheet.csv"
        ]

        all_exist = True
        file_sizes = {}

        for filename in expected_files:
            filepath = output_dir_path / filename
            if filepath.exists() and filepath.stat().st_size > 10:
                size = filepath.stat().st_size
                file_sizes[filename] = size
                print_success(f"{filename} ({size / 1024:.1f} KB)")
            else:
                if not filepath.exists():
                    print_error(f"{filename} NOT FOUND")
                else:
                    print_error(f"{filename} is empty or invalid (size: {filepath.stat().st_size} bytes)")
                all_exist = False

        if not all_exist:
            print_info(f"\nOutput directory contents ({output_dir_path}):")
            for f in sorted(output_dir_path.glob("*")):
                print_info(f"  {f.name} ({f.stat().st_size / 1024:.1f} KB)")

        return all_exist, file_sizes

    print_step(3, "VERIFYING OUTPUT FILES")

    file_size_records = []
    overall_verified = True

    for doc_output_dir in processed_output_dirs:
        print_info(f"\nVerifying outputs in {doc_output_dir}")
        verified, sizes = verify_output_files(doc_output_dir)
        file_size_records.append((doc_output_dir, sizes))
        if not verified:
            overall_verified = False

    if not overall_verified:
        return False

    # ========================================================================
    # PHASE 4: GENERATE SUMMARY REPORT
    # ========================================================================

    print_step(4, "SUMMARY REPORT")

    print("\nPipeline Statistics:")
    print(f"  Markdown Inputs:          {len(markdown_files)} file(s)")
    print(f"  Markdown Input Size:      {total_markdown_size / 1024:.1f} KB")

    facts_count_total = 0
    factsheets_found = 0
    for doc_output_dir, _ in file_size_records:
        factsheet_path = doc_output_dir / "project_factsheet.csv"
        try:
            with open(factsheet_path, "r", encoding="utf-8") as f:
                factsheet_lines = len(f.readlines())
            facts_count_total += max(0, factsheet_lines - 1)
            factsheets_found += 1
        except Exception:
            pass

    if factsheets_found:
        print(f"  Facts Extracted:          {facts_count_total}")
    else:
        print(f"  Facts Extracted:          (see CSV files)")

    print("\nOutput Files Generated:")
    total_size = 0
    for doc_output_dir, sizes in file_size_records:
        for filename, size in sizes.items():
            label = filename if single_input_mode else f"{doc_output_dir.name}/{filename}"
            print(f"  {label:45} {size / 1024:8.1f} KB")
            total_size += size
    print(f"  {'TOTAL':45} {total_size / 1024:8.1f} KB")

    # ========================================================================
    # FINAL STATUS
    # ========================================================================

    print_header("STEP 2 COMPLETE")
    print(f"Status: SUCCESS\n")
    print(f"Output Location: {output_dir.absolute()}")
    if not single_input_mode:
        print("Generated directories:")
        for doc_output_dir in processed_output_dirs:
            print(f"  {doc_output_dir}")
    print("\nNext Step:")
    if single_input_mode:
        print("  Run the analysis script to generate a prioritized verification report.")
        print(f"  python step3_analyze_facts.py \"{processed_output_dirs[0].absolute()}\"")
    else:
        print("  Run the analysis script for each output directory:")
        for doc_output_dir in processed_output_dirs:
            print(f"  python step3_analyze_facts.py \"{doc_output_dir.absolute()}\"")
    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nFact extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
