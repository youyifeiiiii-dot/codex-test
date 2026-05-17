from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections.abc import Iterable
from xml.etree import ElementTree
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
CONFIG_PATH = PROJECT_ROOT / "rag_config.json"
DEFAULT_INPUT_DIR = SCRIPT_DIR / "input"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"
MANIFEST_NAME = ".pdf2md_manifest.json"
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".log",
}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl", ".log"}
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PPT_NAMESPACE = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def load_config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def configured_path(config: dict[str, str], key: str, fallback: Path) -> Path:
    value = config.get(key)
    return Path(value) if value else fallback


def load_manifest(output_dir: Path) -> dict[str, dict[str, object]]:
    manifest_path = output_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(output_dir: Path, manifest: dict[str, dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def write_markdown_file(
    output_dir: Path,
    source_path: Path,
    title: str,
    body: str,
    suffix: str = "",
    metadata: Iterable[str] = (),
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = safe_stem(source_path.stem)
    suffix_part = f"_{suffix}" if suffix else ""
    md_path = output_dir / f"{base_name}{suffix_part}.md"
    normalized_body = normalize_text(body)
    parts = [
        f"# {title}",
        "",
        f"> Source file: `{source_path.name}`",
        *metadata,
        "",
        normalized_body if normalized_body else "_No extractable text found._",
        "",
    ]
    md_path.write_text("\n".join(parts), encoding="utf-8")
    return md_path


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


def iter_docx_pages(docx_path: Path) -> Iterable[str]:
    with zipfile.ZipFile(docx_path) as archive:
        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as exc:
            raise ValueError(f"Invalid DOCX file: {docx_path}") from exc

    root = ElementTree.fromstring(document_xml)
    current_page: list[str] = []

    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        paragraph_text: list[str] = []

        for node in paragraph.iter():
            tag_name = node.tag.rsplit("}", 1)[-1]
            if tag_name == "t" and node.text:
                paragraph_text.append(node.text)
            elif tag_name == "tab":
                paragraph_text.append("\t")
            elif tag_name == "br":
                if node.attrib.get(f"{{{WORD_NAMESPACE['w']}}}type") == "page":
                    text = "".join(paragraph_text).strip()
                    if text:
                        current_page.append(text)
                    yield "\n\n".join(current_page)
                    current_page = []
                    paragraph_text = []
                else:
                    paragraph_text.append("\n")
            elif tag_name == "lastRenderedPageBreak":
                text = "".join(paragraph_text).strip()
                if text:
                    current_page.append(text)
                yield "\n\n".join(current_page)
                current_page = []
                paragraph_text = []

        text = "".join(paragraph_text).strip()
        if text:
            current_page.append(text)

    if current_page:
        yield "\n\n".join(current_page)


def convert_docx_to_markdown(docx_path: Path, output_dir: Path) -> list[Path]:
    pages = list(iter_docx_pages(docx_path)) or [""]
    created_files: list[Path] = []

    for page_number, text in enumerate(pages, start=1):
        md_path = write_markdown_file(
            output_dir,
            docx_path,
            f"{docx_path.stem} - Page {page_number}",
            text,
            suffix=f"page_{page_number:03d}",
            metadata=(
                f"> Type: Word document",
                f"> Page: {page_number} / {len(pages)}",
            ),
        )
        created_files.append(md_path)

    return created_files


def slide_sort_key(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def extract_pptx_slide_text(archive: zipfile.ZipFile, slide_name: str) -> str:
    root = ElementTree.fromstring(archive.read(slide_name))
    text_parts = [
        node.text or ""
        for node in root.findall(".//a:t", PPT_NAMESPACE)
        if node.text
    ]
    return normalize_text("\n".join(text_parts))


def convert_pptx_to_markdown(pptx_path: Path, output_dir: Path) -> list[Path]:
    created_files: list[Path] = []

    with zipfile.ZipFile(pptx_path) as archive:
        slide_names = sorted(
            (
                name
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ),
            key=slide_sort_key,
        )
        if not slide_names:
            raise ValueError(f"Invalid PPTX file: {pptx_path}")

        for index, slide_name in enumerate(slide_names, start=1):
            text = extract_pptx_slide_text(archive, slide_name)
            md_path = write_markdown_file(
                output_dir,
                pptx_path,
                f"{pptx_path.stem} - Slide {index}",
                text,
                suffix=f"slide_{index:03d}",
                metadata=(f"> Slide: {index} / {len(slide_names)}",),
            )
            created_files.append(md_path)

    return created_files


def read_text_file(text_path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return text_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return text_path.read_text(encoding="utf-8", errors="replace")


def convert_text_to_markdown(text_path: Path, output_dir: Path) -> list[Path]:
    md_path = write_markdown_file(
        output_dir,
        text_path,
        text_path.stem,
        read_text_file(text_path),
        metadata=(f"> Type: Text file",),
    )
    return [md_path]


def convert_file_to_markdown(input_path: Path, output_dir: Path) -> list[Path]:
    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        return convert_pdf_pages_to_markdown(input_path, output_dir)
    if suffix == ".docx":
        return convert_docx_to_markdown(input_path, output_dir)
    if suffix == ".pptx":
        return convert_pptx_to_markdown(input_path, output_dir)
    if suffix in TEXT_EXTENSIONS:
        return convert_text_to_markdown(input_path, output_dir)
    raise ValueError(f"Unsupported file type: {input_path}")


def expected_output_names(input_path: Path) -> list[str]:
    suffix = input_path.suffix.lower()
    base_name = safe_stem(input_path.stem)

    if suffix == ".pdf":
        try:
            import fitz
        except ImportError as exc:
            raise SystemExit(
                "PyMuPDF is required. Install it with: pip install pymupdf"
            ) from exc

        with fitz.open(input_path) as document:
            return [
                f"{base_name}_page_{page_number:03d}.md"
                for page_number in range(1, document.page_count + 1)
            ]

    if suffix == ".docx":
        page_count = len(list(iter_docx_pages(input_path))) or 1
        return [
            f"{base_name}_page_{page_number:03d}.md"
            for page_number in range(1, page_count + 1)
        ]

    if suffix == ".pptx":
        with zipfile.ZipFile(input_path) as archive:
            slide_count = len(
                [
                    name
                    for name in archive.namelist()
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                ]
            )
        return [
            f"{base_name}_slide_{slide_number:03d}.md"
            for slide_number in range(1, slide_count + 1)
        ]

    if suffix in TEXT_EXTENSIONS:
        return [f"{base_name}.md"]

    raise ValueError(f"Unsupported file type: {input_path}")


def convert_folder(input_dir: Path, output_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(output_dir)
    input_files = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not input_files:
        print(f"No supported files found in: {input_dir}")
        return []

    all_outputs: list[Path] = []
    skipped = 0
    for input_path in input_files:
        source_key = str(input_path.resolve())
        fingerprint = file_fingerprint(input_path)
        manifest_entry = manifest.get(source_key, {})
        output_names = manifest_entry.get("outputs", [])
        if not manifest_entry:
            output_names = expected_output_names(input_path)

        if (
            (manifest_entry.get("fingerprint") == fingerprint or not manifest_entry)
            and isinstance(output_names, list)
            and bool(output_names)
            and all((output_dir / str(name)).exists() for name in output_names)
        ):
            manifest[source_key] = {
                "fingerprint": fingerprint,
                "source_file": input_path.name,
                "outputs": [str(name) for name in output_names],
            }
            skipped += 1
            print(f"Skipped {input_path.name}: already converted")
            continue

        old_output_names = manifest_entry.get("outputs", [])
        for output_name in old_output_names if isinstance(old_output_names, list) else []:
            output_path = output_dir / str(output_name)
            if output_path.exists():
                output_path.unlink()

        outputs = convert_file_to_markdown(input_path, output_dir)
        all_outputs.extend(outputs)
        manifest[source_key] = {
            "fingerprint": fingerprint,
            "source_file": input_path.name,
            "outputs": [path.name for path in outputs],
        }
        print(f"Converted {input_path.name}: {len(outputs)} Markdown files")

    save_manifest(output_dir, manifest)
    if skipped:
        print(f"Skipped {skipped} unchanged source files")

    return all_outputs


def parse_args() -> argparse.Namespace:
    config = load_config()
    default_input_dir = configured_path(config, "input_dir", DEFAULT_INPUT_DIR)
    default_output_dir = configured_path(config, "output_dir", DEFAULT_OUTPUT_DIR)

    parser = argparse.ArgumentParser(
        description="Convert supported PDF, Word, PowerPoint, and text files to Markdown."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help=f"Folder containing supported files. Defaults to: {default_input_dir}",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help=f"Folder for generated Markdown files. Defaults to: {default_output_dir}",
    )
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    outputs = convert_folder(args.input_dir, args.output_dir)
    print(f"Done. Generated {len(outputs)} Markdown files.")


if __name__ == "__main__":
    main()
