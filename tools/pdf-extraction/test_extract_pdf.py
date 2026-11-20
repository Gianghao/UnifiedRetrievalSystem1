"""Synthetic checks for page positions, provenance, and extraction failures."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from extract_pdf import extract_pages, write_records


def create_pdf(path: Path, pages: list[str], encrypted: bool = False) -> None:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        content = DecodedStreamObject()
        content.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = content
    if encrypted:
        writer.encrypt("test-password")
    writer.write(path)


class PdfExtractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "sample.pdf"

    def test_pages_keep_text_locations_and_source_identity(self):
        create_pdf(self.source, ["Deadline is Friday.", "", "Budget is 500."])
        records = extract_pages(self.source, "attachment-123", "conversation-456")
        self.assertEqual([record["page"] for record in records], [1, 2, 3])
        self.assertEqual(
            [record["status"] for record in records], ["ok", "no_text", "ok"]
        )
        self.assertEqual(records[0]["text"], "Deadline is Friday.")
        self.assertEqual(records[2]["text"], "Budget is 500.")
        expected_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        for record in records:
            self.assertEqual(record["source_id"], "attachment-123")
            self.assertEqual(record["conversation_id"], "conversation-456")
            self.assertEqual(record["source_file"], "sample.pdf")
            self.assertEqual(record["source_sha256"], expected_hash)

    def test_local_sources_have_repeatable_content_identity(self):
        create_pdf(self.source, ["Synthetic research sample."])
        first = extract_pages(self.source)
        second = extract_pages(self.source)
        self.assertEqual(first, second)
        self.assertTrue(first[0]["source_id"].startswith("sha256:"))

    def test_page_failure_retains_its_position_and_later_pages(self):
        create_pdf(self.source, ["First page.", "Second page."])
        with patch(
            "pypdf._page.PageObject.extract_text",
            side_effect=[ValueError("bad page"), "Second page."],
        ):
            records = extract_pages(self.source)
        self.assertEqual(records[0]["status"], "error")
        self.assertEqual(records[0]["page"], 1)
        self.assertIn("bad page", records[0]["error"])
        self.assertEqual(records[1]["page"], 2)
        self.assertEqual(records[1]["text"], "Second page.")

    def test_encrypted_pdf_reports_a_clear_failure(self):
        create_pdf(self.source, ["Protected sample."], encrypted=True)
        with self.assertRaisesRegex(ValueError, "Encrypted PDFs"):
            extract_pages(self.source)

    def test_cli_rejects_invalid_pdf_without_replacing_existing_output(self):
        self.source.write_bytes(b"not a PDF")
        output = self.source.with_suffix(".json")
        output.write_text("previous output", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("extract_pdf.py")),
                str(self.source),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Extraction failed", result.stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "previous output")

    def test_json_preserves_unicode_and_cli_protects_source_file(self):
        output = self.source.with_suffix(".json")
        write_records([{"page": 1, "text": "Tiếng Việt"}], output)
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8"))[0]["text"], "Tiếng Việt"
        )
        create_pdf(self.source, ["Source must remain readable."])
        original = self.source.read_bytes()
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("extract_pdf.py")),
                str(self.source),
                "--output",
                str(self.source),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
