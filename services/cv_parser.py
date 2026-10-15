"""Extract text from PDF, DOCX, or TXT uploads with size and type checks."""
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader
from docx import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

def parse_cv_bytes(filename: str, content: bytes, max_bytes: int = 10 * 1024 * 1024) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload a PDF, DOCX, or TXT file.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")
    try:
        if suffix == ".txt":
            text = content.decode("utf-8-sig")
        elif suffix == ".pdf":
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported. Upload an unlocked PDF.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            doc = Document(BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                text += "\n" + "\n".join(" | ".join(c.text for c in row.cells) for row in table.rows)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Could not read this file. Check that it is a valid, uncorrupted document.") from exc
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise ValueError("No readable text found. Scanned PDFs need OCR before upload.")
    return text[:500_000]
