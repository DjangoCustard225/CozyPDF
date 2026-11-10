"""
All the PDF work happens in this file.

Every function takes the file contents as `bytes` and returns the result
as `bytes`. Nothing is saved to disk: we read the upload into memory,
change it, and send the result straight back to the browser.

If something is wrong with the user's input (bad page numbers, wrong
password, ...) we raise a ValueError with a friendly message.
main.py catches it and shows the message on the web page.

Libraries used:
    pypdf      - read and write PDFs (merge, split, rotate, encrypt ...)
    pypdfium2  - draw PDF pages as pictures (PDF to images)
    Pillow     - work with images
    reportlab  - draw text (watermarks and page numbers)
"""

import io
import zipfile

import pypdfium2
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas


# ---------------------------------------------------------------------------
# Small helpers used by the tools below
# ---------------------------------------------------------------------------

def open_pdf(data):
    """Open PDF bytes and return a PdfReader. Raises ValueError if we can't."""
    try:
        reader = PdfReader(io.BytesIO(data))

        # Some PDFs are "encrypted" with an empty password (they only block
        # printing or copying). We can open those without asking the user.
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError(
                "This PDF is password-protected. Remove the password first "
                "with the Unlock PDF tool."
            )

        page_count = len(reader.pages)  # this fails on broken files
    except ValueError:
        raise
    except Exception:
        raise ValueError("This file looks damaged or is not a real PDF.")

    if page_count == 0:
        raise ValueError("This PDF has no pages.")
    return reader


def pdf_to_bytes(writer):
    """Turn a PdfWriter into the bytes of a finished PDF file."""
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def parse_page_ranges(text, total_pages):
    """
    Turn text like "1-3, 5, 8-" into groups of page indexes.

    People count pages from 1, but Python counts from 0, so page 1 becomes
    index 0. "8-" means "from page 8 to the end".

    Example (10 pages):  "1-3, 5"  ->  [[0, 1, 2], [4]]
    """
    groups = []
    for part in text.replace(" ", "").split(","):
        if part == "":
            continue
        try:
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                start = int(start_text) if start_text else 1
                end = int(end_text) if end_text else total_pages
            else:
                start = end = int(part)
        except ValueError:
            raise ValueError(f'"{part}" is not a valid page or range. Use something like 1-3, 5.')

        if start < 1 or end > total_pages or start > end:
            raise ValueError(
                f'"{part}" is outside the document. This PDF has pages 1 to {total_pages}.'
            )
        groups.append(list(range(start - 1, end)))

    if not groups:
        raise ValueError("Please enter at least one page number.")
    return groups


def parse_page_numbers(text, total_pages):
    """Like parse_page_ranges, but returns one flat set of page indexes."""
    pages = set()
    for group in parse_page_ranges(text, total_pages):
        pages.update(group)
    return pages


