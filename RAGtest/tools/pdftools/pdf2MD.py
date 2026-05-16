from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = SCRIPT_DIR / "input"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"


def configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    lines = [line.strip() for line in text.split("\n")]
    compact: list[str] = []
    previous_blank = False

    for line in lines:
        if not line:
            if not previous_blank:
                compact.append("")
            previous_blank = True
            continue

        compact.append(line)
        previous_blank = False

    return "\n".join(compact).strip()


def safe_stem(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip() or "page"


def convert_pdf_pages_to_markdown(pdf_path: Path, output_dir: Path) -> list[Path]:
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit(
            "PyMuPDF is required. Install it with: pip install pymupdf"
        ) from exc

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Input file must be a PDF: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []
    base_name = safe_stem(pdf_path.stem)

    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = normalize_text(page.get_text("text"))
            md_path = output_dir / f"{base_name}_page_{page_number:03d}.md"
            parts = [
                f"# {pdf_path.stem} - Page {page_number}",
                "",
                f"> Source PDF: `{pdf_path.name}`",
                f"> Page: {page_number} / {document.page_count}",
                "",
                text if text else "_No extractable text found on this page._",
                "",
            ]
            md_path.write_text("\n".join(parts), encoding="utf-8")
            created_files.append(md_path)

    return created_files


def convert_folder(input_dir: Path, output_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in: {input_dir}")
        return []

    all_outputs: list[Path] = []
    for pdf_path in pdf_files:
        outputs = convert_pdf_pages_to_markdown(pdf_path, output_dir)
        all_outputs.extend(outputs)
        print(f"Converted {pdf_path.name}: {len(outputs)} pages")

    return all_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert every PDF in the input folder to per-page Markdown files."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Folder containing PDF files. Defaults to: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder for generated Markdown files. Defaults to: {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    outputs = convert_folder(args.input_dir, args.output_dir)
    print(f"Done. Generated {len(outputs)} Markdown files.")


if __name__ == "__main__":
    main()
