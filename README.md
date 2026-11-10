# CozyPDF

A free PDF toolbox website built with **FastAPI**, **HTML**, **CSS** and a little **JavaScript**.

It comes with 12 tools:

| Organize | Optimize | Convert | Edit | Security |
|---|---|---|---|---|
| Merge PDF | Compress PDF | PDF to Images | Add Watermark | Protect PDF |
| Split PDF | | Images to PDF | Add Page Numbers | Unlock PDF |
| Rotate PDF | | Extract Text | | |
| Delete Pages | | | | |

The site has a black-and-white design with a light and dark mode, drag-and-drop uploads, a progress bar, search and category filters, and a layout that works on phones.
Files are processed in memory and never saved on the server.

---

## 1. Run it on your computer

You need **Python 3.10 or newer**.

```bash
# 1. Go into the project folder
cd cozypdf

# 2. Create a virtual environment (a private space for this project's packages)
python -m venv .venv

# 3. Turn it on
#    macOS / Linux:
source .venv/bin/activate
#    Windows:
.venv\Scripts\activate

# 4. Install the packages
pip install -r requirements.txt

# 5. Start the server
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

`--reload` restarts the server every time you save a file, which is handy while you're learning.

FastAPI also creates interactive API docs at **http://127.0.0.1:8000/docs**. You can try every endpoint from there.

## 2. Run the tests

```bash
python -m pytest
```

---

## 3. How the project is organized

```
cozypdf/
├── main.py              ← the web server: pages + API endpoints
├── pdf_utils.py         ← the actual PDF work (merge, split, ...)
├── tools.py             ← the list of tools shown on the site
├── templates/           ← HTML pages (Jinja2 templates)
│   ├── base.html        ← shared layout: navbar, footer, scripts
│   ├── index.html       ← home page: hero + tool grid
│   ├── tool.html        ← one page used by EVERY tool
│   ├── 404.html         ← "page not found"
│   └── partials/
│       └── tool_card.html
├── static/              ← files sent to the browser as they are
│   ├── css/style.css    ← all the styling (colors are at the top)
│   ├── js/app.js        ← theme toggle, search, upload + progress
│   ├── fonts/           ← JetBrains Mono font files + license
│   ├── icons.svg        ← the icons used on the site
│   └── favicon.svg
├── tests/
│   └── test_cozypdf.py
├── requirements.txt     ← the Python packages to install
├── Dockerfile           ← recipe for running the site in Docker
├── docker-compose.yml   ← starts the site (and optional tunnel) with one command
├── .dockerignore        ← files Docker should leave out
└── .env.example         ← template for your private settings (.env)
```

### What happens when someone uses a tool

1. The browser opens `/tools/merge`. `main.py` finds the `merge` entry in `tools.py` and fills in `tool.html` with it.
2. The user drops in files and clicks **Merge PDFs**.
3. `app.js` sends the files to `/api/merge`.
4. `main.py` checks the files, then calls `pdf_utils.merge_pdfs(...)`.
5. The new PDF is sent back, and `app.js` shows a **Download** button.

If something is wrong (wrong password, bad page numbers, ...), `pdf_utils.py` raises a `ValueError("friendly message")`. `main.py` turns that into an error response, and the message appears on the page.

---

## 4. Add your own tool (example: "Reverse Pages")

**Step 1: write the PDF function** in `pdf_utils.py`:

```python
def reverse_pages(data):
    """Put the pages in the opposite order."""
    reader = open_pdf(data)
    writer = PdfWriter()
    for page in reversed(reader.pages):
        writer.add_page(page)
    return pdf_to_bytes(writer)
```

**Step 2: add an API endpoint** in `main.py`:

```python
@app.post("/api/reverse")
async def api_reverse(file: UploadFile = File(...)):
    data = await read_upload(file)
    result = pdf_utils.reverse_pages(data)
    return send_file(result, output_name(file.filename, "reversed", "pdf"), PDF)
```

**Step 3: describe it** in the `TOOLS` list in `tools.py`:

```python
{
    "slug": "reverse",                 # must match the /api/reverse URL
    "name": "Reverse Pages",
    "description": "Flip the page order so the last page comes first.",
    "category": "Organize",
    "icon": "arrow-down-up",           # an icon from static/icons.svg (see below)
    "accept": ".pdf",
    "multiple": False,
    "button": "Reverse pages",
    "fields": [],
},
```

**Step 4: add its icon** (only if it isn't in `static/icons.svg` yet). Open https://lucide.dev/icons/arrow-down-up, click **Copy SVG**, and paste the lines between `<svg ...>` and `</svg>` into `static/icons.svg`, wrapped like this:

```html
<symbol id="arrow-down-up" viewBox="0 0 24 24">
  ...the pasted lines...