def make_zip(files):
    """Pack a {filename: bytes} dictionary into the bytes of a .zip file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, data in files.items():
            zip_file.writestr(filename, data)
    return buffer.getvalue()


def page_size(page):
    """Return (width, height) of a page in PDF points (1 point = 1/72 inch)."""
    return float(page.mediabox.width), float(page.mediabox.height)


# ---------------------------------------------------------------------------
# Organize
# ---------------------------------------------------------------------------

def merge_pdfs(files):
    """Join a list of PDFs (bytes) into one PDF, in the given order."""
    if len(files) < 2:
        raise ValueError("Please choose at least two PDFs to merge.")

    writer = PdfWriter()
    for data in files:
        reader = open_pdf(data)
        for page in reader.pages:
            writer.add_page(page)
    return pdf_to_bytes(writer)


def split_pdf(data, ranges_text=""):
    """
    Split a PDF into several PDFs and return them together in a .zip file.
    With no ranges, every page becomes its own PDF.
    """
    reader = open_pdf(data)
    total = len(reader.pages)

    if ranges_text.strip():
        groups = parse_page_ranges(ranges_text, total)
    else:
        groups = [[index] for index in range(total)]

    output_files = {}
    for number, group in enumerate(groups, start=1):
        writer = PdfWriter()
        for index in group:
            writer.add_page(reader.pages[index])

        first_page, last_page = group[0] + 1, group[-1] + 1
        if first_page == last_page:
            filename = f"{number:02d}_page_{first_page}.pdf"
        else:
            filename = f"{number:02d}_pages_{first_page}-{last_page}.pdf"
        output_files[filename] = pdf_to_bytes(writer)

    return make_zip(output_files)


def rotate_pdf(data, angle, pages_text=""):
    """Rotate some (or all) pages clockwise by 90, 180 or 270 degrees."""
    if angle not in (90, 180, 270):
        raise ValueError("Rotation must be 90, 180 or 270 degrees.")

    reader = open_pdf(data)
    total = len(reader.pages)
    if pages_text.strip():
        pages_to_rotate = parse_page_numbers(pages_text, total)
    else:
        pages_to_rotate = set(range(total))

    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        new_page = writer.add_page(page)
        if index in pages_to_rotate:
            new_page.rotate(angle)
    return pdf_to_bytes(writer)


def delete_pages(data, pages_text):
    """Return a copy of the PDF without the listed pages."""
    reader = open_pdf(data)
    total = len(reader.pages)
    pages_to_delete = parse_page_numbers(pages_text, total)

    if len(pages_to_delete) >= total:
        raise ValueError("You can't delete every page. Keep at least one.")

    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index not in pages_to_delete:
            writer.add_page(page)
    return pdf_to_bytes(writer)


# ---------------------------------------------------------------------------
# Optimize
# ---------------------------------------------------------------------------

def compress_pdf(data, level="medium"):
    """
    Make a PDF smaller by:
      1. saving the pictures inside it again as lower-quality JPEGs, and
      2. squeezing the page instructions (zlib compression), and
      3. removing duplicate objects.
    If the result isn't smaller, the original file is returned unchanged.
    """
    jpeg_quality = {"low": 80, "medium": 60, "high": 35}.get(level)
    if jpeg_quality is None:
        raise ValueError("Unknown compression level.")

    reader = open_pdf(data)
    writer = PdfWriter(clone_from=reader)

    for page in writer.pages:
        for image in page.images:
            try:
                image.replace(image.image, quality=jpeg_quality)
            except Exception:
                pass  # some unusual image types can't be re-saved, so we skip them
        page.compress_content_streams()

    writer.compress_identical_objects()  # removes duplicate and unused objects
    result = pdf_to_bytes(writer)

    if len(result) < len(data):
        return result
    return data


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------

def pdf_to_images(data, image_format="png", dpi=150):
    """Draw every page as a PNG or JPG picture and return them in a .zip."""
    if image_format not in ("png", "jpg"):
        raise ValueError("Image format must be PNG or JPG.")
    if dpi not in (72, 150, 300):
        raise ValueError("Quality must be 72, 150 or 300 DPI.")

    open_pdf(data)  # checks the file and gives a friendly error if it's broken

    document = pypdfium2.PdfDocument(data)
    scale = dpi / 72  # PDFs measure in points: 72 points = 1 inch
    output_files = {}
    try:
        for index in range(len(document)):
            picture = document[index].render(scale=scale).to_pil()

            buffer = io.BytesIO()
            if image_format == "jpg":
                picture.convert("RGB").save(buffer, "JPEG", quality=90)
            else:
                picture.save(buffer, "PNG")
            output_files[f"page_{index + 1:03d}.{image_format}"] = buffer.getvalue()
    finally:
        document.close()

    return make_zip(output_files)


def images_to_pdf(files):
    """Put a list of images (bytes) into one PDF, one image per page."""
    if not files:
        raise ValueError("Please choose at least one image.")

    images = []
    for data in files:
        try:
            image = Image.open(io.BytesIO(data))
            image = ImageOps.exif_transpose(image)  # fixes sideways phone photos
        except Exception:
            raise ValueError("One of the files isn't an image we can read. Try JPG or PNG.")
        images.append(image.convert("RGB"))  # PDF pages need RGB images

    buffer = io.BytesIO()
    images[0].save(buffer, "PDF", save_all=True, append_images=images[1:], resolution=100)
    return buffer.getvalue()


def extract_text(data):
    """Return all the text in the PDF as UTF-8 bytes (a .txt file)."""
    reader = open_pdf(data)

    sections = []
    found_any_text = False
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            found_any_text = True
        sections.append(f"----- Page {number} -----\n{text}\n")

    if not found_any_text:
        raise ValueError(
            "No text found. This PDF is probably made of scanned images, "
            "which need OCR software to read."
        )
    return "\n".join(sections).encode("utf-8")


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

def make_overlay_page(width, height, draw):
    """
    Create a see-through PDF page of the given size and let `draw(c)`
    paint on it with a reportlab canvas `c`. We then lay this page on top
    of a real page, like a sticker.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    draw(c)
    c.save()
    return PdfReader(buffer).pages[0]


