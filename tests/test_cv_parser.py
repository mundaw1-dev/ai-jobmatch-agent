from docx import Document
from io import BytesIO
import pytest
from services.cv_parser import parse_cv_bytes

def test_parse_txt():
    assert "Python" in parse_cv_bytes("cv.txt", b"Python Engineer")

def test_reject_unsupported():
    with pytest.raises(ValueError): parse_cv_bytes("cv.exe", b"bad")

def test_reject_empty():
    with pytest.raises(ValueError): parse_cv_bytes("cv.txt", b"")

def test_reject_oversize():
    with pytest.raises(ValueError): parse_cv_bytes("cv.txt", b"12345", max_bytes=4)

def test_parse_docx():
    buf=BytesIO(); doc=Document(); doc.add_paragraph("Data Engineer"); doc.save(buf)
    assert "Data Engineer" in parse_cv_bytes("cv.docx", buf.getvalue())
