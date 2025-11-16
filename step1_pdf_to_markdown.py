#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 1: PDF to Markdown Conversion using Docling
Converts PDF documents to markdown format and saves to markdown_outputs/ directory

Usage:
    python step1_pdf_to_markdown.py <input.pdf>
    python step1_pdf_to_markdown.py saas/backend/your_test.pdf
    python step1_pdf_to_markdown.py input.pdf --provider openai
    python step1_pdf_to_markdown.py input.pdf --output-dir pipeline_runs/my_esia_project
"""

import sys
import io
import os
import argparse
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from llm_config import SUPPORTED_PROVIDERS, resolve_provider_for_step

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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a PDF to markdown outputs for the ESIA pipeline.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("pdf_path", type=Path, help="Path to the PDF that needs conversion.")
    parser.add_argument(
        "--provider",
        type=str,
        choices=list(SUPPORTED_PROVIDERS),
        help="Optional LLM provider label for this step (default is read from LLM_PROVIDER or ollama).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("markdown_outputs"),
        help="Directory to write converted markdown (default: markdown_outputs/).",
    )

    return parser.parse_args()


def convert_pdf_to_markdown(pdf_path: Path, markdown_dir: Path | str = Path("markdown_outputs")) -> tuple[Path, str]:
    """Converts a PDF file to markdown and returns the path plus the generated text."""

    markdown_dir = Path(markdown_dir)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    print_info("Initializing DocumentConverter...")
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()

    print_info(f"Converting PDF: {pdf_path}")
    with tqdm(total=100, desc="  Converting", unit="%", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}%", leave=False) as pbar:
        result = converter.convert(str(pdf_path))
        pbar.update(70)

        print_info("Exporting to markdown...")
        markdown_text = result.document.export_to_markdown()
        pbar.update(30)

    markdown_filename = generate_unique_markdown_filename(pdf_path)
    markdown_path = markdown_dir / markdown_filename

    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return markdown_path, markdown_text


def generate_unique_markdown_filename(pdf_path):
    """Generate unique markdown filename from PDF name and timestamp."""
    pdf_name = Path(pdf_path).stem  # Get filename without extension
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{pdf_name}_{timestamp}.md"


def main():
    """Run PDF to Markdown conversion."""

    print_header("STEP 1: PDF TO MARKDOWN CONVERSION (Docling)")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    args = parse_arguments()
    pdf_path = args.pdf_path
    provider_override = args.provider

    try:
        llm_provider = resolve_provider_for_step("step1", provider_override)
    except ValueError as exc:
        print_error(str(exc))
        return False

    print_info(f"LLM Provider for Step 1 pipeline metadata: {llm_provider.upper()}")

    # Check if PDF exists
    if not pdf_path.exists():
        print_error(f"PDF file not found: {pdf_path}")
        return False

    print_success(f"Found PDF: {pdf_path} ({pdf_path.stat().st_size / 1024:.1f} KB)")

    # ========================================================================
    # PHASE 1: CREATE MARKDOWN_OUTPUTS DIRECTORY
    # ========================================================================

    print_step(1, "CREATING MARKDOWN_OUTPUTS DIRECTORY")

    markdown_dir = Path("markdown_outputs")
    try:
        markdown_dir.mkdir(parents=True, exist_ok=True)
        print_success(f"Markdown directory ready: {markdown_dir.absolute()}")
    except Exception as e:
        print_error(f"Failed to create markdown directory: {e}")
        return False

    # ========================================================================
    # PHASE 2: DOCLING CONVERSION (PDF → Markdown)
    # ========================================================================

    print_step(2, "DOCLING PDF TO MARKDOWN CONVERSION")

    output_dir = args.output_dir
    try:
        markdown_path, markdown_text = convert_pdf_to_markdown(pdf_path, markdown_dir=output_dir)
        doc_byte_size = len(markdown_text.encode('utf-8'))
        doc_lines = len(markdown_text.split('\n'))

        print_success(f"Markdown generated: {markdown_path}")
        print(f"    Size: {doc_byte_size / 1024:.1f} KB")
        print(f"    Lines: {doc_lines:,}")
        print(f"    Characters: {len(markdown_text):,}")

    except ImportError as e:
        print_error(f"Docling import failed: {e}")
        print_info("Install with: pip install docling")
        return False
    except Exception as e:
        print_error(f"PDF conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # FINAL STATUS
    # ========================================================================

    print_header("STEP 1 COMPLETE")
    print(f"Status: SUCCESS\n")
    print(f"Output File: {markdown_path.absolute()}\n")
    print(f"Next Step:")
    print(f"  python step2_extract_facts.py {markdown_path}\n")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nPDF conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
