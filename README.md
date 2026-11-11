# CozyPDF

A free PDF toolbox built with FastAPI. Merge, split, rotate, compress, convert, watermark, number, protect and unlock PDFs. Files are processed in memory and never saved on the server.

## Run

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run fastapi run
```

Open http://127.0.0.1:8000.

## Test

```bash
uv run pytest
```
