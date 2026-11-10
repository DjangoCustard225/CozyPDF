"""
CozyPDF - a PDF toolbox website built with FastAPI.

Start it with:
    uvicorn main:app --reload
then open http://127.0.0.1:8000 in your browser.

This file does two jobs:
  1. It serves the HTML pages (the home page and one page per tool).
  2. It provides the API endpoints (/api/...) that those pages call
     with JavaScript to process the files.

The PDF work itself lives in pdf_utils.py, which keeps this file short.
"""

import re
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

import pdf_utils
from tools import CATEGORIES, TOOLS, get_tool

BASE_DIR = Path(__file__).resolve().parent
MAX_FILE_SIZE_MB = 50  # the biggest file we accept (per file)

# "Media types" tell the browser what kind of file we are sending back.
PDF = "application/pdf"
ZIP = "application/zip"
TEXT = "text/plain; charset=utf-8"

app = FastAPI(title="CozyPDF")

# Files in the "static" folder (CSS, JavaScript) are served at /static/...
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# HTML files in the "templates" folder are filled in with Jinja2.
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# Browsers keep copies of CSS, JavaScript and icons to load pages faster.
# Adding "?v=<number>" to those links makes them download fresh copies after
# you change a file. The number is the time the newest static file was changed.
# It is worked out every time a page is built (a few tiny file checks), so a
# changed file is picked up straight away, without restarting the server.
def static_version():
    return str(int(max(
        path.stat().st_mtime for path in (BASE_DIR / "static").rglob("*") if path.is_file()
    )))


def icon(name, extra_class=""):
    """
    HTML for one icon from static/icons.svg. In a template, write
    {{ icon("download") }} to show the "download" icon.
    Markup(...) tells Jinja2 this is safe HTML that it shouldn't escape.
    """
    return Markup(
        f'<svg class="icon {extra_class}" aria-hidden="true">'
        f'<use href="/static/icons.svg?v={static_version()}#{name}"></use></svg>'
    )


# Make these available in every template.
templates.env.globals["icon"] = icon
templates.env.globals["static_version"] = static_version


# ===========================================================================
# Error handling
# ===========================================================================

@app.exception_handler(ValueError)
async def show_friendly_error(request: Request, error: ValueError):
    """
    pdf_utils raises ValueError("some friendly message") when the user's
    input is wrong. We send that message back as JSON with status 400,
    and the JavaScript shows it on the page.
    """
    return JSONResponse(status_code=400, content={"detail": str(error)})


# ===========================================================================
# Helpers
# ===========================================================================

async def read_upload(upload: UploadFile, must_be_pdf=True):
    """Read an uploaded file into memory and check it looks okay."""
    data = await upload.read()
    name = upload.filename or "file"

    if not data:
        raise ValueError(f'"{name}" is empty.')
    if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f'"{name}" is bigger than {MAX_FILE_SIZE_MB} MB.')

    # Every real PDF starts with "%PDF". Checking the content is safer than
    # trusting the file name, because anyone can rename a file to .pdf.
    if must_be_pdf and b"%PDF" not in data[:1024]:
        raise ValueError(f'"{name}" is not a PDF file.')

    return data


def output_name(original_name, suffix, extension):
    """
    Build a safe download name, e.g. ("My Report.pdf", "rotated", "pdf")
    -> "My_Report_rotated.pdf". We only keep plain letters, numbers, - and _
    so the name works in every browser and operating system.
    """
    stem = Path(original_name or "file").stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "file"
    return f"{stem}_{suffix}.{extension}"


