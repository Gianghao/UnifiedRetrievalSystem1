"""Extract source-linked PDF pages for a local retrieval experiment."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import pypdf
from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pages(
    input_pdf: Path,
    source_id: str | None = None,
    conversation_id: str | None = None,
) -> list[dict]:
    """Keep physical, one-based page positions even when a page has no text."""
    with input_pdf.open("rb") as source:
        source_hash = hashlib.file_digest(source, "sha256").hexdigest()
        source.seek(0)
        reader = PdfReader(source)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported by this experiment.")

        records = []
        for page_number, page in enumerate(reader.pages, start=1):
            record = {
                "source_id": source_id or f"sha256:{source_hash}",
                "source_file": input_pdf.name,
                "source_type": "pdf",
                "source_sha256": source_hash,
                "page": page_number,
                "processor": "pypdf",
                "processor_version": pypdf.__version__,
            }
            if conversation_id is not None:
                record["conversation_id"] = conversation_id
            try:
                text = (page.extract_text() or "").strip()
                record["text"] = text
                record["status"] = "ok" if text else "no_text"
            except Exception as error:
                # A damaged page must remain visible at its original position.
                record["text"] = ""
                record["status"] = "error"
                record["error"] = f"{type(error).__name__}: {error}"
            records.append(record)
        return records


def write_records(records: list[dict], output: Path) -> None:
    """Replace the output only after the complete UTF-8 JSON has been written."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output.parent,
            prefix=".pdf-pages-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(records, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        temporary_path.replace(output)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", help="Attachment/message ID or corpus source ID.")
    parser.add_argument("--conversation-id", help="Conversation containing this attachment.")
    arguments = parser.parse_args()
    if arguments.input_pdf.resolve() == arguments.output.resolve():
        parser.error("The output must be a different file from the source PDF.")

    try:
        records = extract_pages(
            arguments.input_pdf, arguments.source_id, arguments.conversation_id
        )
        write_records(records, arguments.output)
    except (OSError, ValueError, PdfReadError) as error:
        print(f"Extraction failed: {error}", file=sys.stderr)
        return 1

    text_pages = sum(record["status"] == "ok" for record in records)
    empty_pages = sum(record["status"] == "no_text" for record in records)
    failed_pages = sum(record["status"] == "error" for record in records)
    print(
        f"Saved {len(records)} pages to {arguments.output} "
        f"({text_pages} with text, {empty_pages} without text, {failed_pages} failed)."
    )
    if empty_pages:
        print(
            "Review pages marked no_text. They may be blank or may require OCR.",
            file=sys.stderr,
        )
    return 1 if failed_pages else 0


if __name__ == "__main__":
    sys.exit(main())
