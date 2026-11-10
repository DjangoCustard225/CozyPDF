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

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and the packages. Install it once by following https://docs.astral.sh/uv/getting-started/installation/ . You don't need to install Python yourself: uv downloads the right version (3.14) when it is needed.

```bash
# 1. Go into the project folder
cd cozypdf

# 2. Set up everything: Python, a private environment (.venv) and all packages
uv sync

# 3. Start the site
uv run fastapi run
```

Open **http://127.0.0.1:8000** in your browser.

While you are learning, use `uv run fastapi dev` instead. It restarts the server every time you save a file and shows detailed error pages.

FastAPI also creates interactive API docs at **http://127.0.0.1:8000/docs**. You can try every endpoint from there.

## 2. Run the tests and checks

```bash
uv run pytest               # run the tests
uv run ruff check --fix     # sort the imports in the Python files
```

To add a package later, run `uv add some-package`. For a tool you only use while working on the project, run `uv add --dev some-package`. uv updates `pyproject.toml` and `uv.lock` for you.

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
├── pyproject.toml       ← project details, packages to install, test and lint settings
├── uv.lock              ← the exact package versions (made by uv, don't edit by hand)
└── .python-version      ← the Python version uv uses (3.14)
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

These steps put the site on the internet from a computer at home (a mini PC, a Raspberry Pi 4 or newer, an old laptop ...). They assume a Linux server with **systemd** (Debian, Ubuntu and Raspberry Pi OS all have it). There is no Docker: the site runs as a normal Python program that systemd keeps alive.

### Step 1: Install git and uv on the server

```bash
sudo apt install git curl
```

Then install uv, following https://docs.astral.sh/uv/getting-started/installation/ . It installs for your user only, and you can check it with `uv --version` (open a new terminal first). uv will download Python 3.14 by itself.

### Step 2: Copy the project to the server

The easiest way is GitHub: put the project in a repository, then on the server run `git clone <your-repo-url> cozypdf`.

Or copy it straight from your own computer (replace the user and address with your server's):

```bash
rsync -av --exclude .venv --exclude .git cozypdf/ user@192.168.1.50:~/cozypdf/
```

### Step 3: Install and try it

On the server:

```bash
cd ~/cozypdf
uv sync --no-dev
uv run fastapi run
```

`--no-dev` skips the tools that are only for working on the project.

Open `http://<server-ip>:8000` from another device on your home network. If it works, press **Ctrl+C** to stop it. Next, make it start by itself.

### Step 4: Keep it running with systemd

A systemd "service" starts the site when the server boots and starts it again if it crashes. Create the service file (replace `YOUR_USERNAME` with your username on the server, three times):

```bash
sudo nano /etc/systemd/system/cozypdf.service
```

```ini
[Unit]
Description=CozyPDF
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/cozypdf
ExecStart=/home/YOUR_USERNAME/cozypdf/.venv/bin/fastapi run --host 127.0.0.1 --port 8000 --workers 2
Restart=always
# Stops one huge PDF from using all of the server's memory
MemoryMax=1G

[Install]
WantedBy=multi-user.target
```

`--host 127.0.0.1` means only the server itself can reach the site. That is what you want when a tunnel or Caddy (Step 5) sits in front of it. To open it from other devices on your home network without them, use `--host 0.0.0.0` instead. The service runs the program inside the project's `.venv`, so it must run as the same user who ran `uv sync`.

Start it and turn on start-at-boot:

```bash
sudo systemctl enable --now cozypdf
```

Useful commands:

```bash
sudo systemctl status cozypdf    # is it running?
journalctl -u cozypdf -f         # watch the logs (Ctrl+C to stop watching)
sudo systemctl restart cozypdf   # restart after you change the code
```

To update the site later: copy or `git pull` the new code into `~/cozypdf`, then restart the service. If `pyproject.toml` or `uv.lock` changed, run `uv sync --no-dev` first.

### Step 5: Make it reachable from the internet

Pick **one** of these.

#### Option A (recommended): Cloudflare Tunnel, no router changes

The server makes an outgoing connection to Cloudflare, and Cloudflare serves your site. You don't open any ports, your home IP address stays hidden, and HTTPS is automatic. It works even if your internet provider blocks incoming connections. It's free, but you need a **domain name that uses Cloudflare's DNS** (a domain costs roughly $10 a year).

1. Make a free account at https://dash.cloudflare.com and add your domain.
2. Open **Zero Trust → Networks → Tunnels** (menu names change now and then) and click **Create a tunnel**. Choose **Cloudflared** and give it a name.
3. Pick your server's system (for example **Debian**). The page shows the commands to install `cloudflared` and connect it with your private token. Copy them and run them on the server. The last one installs `cloudflared` as a service, so it also starts at boot.
4. In the tunnel's **Public Hostname** tab, add your hostname, for example `pdf.yourdomain.com`, with service type **HTTP** and URL **`localhost:8000`**.

Visit `https://pdf.yourdomain.com`.

**No domain yet?** After installing `cloudflared`, try a temporary link. It needs no account, and the address changes every time you restart it:

```bash
cloudflared tunnel --url http://localhost:8000
```

#### Option B: Port forwarding, no Cloudflare

1. Give the server a fixed address on your network (set a DHCP reservation in your router).
2. In your router, forward **ports 80 and 443** to the server.
3. Get a domain, or a free name from https://www.duckdns.org, that points to your home IP address.
4. Run a reverse proxy that handles HTTPS. [Caddy](https://caddyserver.com) is the easiest. Its whole config can be two lines (`pdf.yourdomain.com` and `reverse_proxy localhost:8000`) and it gets the HTTPS certificate for you.

This only works if your internet provider gives you a real public IP address. If you are behind CGNAT (common on mobile and some home internet), use Option A.

### Before you share the link

- **Memory:** `MemoryMax=1G` in the service file limits the site to 1 GB of RAM. Raise or lower it to match your machine.
- **Upload limit:** `MAX_FILE_SIZE_MB` in `main.py` is 50. Cloudflare's free plan allows uploads up to 100 MB, so this is fine.
- **Abuse:** anyone on the internet can use the tools. Consider adding rate limiting (the `slowapi` package) and keep an eye on the logs.
- **Keep it separate:** don't forward other ports on your server, and keep the operating system up to date.
