import json
import re
from html import escape


METHOD_COLORS = {
    "GET": "#0f766e",
    "POST": "#1d4ed8",
    "PUT": "#a16207",
    "PATCH": "#7c3aed",
    "DELETE": "#b91c1c",
}


def render_docs_html(app) -> str:
    routes = [route.describe() for route in app.routes]
    nav = "\n".join(render_nav_item(route, index) for index, route in enumerate(routes))
    cards = "\n".join(render_route_card(route, index) for index, route in enumerate(routes))
    if not cards:
        cards = "<section class='empty'>No routes registered yet.</section>"
    logo = f"<img src='{escape(app.config.docs_logo_url)}' alt='QuickAPI logo' class='brand-logo'>" if app.config.docs_logo_url else ""
    favicon = f"<link rel='icon' href='{escape(app.config.docs_favicon_url)}'>" if app.config.docs_favicon_url else ""
    app_name = escape(app.config.name)

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {favicon}
  <title>{app_name} Docs</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #64748b;
      --line: #d7e0ea;
      --soft: #eef4f8;
      --dark: #08111f;
      --green: #087f45;
      --green-bg: #dcfce7;
      --red: #b42318;
      --red-bg: #fee2e2;
      --blue: #0b63ce;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }}
    header {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 22px clamp(16px, 4vw, 44px);
      background: var(--dark);
      color: white;
      border-bottom: 4px solid #08b6d8;
    }}
    .brand-logo {{
      width: 52px;
      height: 52px;
      border-radius: 12px;
      object-fit: cover;
      flex: 0 0 auto;
    }}
    h1 {{ margin: 0; font-size: clamp(24px, 4vw, 38px); letter-spacing: 0; }}
    .tagline {{ margin: 5px 0 0; color: #bfefff; font-size: 14px; }}
    .shell {{
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      gap: 18px;
      max-width: 1380px;
      margin: 0 auto;
      padding: 18px clamp(12px, 3vw, 28px) 48px;
    }}
    aside {{
      position: sticky;
      top: 14px;
      align-self: start;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 14px 36px rgba(15, 23, 42, .06);
    }}
    .side-head {{ padding: 14px; border-bottom: 1px solid var(--line); background: #fbfdff; }}
    .side-head strong {{ display: block; font-size: 15px; }}
    .side-head span {{ color: var(--muted); font-size: 12px; }}
    nav a {{
      display: grid;
      grid-template-columns: 58px minmax(0, 1fr);
      gap: 8px;
      padding: 10px 12px;
      color: var(--ink);
      text-decoration: none;
      border-bottom: 1px solid var(--line);
    }}
    nav a:hover {{ background: #f8fbff; }}
    .method {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 56px;
      height: 28px;
      border-radius: 5px;
      color: white;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0;
    }}
    .path, code {{ font-family: Consolas, Menlo, monospace; }}
    .path {{ overflow-wrap: anywhere; font-weight: 800; }}
    .overview {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }}
    .metric, .endpoint {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 14px 36px rgba(15, 23, 42, .06);
    }}
    .metric {{ padding: 14px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 22px; }}
    .endpoint {{ margin-bottom: 14px; overflow: hidden; }}
    .endpoint > summary {{
      display: grid;
      grid-template-columns: 70px minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      padding: 14px;
      cursor: pointer;
      list-style: none;
      border-bottom: 1px solid var(--line);
    }}
    .endpoint > summary::-webkit-details-marker {{ display: none; }}
    .handler {{ color: var(--muted); font-size: 13px; white-space: nowrap; }}
    .section {{ padding: 14px; border-bottom: 1px solid var(--line); }}
    .section-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .section-title h2 {{ margin: 0; font-size: 15px; }}
    .hint {{ color: var(--muted); font-size: 13px; line-height: 1.5; }}
    .url-box {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      overflow-wrap: anywhere;
    }}
    .grid-2 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }}
    label {{ display: block; margin: 10px 0 6px; color: var(--muted); font-size: 12px; font-weight: 900; text-transform: uppercase; }}
    input[type="text"], textarea {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      color: var(--ink);
      padding: 10px;
      font: 13px Consolas, Menlo, monospace;
    }}
    textarea {{ min-height: 145px; resize: vertical; }}
    input[type="file"] {{
      width: 100%;
      border: 1px dashed #9db2c6;
      border-radius: 8px;
      background: #fbfdff;
      padding: 12px;
    }}
    .format-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }}
    .format-grid label {{
      display: flex;
      align-items: center;
      gap: 7px;
      margin: 0;
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      color: var(--ink);
      text-transform: none;
      font-size: 13px;
    }}
    .send-row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 10px; }}
    button {{
      border: 0;
      border-radius: 7px;
      background: var(--dark);
      color: white;
      padding: 10px 14px;
      font-weight: 900;
      cursor: pointer;
    }}
    button.secondary {{ background: #e5edf5; color: var(--ink); }}
    .status-chip {{
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 900;
      white-space: nowrap;
    }}
    .ok-code {{ color: var(--green); background: var(--green-bg); }}
    .err-code {{ color: var(--red); background: var(--red-bg); }}
    pre {{
      min-height: 145px;
      max-height: 360px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 11px;
      background: #0f172a;
      color: #e2e8f0;
      font: 12px Consolas, Menlo, monospace;
    }}
    .response-ok, .result-ok {{ border-color: #22c55e; }}
    .response-error, .result-error {{ border-color: #ef4444; color: #fecaca; }}
    .links {{ display: grid; gap: 8px; margin-top: 10px; }}
    .download-link {{
      display: inline-flex;
      width: fit-content;
      align-items: center;
      gap: 8px;
      border-radius: 7px;
      background: var(--green);
      color: white;
      padding: 9px 11px;
      text-decoration: none;
      font-weight: 800;
    }}
    .empty {{ padding: 20px; background: white; border: 1px solid var(--line); border-radius: 8px; }}
    @media (max-width: 900px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{ position: static; }}
      .overview, .grid-2 {{ grid-template-columns: 1fr; }}
      .endpoint > summary {{ grid-template-columns: 1fr; }}
      .handler {{ white-space: normal; }}
    }}
    @media (max-width: 560px) {{
      header {{ align-items: flex-start; }}
      .format-grid {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    {logo}
    <div>
      <h1>{app_name} Docs</h1>
      <p class="tagline">Swagger-style QuickAPI console: choose an endpoint, fill request data, send it, and inspect the real response.</p>
    </div>
  </header>
  <div class="shell">
    <aside>
      <div class="side-head">
        <strong>Endpoints</strong>
        <span>{len(routes)} routes on this API</span>
      </div>
      <nav>{nav}</nav>
    </aside>
    <main>
      <section class="overview">
        <div class="metric"><span>Base URL</span><strong id="baseUrl">loading</strong></div>
        <div class="metric"><span>Request style</span><strong>JSON + File</strong></div>
        <div class="metric"><span>Engine</span><strong>QuickAPI</strong></div>
      </section>
      {cards}
    </main>
  </div>
  <script>
    const byteLabel = (value) => {{
      if (!value) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB'];
      const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
      return `${{(value / Math.pow(1024, index)).toFixed(index ? 1 : 0)}} ${{units[index]}}`;
    }};

    const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {{
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error || new Error('File could not be read'));
      reader.readAsDataURL(file);
    }});

    document.querySelector('#baseUrl').textContent = window.location.origin;

    document.querySelectorAll('.endpoint').forEach((card) => {{
      updatePreview(card);
      card.querySelectorAll('input, textarea').forEach((input) => {{
        input.addEventListener('input', () => updatePreview(card));
        input.addEventListener('change', () => updatePreview(card));
      }});
    }});

    function buildPath(card) {{
      let path = card.dataset.path;
      card.querySelectorAll('[data-param-name]').forEach((input) => {{
        const raw = input.value.trim();
        const name = input.dataset.paramName;
        const tokenPath = '{' + name + ':path}';
        const tokenNormal = '{' + name + '}';
        path = path.split(tokenPath).join(raw || input.placeholder || name).split(tokenNormal).join(encodeURIComponent(raw || input.placeholder || name));
      }});
      return path;
    }}

    function buildQuery(card) {{
      const query = card.querySelector('[data-role="query"]')?.value.trim();
      if (!query) return '';
      const params = new URLSearchParams();
      query.split('\\n').map((line) => line.trim()).filter(Boolean).forEach((line) => {{
        const parts = line.split('=');
        params.append(parts.shift().trim(), parts.join('=').trim());
      }});
      const text = params.toString();
      return text ? `?${{text}}` : '';
    }}

    function updatePreview(card) {{
      const url = new URL(buildPath(card) + buildQuery(card), window.location.origin);
      card.querySelector('[data-role="url"]').textContent = url.href;
    }}

    function selectedFormats(card) {{
      return Array.from(card.querySelectorAll('[data-role="format"]:checked')).map((item) => item.value);
    }}

    async function quickapiTry(button) {{
      const card = button.closest('.endpoint');
      const method = card.dataset.method;
      const result = card.querySelector('[data-role="response"]');
      const status = card.querySelector('[data-role="status"]');
      const links = card.querySelector('[data-role="links"]');
      const bodyEl = card.querySelector('[data-role="body"]');
      const fileEl = card.querySelector('[data-role="file"]');

      links.innerHTML = '';
      status.textContent = 'Sending';
      status.className = 'status-chip';
      result.className = '';
      result.textContent = 'Sending request...';

      try {{
        let path = buildPath(card) + buildQuery(card);
        const options = {{ method, headers: {{ Accept: 'application/json' }} }};
        if (!['GET', 'DELETE'].includes(method)) {{
          options.headers['Content-Type'] = 'application/json';
          let body = JSON.parse(bodyEl.value.trim() || '{{}}');
          if (fileEl && fileEl.files.length) {{
            const file = fileEl.files[0];
            body.filename = file.name;
            body.data_base64 = await readFileAsDataUrl(file);
            const formats = selectedFormats(card);
            if (formats.length) body.target_formats = formats;
            bodyEl.value = JSON.stringify(body, null, 2);
          }}
          options.body = JSON.stringify(body);
        }}

        const response = await fetch(path, options);
        const text = await response.text();
        let payload;
        try {{ payload = JSON.parse(text); }} catch {{ payload = text; }}
        status.textContent = `${{response.status}} ${{response.ok ? 'OK' : 'ERROR'}}`;
        status.className = response.ok ? 'status-chip ok-code' : 'status-chip err-code';
        result.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
        result.className = response.ok ? 'response-ok' : 'response-error';
        renderDownloads(payload, links);
      }} catch (error) {{
        status.textContent = 'Request error';
        status.className = 'status-chip err-code';
        result.className = 'response-error';
        result.textContent = JSON.stringify({{ ok: false, message: error.message, hint: 'Check path values, query lines, and JSON body.' }}, null, 2);
      }}
    }}

    function renderDownloads(payload, container) {{
      if (!payload || typeof payload !== 'object' || !payload.data) return;
      const files = Array.isArray(payload.data.files) ? payload.data.files : (payload.data.download_url ? [payload.data] : []);
      files.forEach((file) => {{
        if (!file.download_url) return;
        const link = document.createElement('a');
        link.href = file.download_url;
        link.download = file.filename || '';
        link.className = 'download-link';
        link.textContent = `${{(file.format || 'file').toUpperCase()}} download ${{file.size_bytes ? '- ' + byteLabel(file.size_bytes) : ''}}`;
        container.appendChild(link);
      }});
    }}

    function copyCurl(button) {{
      const card = button.closest('.endpoint');
      const method = card.dataset.method;
      const url = card.querySelector('[data-role="url"]').textContent;
      const bodyEl = card.querySelector('[data-role="body"]');
      let command = `curl -X ${{method}} "${{url}}"`;
      if (!['GET', 'DELETE'].includes(method)) {{
        command += ` -H "Content-Type: application/json" -d '${{(bodyEl.value || '{{}}').replaceAll("'", "\\\\'")}}'`;
      }}
      navigator.clipboard?.writeText(command);
      button.textContent = 'Copied';
      setTimeout(() => button.textContent = 'Copy curl', 900);
    }}
  </script>
</body>
</html>"""
    return (
        html.replace("{favicon}", favicon)
        .replace("{app_name}", app_name)
        .replace("{logo}", logo)
        .replace("{len(routes)}", str(len(routes)))
        .replace("{nav}", nav)
        .replace("{cards}", cards)
        .replace("{{", "{")
        .replace("}}", "}")
    )


def render_nav_item(route: dict, index: int) -> str:
    return (
        f"<a href='#op-{index}'>"
        f"<span class='method' style='background:{method_color(route['method'])}'>{escape(route['method'])}</span>"
        f"<span class='path'>{escape(route['path'])}</span>"
        "</a>"
    )


def render_route_card(route: dict, index: int) -> str:
    method = route["method"]
    path = route["path"]
    errors = route["errors"] or [400, 404, 422, 429, 500]
    params = route_params(path)
    body = request_example(route)
    param_inputs = render_param_inputs(params)
    file_tool = render_file_tool(path)
    body_panel = render_body_panel(method, body, file_tool)
    error_badges = " ".join(f"<span class='status-chip err-code'>{code}</span>" for code in errors)
    meta = {
        "handler": route["name"],
        "auth": route["auth"],
        "ml_check": route["ml_check"],
        "rate_limit": route["rate_limit"],
        "native": route["native"],
    }
    open_attr = " open" if index == 0 or path == "/api/convert" else ""
    return f"""
      <details class="endpoint" id="op-{index}" data-method="{escape(method)}" data-path="{escape(path)}"{open_attr}>
        <summary>
          <span class="method" style="background:{method_color(method)}">{escape(method)}</span>
          <span class="path">{escape(path)}</span>
          <span class="handler">{escape(route['name'])}</span>
        </summary>
        <section class="section">
          <div class="section-title">
            <h2>Request</h2>
            <span class="status-chip ok-code">200 OK</span>
          </div>
          <div class="url-box">
            <span class="method" style="background:{method_color(method)}">{escape(method)}</span>
            <code data-role="url">{escape(path)}</code>
          </div>
          <div class="grid-2">
            <div>
              {param_inputs}
              <label>Query parameters</label>
              <textarea data-role="query" spellcheck="false" placeholder="Example:&#10;page=1&#10;limit=20"></textarea>
            </div>
            <div>
              <label>Route metadata</label>
              <pre>{escape(json.dumps(meta, indent=2))}</pre>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="section-title">
            <h2>Try it</h2>
            <span class="hint">{request_note(method, path)}</span>
          </div>
          {body_panel}
          <div class="send-row">
            <button type="button" aria-label="Send JSON Request" onclick="quickapiTry(this)">Send request</button>
            <button type="button" class="secondary" onclick="copyCurl(this)">Copy curl</button>
            <span class="status-chip" data-role="status">Not sent</span>
          </div>
        </section>
        <section class="section">
          <div class="section-title">
            <h2>Response</h2>
            <span>{error_badges}</span>
          </div>
          <pre data-role="response">Send a request to see the real HTTP response here.</pre>
          <div class="links" data-role="links"></div>
        </section>
      </details>"""


def render_param_inputs(params: list[str]) -> str:
    if not params:
        return "<label>Path parameters</label><p class='hint'>No path parameters for this endpoint.</p>"
    controls = ["<label>Path parameters</label>"]
    for param in params:
        controls.append(
            f"<input type='text' data-param-name='{escape(param)}' placeholder='{escape(example_param(param))}' "
            f"aria-label='Path parameter {escape(param)}'>"
        )
    return "\n".join(controls)


def render_body_panel(method: str, body: str, file_tool: str) -> str:
    if method in {"GET", "DELETE"}:
        return "<p class='hint'>This endpoint sends no JSON body. Fill path or query fields above, then send the request.</p>"
    return f"""
      {file_tool}
      <label>JSON body</label>
      <textarea data-role="body" spellcheck="false">{escape(body)}</textarea>"""


def render_file_tool(path: str) -> str:
    if path != "/api/convert":
        return ""
    return """
      <div class="grid-2">
        <div>
          <label>Audio file</label>
          <input type="file" data-role="file" accept="audio/*,.mp3,.wav,.flac,.ogg,.opus,.m4a,.aac,.wma,.aiff,.aif,.webm">
          <p class="hint">Choose an audio file here; docs will place filename and base64 data into the JSON body before sending.</p>
        </div>
        <div>
          <label>Target formats</label>
          <div class="format-grid">
            <label><input data-role="format" type="checkbox" value="wav" checked> WAV</label>
            <label><input data-role="format" type="checkbox" value="flac" checked> FLAC</label>
            <label><input data-role="format" type="checkbox" value="mp3"> MP3</label>
            <label><input data-role="format" type="checkbox" value="ogg"> OGG</label>
            <label><input data-role="format" type="checkbox" value="m4a"> M4A</label>
            <label><input data-role="format" type="checkbox" value="opus"> OPUS</label>
          </div>
        </div>
      </div>"""


def request_note(method: str, path: str) -> str:
    if path == "/api/convert":
        return "Pick an audio file, choose formats, then send. QuickAPI will return download links."
    if method in {"GET", "DELETE"}:
        return "No body needed."
    return "Edit JSON and send it with Content-Type: application/json."


def request_example(route: dict) -> str:
    if route["method"] not in {"POST", "PUT", "PATCH"}:
        return ""
    path = route["path"]
    name = route["name"]
    if path == "/api/convert":
        return json.dumps(
            {
                "filename": "song.mp3",
                "target_formats": ["wav", "flac"],
                "data_base64": "<choose a file above or paste base64 here>",
            },
            indent=2,
        )
    if path == "/api/batch":
        return json.dumps({"requests": [{"method": "GET", "path": "/api/health"}]}, indent=2)
    if "cart" in path:
        return json.dumps({"product_id": "trend-1", "quantity": 1}, indent=2)
    if name == "echo":
        return json.dumps({"message": "Hello QuickAPI"}, indent=2)
    return json.dumps({"hello": "quickapi"}, indent=2)


def route_params(path: str) -> list[str]:
    return re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)(?::path)?}", path)


def example_param(param: str) -> str:
    if param.endswith("path") or param == "file_path":
        return "example.wav"
    if param in {"id", "product_id"}:
        return "1"
    return param


def method_color(method: str) -> str:
    return METHOD_COLORS.get(method, "#334155")