</symbol>
```

Refresh the browser. The new card appears on the home page, and its page works right away.
You don't have to write any new HTML or JavaScript.

---

## 5. Change the look

- **Colors:** the site is black and white. The colors are variables at the top of `static/css/style.css` (`--bg`, `--text`, `--border`, ...). The dark-mode values are in the `[data-theme="dark"]` block just below.
- **Font:** the site uses [JetBrains Mono](https://www.jetbrains.com/lp/mono/) (SIL Open Font License), stored in `static/fonts/` so it works offline. To change it, put new `.woff2` files there and update the `@font-face` rules and `--font` at the top of `style.css`, plus the two `preload` links in `templates/base.html`.
- **Icons:** the site uses [Lucide](https://lucide.dev/icons) icons, stored in `static/icons.svg` so they work offline. Only the icons the site uses are included. Write `{{ icon("icon-name") }}` anywhere in a template. To add one, see Step 4 in section 4.

## 6. Good next steps

- **Bigger files or heavy tools:** the PDF work runs inside the web request. For very large files, or slow tools like OCR, move the work to a background worker (for example Celery or RQ with Redis).
- **Putting it online:** see section 7.

---

## 7. Host it on your own home server

These steps put the site on the internet from a computer at home (a mini PC, a Raspberry Pi 4 or newer, an old laptop, a NAS ...). The project already includes a `Dockerfile` and a `docker-compose.yml`.

### Step 1: Install Docker on the server

Follow the official guide for your system: https://docs.docker.com/engine/install/
Then check it works:

```bash
docker --version
docker compose version
```

### Step 2: Copy the project to the server

From your own computer (replace the user and address with your server's):

```bash
scp -r cozypdf user@192.168.1.50:~/
```

Or put the project on GitHub and run `git clone` on the server.

### Step 3: Start the site

On the server:

```bash
cd ~/cozypdf
docker compose up -d --build
```

Open `http://<server-ip>:8000` from another device on your home network. If that works, the site is running. It will also restart by itself after a reboot.

Useful commands:

```bash
docker compose logs -f           # watch the logs (Ctrl+C to stop watching)
docker compose down              # stop the site
docker compose up -d --build     # rebuild and restart after you change the code
```

### Step 4: Make it reachable from the internet

Pick **one** of these.

#### Option A (recommended): Cloudflare Tunnel, no router changes

The server makes an outgoing connection to Cloudflare, and Cloudflare serves your site. You don't open any ports, your home IP address stays hidden, and HTTPS is automatic. It works even if your internet provider blocks incoming connections. It's free, but you need a **domain name that uses Cloudflare's DNS** (a domain costs roughly $10 a year).

1. Make a free account at https://dash.cloudflare.com and add your domain.
2. Open **Zero Trust → Networks → Tunnels** (menu names change now and then) and click **Create a tunnel**. Choose **Cloudflared** and give it a name.
3. Copy the **token** shown on the install page. It is the long text after `--token`.
4. On the server, create the file `.env` next to `docker-compose.yml`:
   ```bash
   cp .env.example .env
   nano .env        # paste your token after TUNNEL_TOKEN=
   ```
5. In the tunnel's **Public Hostname** tab, add your hostname, for example `pdf.yourdomain.com`, with service type **HTTP** and URL **`cozypdf:8000`**.
6. Start the site together with the tunnel:
   ```bash
   docker compose --profile tunnel up -d
   ```

Visit `https://pdf.yourdomain.com`.

**No domain yet?** Try a temporary link first. It needs no account, and the address changes every time you restart it:

```bash
docker run --rm --network host cloudflare/cloudflared:latest tunnel --url http://localhost:8000
```

#### Option B: Port forwarding, no Cloudflare

1. Give the server a fixed address on your network (set a DHCP reservation in your router).
2. In your router, forward **ports 80 and 443** to the server.
3. Get a domain, or a free name from https://www.duckdns.org, that points to your home IP address.
4. Run a reverse proxy that handles HTTPS. [Caddy](https://caddyserver.com) is the easiest. Its whole config can be two lines (`pdf.yourdomain.com` and `reverse_proxy localhost:8000`) and it gets the HTTPS certificate for you.

This only works if your internet provider gives you a real public IP address. If you are behind CGNAT (common on mobile and some home internet), use Option A.

### Before you share the link

- **Memory:** `docker-compose.yml` limits the site to 1 GB of RAM so one huge PDF can't freeze the server. Raise or lower `mem_limit` to match your machine.
- **Upload limit:** `MAX_FILE_SIZE_MB` in `main.py` is 50. Cloudflare's free plan allows uploads up to 100 MB, so this is fine.
- **Abuse:** anyone on the internet can use the tools. Consider adding rate limiting (the `slowapi` package) and keep an eye on the logs.
- **Keep it separate:** don't forward other ports on your server. Keep the operating system and Docker up to date.
- **Updates:** after editing the code, copy it to the server again and run `docker compose up -d --build`.
