"""
Tests for CozyPDF. Run them from the project folder with:

    python -m pytest

Each test creates a small PDF in memory, runs a tool on it,
and checks that the result looks right.
"""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from reportlab.pdfgen import canvas

import pdf_utils
from main import app

client = TestClient(app)


# ----- Helpers that build test files -----

def make_pdf(page_count=3):
    """Create a PDF with `page_count` pages that say "Page 1", "Page 2" ..."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    for number in range(1, page_count + 1):
        c.drawString(100, 700, f"Page {number}")
        c.showPage()
    c.save()
    return buffer.getvalue()


def make_png(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (200, 100), color).save(buffer, "PNG")
    return buffer.getvalue()


def count_pages(pdf_bytes):
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


def page_text(pdf_bytes, index):
    return PdfReader(io.BytesIO(pdf_bytes)).pages[index].extract_text()


# ----- Page ranges -----

def test_parse_page_ranges():
    assert pdf_utils.parse_page_ranges("1-3, 5", 10) == [[0, 1, 2], [4]]
    assert pdf_utils.parse_page_ranges("8-", 10) == [[7, 8, 9]]


@pytest.mark.parametrize("bad_text", ["0", "11", "5-2", "abc", ""])
def test_parse_page_ranges_rejects_bad_input(bad_text):
    with pytest.raises(ValueError):
        pdf_utils.parse_page_ranges(bad_text, 10)


# ----- Organize -----

def test_merge():
    result = pdf_utils.merge_pdfs([make_pdf(2), make_pdf(3)])
    assert count_pages(result) == 5


def test_merge_needs_two_files():
    with pytest.raises(ValueError):
        pdf_utils.merge_pdfs([make_pdf(2)])


def test_split_every_page():
    result = pdf_utils.split_pdf(make_pdf(3))
    names = zipfile.ZipFile(io.BytesIO(result)).namelist()
    assert len(names) == 3


def test_split_ranges():
    result = pdf_utils.split_pdf(make_pdf(5), "1-2, 4-5")
    archive = zipfile.ZipFile(io.BytesIO(result))
    assert archive.namelist() == ["01_pages_1-2.pdf", "02_pages_4-5.pdf"]
    assert count_pages(archive.read("01_pages_1-2.pdf")) == 2


def test_rotate_only_some_pages():
    result = pdf_utils.rotate_pdf(make_pdf(3), 90, "2")
    pages = PdfReader(io.BytesIO(result)).pages
    assert [page.rotation for page in pages] == [0, 90, 0]


def test_delete_pages():
    result = pdf_utils.delete_pages(make_pdf(4), "2-3")
    assert count_pages(result) == 2
    assert "Page 4" in page_text(result, 1)


def test_cannot_delete_every_page():
    with pytest.raises(ValueError):
        pdf_utils.delete_pages(make_pdf(2), "1-2")


# ----- Optimize -----

def test_compress_returns_valid_pdf():
    original = make_pdf(3)
    result = pdf_utils.compress_pdf(original, "high")
    assert count_pages(result) == 3
    assert len(result) <= len(original)


# ----- Convert -----

def test_pdf_to_images():
    result = pdf_utils.pdf_to_images(make_pdf(2), "jpg", 72)
    names = zipfile.ZipFile(io.BytesIO(result)).namelist()
    assert names == ["page_001.jpg", "page_002.jpg"]


def test_images_to_pdf():
    result = pdf_utils.images_to_pdf([make_png("red"), make_png("blue")])
    assert count_pages(result) == 2


def test_extract_text():
    result = pdf_utils.extract_text(make_pdf(2)).decode("utf-8")
    assert "Page 1" in result and "Page 2" in result


# ----- Edit -----

def test_watermark():
    result = pdf_utils.add_watermark(make_pdf(2), "DRAFT")
    assert "DRAFT" in page_text(result, 0)


def test_page_numbers():
    result = pdf_utils.add_page_numbers(make_pdf(3), style="page-of")
    assert "Page 2 of 3" in page_text(result, 1)


# ----- Security -----

def test_protect_and_unlock():
    locked = pdf_utils.protect_pdf(make_pdf(2), "secret")
    assert PdfReader(io.BytesIO(locked)).is_encrypted

    with pytest.raises(ValueError):
        pdf_utils.unlock_pdf(locked, "wrong")

    unlocked = pdf_utils.unlock_pdf(locked, "secret")
    assert not PdfReader(io.BytesIO(unlocked)).is_encrypted
    assert count_pages(unlocked) == 2


def test_locked_pdf_gives_friendly_error():
    locked = pdf_utils.protect_pdf(make_pdf(1), "secret")
    with pytest.raises(ValueError, match="password"):
        pdf_utils.rotate_pdf(locked, 90)


# ----- Website and API -----

def test_home_page_lists_every_tool():
    response = client.get("/")
    assert response.status_code == 200
    assert "Merge PDF" in response.text
    assert "Unlock PDF" in response.text


def test_every_tool_page_loads():
    from tools import TOOLS

    for tool in TOOLS:
        response = client.get(f"/tools/{tool['slug']}")
        assert response.status_code == 200, tool["slug"]


def test_unknown_tool_is_404():
    assert client.get("/tools/not-a-tool").status_code == 404


def test_api_merge():
    files = [
        ("files", ("a.pdf", make_pdf(1), "application/pdf")),
        ("files", ("b.pdf", make_pdf(2), "application/pdf")),
    ]
    response = client.post("/api/merge", files=files)
    assert response.status_code == 200
    assert count_pages(response.content) == 3
    assert 'filename="merged.pdf"' in response.headers["content-disposition"]


def test_api_rejects_non_pdf():
    files = {"file": ("fake.pdf", b"hello, I am not a PDF", "application/pdf")}
    response = client.post("/api/rotate", files=files)
    assert response.status_code == 400
    assert "not a PDF" in response.json()["detail"]


def test_api_shows_friendly_error():
    files = {"file": ("doc.pdf", make_pdf(2), "application/pdf")}
    response = client.post("/api/delete-pages", files=files, data={"pages": "9"})
    assert response.status_code == 400
    assert "pages 1 to 2" in response.json()["detail"]


def test_api_safe_download_name():
    files = {"file": ("My Report (final).pdf", make_pdf(1), "application/pdf")}
    response = client.post("/api/rotate", files=files, data={"angle": "180"})
    assert 'filename="My_Report_final_rotated.pdf"' in response.headers["content-disposition"]


# ----- Icons -----

def test_every_icon_used_exists_in_icons_svg():
    import re
    from pathlib import Path
    from tools import TOOLS

    # Parse the file as real XML: this also fails if icons.svg is broken.
    import xml.etree.ElementTree as ET
    svg = ET.parse("static/icons.svg").getroot()
    available = {symbol.get("id") for symbol in svg.iter("{http://www.w3.org/2000/svg}symbol")}

    used = {tool["icon"] for tool in TOOLS}
    for template in Path("templates").rglob("*.html"):
        used |= set(re.findall(r'icon\("([\w-]+)"', template.read_text()))
    script = Path("static/js/app.js").read_text()
    used |= set(re.findall(r'(?:iconHTML|makeIconButton)\("([\w-]+)"', script))

    assert used - available == set(), "add these icons to static/icons.svg"


def test_favicon_is_served_at_both_addresses():
    page = client.get("/").text
    assert "/static/favicon.svg?v=" in page  # versioned, so browsers refresh it

    for address in ("/static/favicon.svg", "/favicon.ico"):
        response = client.get(address)
        assert response.status_code == 200, address
        assert "<svg" in response.text
