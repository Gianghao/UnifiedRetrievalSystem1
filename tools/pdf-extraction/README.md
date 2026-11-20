# PDF page extraction experiment

This is Tài's first processing milestone. A local PDF becomes a JSON array with
one record per physical page. Each record contains searchable text and enough
source metadata to locate the original attachment and page.

This standalone experiment runs on a local file. Uploads in the messaging app
still require a separate processing job to run extraction automatically.

## Run

Open PowerShell in the repository root, the folder containing `package.json` and
`docker-compose.yml`. All commands below use paths relative to that folder.

If the project environment has already been prepared, verify it with this command.

```powershell
.\.venv\Scripts\python.exe --version
```

List the actual PDF paths in the local input folder.

```powershell
Get-ChildItem -LiteralPath '.local-research/input' -Filter '*.pdf' -File | ForEach-Object { $_.FullName }
```

Run the next commands and paste one of those paths when prompted. Paste the path
without surrounding quotes. You can also enter the path to another local PDF.

```powershell
$pdfPath = Read-Host 'PDF path'
.\.venv\Scripts\python.exe tools/pdf-extraction/extract_pdf.py $pdfPath --output .local-research/pdf-pages.json
```

For a PDF downloaded from a conversation, supply the attachment's message UUID
as `--source-id` and its conversation UUID as `--conversation-id`. For independent
local files, the default source ID is derived from the file's SHA-256 hash.
Conversation metadata is provenance. Access checks belong in the application
when this experiment is integrated into its processing and retrieval services.

Input PDFs, extracted text, and validation images belong in `.local-research/`,
which Git ignores. Local experiment copies have their own lifecycle, so remove
them when finished. The app's 30-day attachment expiry does not clean them up.

## Prepare a fresh environment

Create `.venv` once per checkout using an installed Python 3.11 or later.
For an Anaconda installation at `D:\Anaconda`, run these commands from the
repository root.

```powershell
& 'D:\Anaconda\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/pdf-extraction/requirements.txt
```

For another installation, replace `D:\Anaconda\python.exe` with its actual
executable path. PowerShell's `&` runs the executable at the quoted path.
The short command `python` resolves through the current terminal's `PATH`.
An installed interpreter can still be run by its full path when that short
command is unavailable.

## Output

```json
[
  {
    "source_id": "attachment-message-uuid",
    "source_file": "sample.pdf",
    "source_type": "pdf",
    "source_sha256": "sha256-of-the-original-file",
    "page": 1,
    "processor": "pypdf",
    "processor_version": "6.21.4",
    "conversation_id": "conversation-uuid",
    "text": "The demo deadline is Friday.",
    "status": "ok"
  }
]
```

`page` starts at 1 and refers to the physical PDF page, including cover pages.
Printed page labels can differ. Every page retains its position.

- `ok` means the page yielded non-whitespace text. Check extraction fidelity
  against the original before using it as benchmark evidence.
- `no_text` means the page yielded no text. It may be blank or an image requiring
  OCR. Text extraction alone cannot determine which.
- `error` includes a diagnostic for that page. Other readable pages continue.
  The command writes those records and returns exit code 1.

Encrypted or unreadable documents return exit code 1. Extraction completes before
the output is atomically replaced, preserving an existing output if opening or
writing the document fails. The source PDF cannot be used as the output path.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tools/pdf-extraction -p "test_*.py" -v
```

These checks use synthetic documents. They cover page numbering across an empty
page, source identity, Unicode JSON, encrypted and malformed inputs, per-page
failure reporting, and protection of an existing output and the source PDF.

For a real sample, compare a sentence on a specific rendered page with the
matching JSON record. Text extraction can lose table structure, reading order,
or mathematical formatting. OCR, chunking, indexing, and search are future work.

The implementation follows the upstream extraction interface and limitations.
[pypdf text extraction documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