def add_watermark(data, text, opacity=0.2):
    """Write big diagonal text across the middle of every page."""
    text = text.strip()
    if not text:
        raise ValueError("Please enter the watermark text.")
    if len(text) > 60:
        raise ValueError("Watermark text must be 60 characters or fewer.")
    if not 0 < opacity <= 1:
        raise ValueError("Opacity must be between 0 and 1.")

    reader = open_pdf(data)
    writer = PdfWriter(clone_from=reader)

    for page in writer.pages:
        width, height = page_size(page)
        # Make the text roughly fit across the page diagonal.
        font_size = max(20, min(120, min(width, height) * 1.2 / len(text)))

        def draw(c):
            c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
            c.setFont("Helvetica-Bold", font_size)
            c.translate(width / 2, height / 2)  # move to the page center
            c.rotate(45)
            c.drawCentredString(0, -font_size / 3, text)

        page.merge_page(make_overlay_page(width, height, draw))

    return pdf_to_bytes(writer)


def add_page_numbers(data, position="bottom-center", style="number"):
    """Write a page number on every page."""
    if position not in ("bottom-center", "bottom-right", "top-right"):
        raise ValueError("Unknown position.")
    if style not in ("number", "page-of"):
        raise ValueError("Unknown style.")

    reader = open_pdf(data)
    writer = PdfWriter(clone_from=reader)
    total = len(writer.pages)
    margin = 30  # distance from the edge of the page, in points

    for number, page in enumerate(writer.pages, start=1):
        width, height = page_size(page)
        label = str(number) if style == "number" else f"Page {number} of {total}"

        def draw(c):
            c.setFillColor(Color(0.2, 0.2, 0.2))
            c.setFont("Helvetica", 10)
            if position == "bottom-center":
                c.drawCentredString(width / 2, margin, label)
            elif position == "bottom-right":
                c.drawRightString(width - margin, margin, label)
            else:  # top-right
                c.drawRightString(width - margin, height - margin, label)

        page.merge_page(make_overlay_page(width, height, draw))

    return pdf_to_bytes(writer)


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def protect_pdf(data, password):
    """Lock the PDF with a password (AES-256 encryption)."""
    if len(password) < 4:
        raise ValueError("Please use a password with at least 4 characters.")

    reader = open_pdf(data)
    writer = PdfWriter(clone_from=reader)
    writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
    return pdf_to_bytes(writer)


def unlock_pdf(data, password):
    """Remove the password from a PDF, given the correct password."""
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        raise ValueError("This file looks damaged or is not a real PDF.")

    if not reader.is_encrypted:
        raise ValueError("This PDF isn't password-protected, so there's nothing to unlock.")
    if not reader.decrypt(password):
        raise ValueError("That password is not correct.")

    writer = PdfWriter(clone_from=reader)
    return pdf_to_bytes(writer)
