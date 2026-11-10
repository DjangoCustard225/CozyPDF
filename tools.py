"""
The list of tools shown on the website.

Each tool is a plain Python dictionary. The HTML templates read these
dictionaries to build the cards on the home page and each tool's page.

Keys used in every tool:
    slug         short id used in the URLs: /tools/<slug> and /api/<slug>
    name         title shown to the user
    description  one sentence shown on the card and on the tool page
    category     one of CATEGORIES (used by the filter buttons)
    icon         a Lucide icon name (browse them at https://lucide.dev/icons)
    accept       which file types the upload box accepts
    multiple     True if the tool takes more than one file
    button       text on the main button
    fields       extra options shown under the upload box (can be empty)

A field is also a dictionary:
    name         the form field name (must match the argument in main.py)
    label        text shown above the input
    type         "text", "password" or "select"
    options      (select only) list of {"value": ..., "label": ...}
    default      (optional) value selected at the start
    placeholder  (optional) grey hint text inside the input
    help         (optional) small explanation under the input
    required     (optional) True if the user must fill it in
"""

CATEGORIES = ["Organize", "Optimize", "Convert", "Edit", "Security"]

IMAGE_TYPES = ".jpg,.jpeg,.png,.webp,.bmp,.gif,.tiff"

TOOLS = [
    # ---------------- Organize ----------------
    {
        "slug": "merge",
        "name": "Merge PDF",
        "description": "Combine several PDFs into a single file, in the order you choose.",
        "category": "Organize",
        "icon": "combine",
        "accept": ".pdf",
        "multiple": True,
        "button": "Merge PDFs",
        "fields": [],
    },
    {
        "slug": "split",
        "name": "Split PDF",
        "description": "Break a PDF into smaller files, one per page or by page ranges.",
        "category": "Organize",
        "icon": "scissors",
        "accept": ".pdf",
        "multiple": False,
        "button": "Split PDF",
        "fields": [
            {
                "name": "ranges",
                "label": "Page ranges (optional)",
                "type": "text",
                "placeholder": "e.g. 1-3, 5, 8-10",
                "help": "Each range becomes its own PDF. Leave empty to put every page in its own file.",
            },
        ],
    },
    {
        "slug": "rotate",
        "name": "Rotate PDF",
        "description": "Turn pages that are sideways or upside down.",
        "category": "Organize",
        "icon": "rotate-cw",
        "accept": ".pdf",
        "multiple": False,
        "button": "Rotate pages",
        "fields": [
            {
                "name": "angle",
                "label": "Rotation",
                "type": "select",
                "default": "90",
                "options": [
                    {"value": "90", "label": "90° clockwise"},
                    {"value": "180", "label": "180° (upside down)"},
                    {"value": "270", "label": "90° counter-clockwise"},
                ],
            },
            {
                "name": "pages",
                "label": "Pages to rotate (optional)",
                "type": "text",
                "placeholder": "e.g. 1, 3-4",
                "help": "Leave empty to rotate every page.",
            },
        ],
    },
    {
        "slug": "delete-pages",
        "name": "Delete Pages",
        "description": "Remove the pages you don't need from a PDF.",
        "category": "Organize",
        "icon": "file-minus",
        "accept": ".pdf",
        "multiple": False,
        "button": "Delete pages",
        "fields": [
            {
                "name": "pages",
                "label": "Pages to delete",
                "type": "text",
                "placeholder": "e.g. 2, 5-7",
                "required": True,
            },
        ],
    },
    # ---------------- Optimize ----------------
    {
        "slug": "compress",
        "name": "Compress PDF",
        "description": "Make a PDF smaller so it is easier to email and upload.",
        "category": "Optimize",
        "icon": "minimize-2",
        "accept": ".pdf",
        "multiple": False,
        "button": "Compress PDF",
        "fields": [
            {
                "name": "level",
                "label": "Compression level",
                "type": "select",
                "default": "medium",
                "options": [
                    {"value": "low", "label": "Light (best quality)"},
                    {"value": "medium", "label": "Recommended"},
                    {"value": "high", "label": "Strong (smallest file)"},
                ],
            },
        ],
    },
    # ---------------- Convert ----------------
    {
        "slug": "pdf-to-images",
        "name": "PDF to Images",
        "description": "Turn every page of a PDF into a PNG or JPG image.",
        "category": "Convert",
        "icon": "image",
        "accept": ".pdf",
        "multiple": False,
        "button": "Convert to images",
        "fields": [
            {
                "name": "image_format",
                "label": "Image format",
                "type": "select",
                "default": "png",
                "options": [
                    {"value": "png", "label": "PNG (sharp, larger)"},
                    {"value": "jpg", "label": "JPG (smaller)"},
                ],
            },
            {
                "name": "dpi",
                "label": "Quality",
                "type": "select",
                "default": "150",
                "options": [
                    {"value": "72", "label": "Screen (72 DPI)"},
                    {"value": "150", "label": "Standard (150 DPI)"},
                    {"value": "300", "label": "Print (300 DPI)"},
                ],
            },
        ],
    },
    {
        "slug": "images-to-pdf",
        "name": "Images to PDF",
        "description": "Put JPG, PNG and other images together into one PDF.",
        "category": "Convert",
        "icon": "images",
        "accept": IMAGE_TYPES,
        "multiple": True,
        "button": "Create PDF",
        "fields": [],
    },
    {
        "slug": "extract-text",
        "name": "Extract Text",
        "description": "Copy all the text out of a PDF into a plain .txt file.",
        "category": "Convert",
        "icon": "file-text",
        "accept": ".pdf",
        "multiple": False,
        "button": "Extract text",
        "fields": [],
    },
    # ---------------- Edit ----------------
    {
        "slug": "watermark",
        "name": "Add Watermark",
        "description": "Stamp a word like CONFIDENTIAL or DRAFT across every page.",
        "category": "Edit",
        "icon": "stamp",
        "accept": ".pdf",
        "multiple": False,
        "button": "Add watermark",
        "fields": [
            {
                "name": "text",
                "label": "Watermark text",
                "type": "text",
                "placeholder": "e.g. CONFIDENTIAL",
                "required": True,
            },
            {
                "name": "opacity",
                "label": "Visibility",
                "type": "select",
                "default": "0.2",
                "options": [
                    {"value": "0.1", "label": "Faint"},
                    {"value": "0.2", "label": "Normal"},
                    {"value": "0.4", "label": "Strong"},
                ],
            },
        ],
    },
    {
        "slug": "page-numbers",
        "name": "Add Page Numbers",
        "description": "Number the pages of your PDF automatically.",
        "category": "Edit",
        "icon": "hash",
        "accept": ".pdf",
        "multiple": False,
        "button": "Add page numbers",
        "fields": [
            {
                "name": "position",
                "label": "Position",
                "type": "select",
                "default": "bottom-center",
                "options": [
                    {"value": "bottom-center", "label": "Bottom center"},
                    {"value": "bottom-right", "label": "Bottom right"},
                    {"value": "top-right", "label": "Top right"},
                ],
            },
            {
                "name": "style",
                "label": "Style",
                "type": "select",
                "default": "number",
                "options": [
                    {"value": "number", "label": "1, 2, 3 …"},
                    {"value": "page-of", "label": "Page 1 of 10"},
                ],
            },
        ],
    },
    # ---------------- Security ----------------
    {
        "slug": "protect",
        "name": "Protect PDF",
        "description": "Add a password so only people who know it can open the file.",
        "category": "Security",
        "icon": "lock",
        "accept": ".pdf",
        "multiple": False,
        "button": "Protect PDF",
        "fields": [
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "placeholder": "At least 4 characters",
                "required": True,
            },
        ],
    },
    {
        "slug": "unlock",
        "name": "Unlock PDF",
        "description": "Remove the password from a PDF you already know the password for.",
        "category": "Security",
        "icon": "lock-open",
        "accept": ".pdf",
        "multiple": False,
        "button": "Unlock PDF",
        "fields": [
            {
                "name": "password",
                "label": "Current password",
                "type": "password",
                "required": True,
            },
        ],
    },
]


def get_tool(slug):
    """Return the tool with this slug, or None if there isn't one."""
    for tool in TOOLS:
        if tool["slug"] == slug:
            return tool
    return None
