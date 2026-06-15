# QuickAPI Install

## Requirements

- Python 3.10+
- Git

## Clone And Install

```bash
git clone https://github.com/emrebe06/QuickAPI.git
cd QuickAPI
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -e .
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -e .
```

## Smoke Test

Create `main.py`:

```python
from quickapi import QuickAPI, q

app = QuickAPI("Demo API")

@app.get("/ping")
def ping():
    return q.ok({"pong": True})
```

Run:

```bash
quickapi run main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/ping
```