def send_file(data, filename, media_type):
    """Send bytes back to the browser as a file download."""
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===========================================================================
# HTML pages
# ===========================================================================

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Some browsers ask for /favicon.ico by themselves, without reading the
    <link> in the page. We answer with the same logo file.
    """
    return FileResponse(BASE_DIR / "static" / "favicon.svg", media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"tools": TOOLS, "categories": CATEGORIES}
    )


@app.get("/tools/{slug}", response_class=HTMLResponse)
async def tool_page(request: Request, slug: str):
    tool = get_tool(slug)
    if tool is None:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    return templates.TemplateResponse(
        request, "tool.html", {"tool": tool, "max_mb": MAX_FILE_SIZE_MB}
    )


# ===========================================================================
# API endpoints - one for each tool.
# Single-file tools receive a field called "file";
# multi-file tools receive a list called "files".
# ===========================================================================

@app.post("/api/merge")
async def api_merge(files: list[UploadFile] = File(...)):
    pdfs = [await read_upload(f) for f in files]
    result = pdf_utils.merge_pdfs(pdfs)
    return send_file(result, "merged.pdf", PDF)


@app.post("/api/split")
async def api_split(file: UploadFile = File(...), ranges: str = Form("")):
    data = await read_upload(file)
    result = pdf_utils.split_pdf(data, ranges)
    return send_file(result, output_name(file.filename, "split", "zip"), ZIP)


@app.post("/api/rotate")
async def api_rotate(
    file: UploadFile = File(...),
    angle: int = Form(90),
    pages: str = Form(""),
):
    data = await read_upload(file)
    result = pdf_utils.rotate_pdf(data, angle, pages)
    return send_file(result, output_name(file.filename, "rotated", "pdf"), PDF)


@app.post("/api/delete-pages")
async def api_delete_pages(file: UploadFile = File(...), pages: str = Form(...)):
    data = await read_upload(file)
    result = pdf_utils.delete_pages(data, pages)
    return send_file(result, output_name(file.filename, "edited", "pdf"), PDF)


@app.post("/api/compress")
async def api_compress(file: UploadFile = File(...), level: str = Form("medium")):
    data = await read_upload(file)
    result = pdf_utils.compress_pdf(data, level)
    return send_file(result, output_name(file.filename, "compressed", "pdf"), PDF)


@app.post("/api/pdf-to-images")
async def api_pdf_to_images(
    file: UploadFile = File(...),
    image_format: str = Form("png"),
    dpi: int = Form(150),
):
    data = await read_upload(file)
    result = pdf_utils.pdf_to_images(data, image_format, dpi)
    return send_file(result, output_name(file.filename, "images", "zip"), ZIP)


@app.post("/api/images-to-pdf")
async def api_images_to_pdf(files: list[UploadFile] = File(...)):
    images = [await read_upload(f, must_be_pdf=False) for f in files]
    result = pdf_utils.images_to_pdf(images)
    return send_file(result, "images.pdf", PDF)


@app.post("/api/extract-text")
async def api_extract_text(file: UploadFile = File(...)):
    data = await read_upload(file)
    result = pdf_utils.extract_text(data)
    return send_file(result, output_name(file.filename, "text", "txt"), TEXT)


@app.post("/api/watermark")
async def api_watermark(
    file: UploadFile = File(...),
    text: str = Form(...),
    opacity: float = Form(0.2),
):
    data = await read_upload(file)
    result = pdf_utils.add_watermark(data, text, opacity)
    return send_file(result, output_name(file.filename, "watermarked", "pdf"), PDF)


@app.post("/api/page-numbers")
async def api_page_numbers(
    file: UploadFile = File(...),
    position: str = Form("bottom-center"),
    style: str = Form("number"),
):
    data = await read_upload(file)
    result = pdf_utils.add_page_numbers(data, position, style)
    return send_file(result, output_name(file.filename, "numbered", "pdf"), PDF)


@app.post("/api/protect")
async def api_protect(file: UploadFile = File(...), password: str = Form(...)):
    data = await read_upload(file)
    result = pdf_utils.protect_pdf(data, password)
    return send_file(result, output_name(file.filename, "protected", "pdf"), PDF)


@app.post("/api/unlock")
async def api_unlock(file: UploadFile = File(...), password: str = Form(...)):
    data = await read_upload(file)
    result = pdf_utils.unlock_pdf(data, password)
    return send_file(result, output_name(file.filename, "unlocked", "pdf"), PDF)
