#!/usr/bin/env python3
"""
Clay Table Config Extractor

Extracts Clay table configs (fields, prompts, action settings, sample records)
via Clay's internal API.

Usage:
    # First time: paste a cURL from Chrome DevTools to save your session
    python3 scripts/clay-extract.py --auth
    # (In Chrome: DevTools → Network → any api.clay.com request → Copy as cURL → paste)

    # Extract a specific table
    python3 scripts/clay-extract.py 'https://app.clay.com/workspaces/<WORKSPACE_ID>/workbooks/wb_xxx/tables/t_xxx'

    # List all tables in a workspace folder
    python3 scripts/clay-extract.py 'https://app.clay.com/workspaces/<WORKSPACE_ID>/home/f_xxx'

    # Extract by table ID directly
    python3 scripts/clay-extract.py --workspace <WORKSPACE_ID> t_xxx

Session is saved to .clay-session.json and reused until it expires.
Output goes to tmp/clay_extract_<table_name>.json (won't overwrite existing files).
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SESSION_FILE = Path(".clay-session.json")

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def extract_cookie_from_curl(curl_str: str) -> str | None:
    """Parse a 'Copy as cURL' string to extract the Cookie header."""
    # Match -b 'cookie...' or --cookie 'cookie...' or -H 'cookie: ...'
    patterns = [
        r"-b\s+'([^']+)'",
        r"-b\s+\"([^\"]+)\"",
        r"--cookie\s+'([^']+)'",
        r"--cookie\s+\"([^\"]+)\"",
        r"-H\s+'[Cc]ookie:\s*([^']+)'",
        r'-H\s+"[Cc]ookie:\s*([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, curl_str)
        if match:
            cookie = match.group(1).strip()
            if "claysession" in cookie:
                return cookie
    return None


def validate_workspace_id(workspace_id) -> str:
    """Reject missing or malformed IDs before any authenticated request."""
    if isinstance(workspace_id, bool):
        raise ValueError("Workspace ID must be a positive decimal number.")
    value = str(workspace_id) if workspace_id is not None else ""
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise ValueError("Select a valid workspace with --workspace, a full Clay URL, or CLAY_WORKSPACE_ID.")
    return value


def workspace_from_url(value: str | None) -> str | None:
    """Read a workspace only from a full Clay URL, without fetching it."""
    if not value:
        return None
    if value.startswith("/") and not value.startswith("//"):
        raise ValueError("Use a full Clay URL rather than a relative path.")
    parsed = urlparse(value)
    if "://" not in value and not value.startswith("//") and parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.scheme and not parsed.netloc:
        return None
    if (parsed.scheme != "https" or parsed.hostname not in {"app.clay.com", "api.clay.com"}
            or parsed.username or parsed.password):
        raise ValueError("Use a full HTTPS URL on app.clay.com or api.clay.com.")
    candidates = parse_qs(parsed.query, keep_blank_values=True).get("workspaceId", [])
    match = re.search(r"/workspaces/([^/]*)(?:/|$)", parsed.path)
    if match:
        candidates.append(match.group(1))
    elif re.search(r"/workspaces(?:/|$)", parsed.path):
        raise ValueError("The Clay URL is missing its workspace ID.")
    ids = {validate_workspace_id(candidate) for candidate in candidates}
    if len(ids) > 1:
        raise ValueError("The Clay URL contains conflicting workspace IDs.")
    return next(iter(ids), None)


def workspace_from_curl(curl_str: str) -> str | None:
    """Infer from Clay request/referer URLs; never execute the pasted command."""
    urls = re.findall(r"https://(?:app|api)\.clay\.com/[^\s'\"]+", curl_str)
    ids = {workspace for url in urls if (workspace := workspace_from_url(url)) is not None}
    if len(ids) > 1:
        raise ValueError("The pasted cURL contains conflicting workspace IDs.")
    return next(iter(ids), None)


def resolve_workspace(workspace_id=None, input_url=None, curl_str=None) -> str:
    """Order: explicit flag, input/cURL URL, environment, private saved session."""
    url_workspace = workspace_from_url(input_url)
    curl_workspace = workspace_from_curl(curl_str) if curl_str else None
    url_ids = {value for value in (url_workspace, curl_workspace) if value is not None}
    if len(url_ids) > 1:
        raise ValueError("The input URL and pasted cURL select different workspaces.")
    selected_url_workspace = next(iter(url_ids), None)
    if workspace_id is not None:
        selected = validate_workspace_id(workspace_id)
        if selected_url_workspace is not None and selected_url_workspace != selected:
            raise ValueError("--workspace conflicts with the workspace in the supplied URL or cURL.")
        return selected
    if selected_url_workspace is not None:
        return selected_url_workspace
    if "CLAY_WORKSPACE_ID" in os.environ:
        return validate_workspace_id(os.environ["CLAY_WORKSPACE_ID"])
    saved = load_saved_session()
    return validate_workspace_id(saved.get("workspaceId") if saved else None)


def save_session(cookie: str, workspace_id: str):
    """Persist the cookie and caller-selected workspace in a private file."""
    workspace_id = validate_workspace_id(workspace_id)
    gitignore = Path(".gitignore")
    content = gitignore.read_text() if gitignore.exists() else ""
    if ".clay-session.json" not in content.splitlines():
        with gitignore.open("a") as f:
            f.write("\n.clay-session.json\n")
    fd = os.open(SESSION_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump({"cookie": cookie, "workspaceId": workspace_id, "savedAt": time.time()}, f, indent=2)
    print(f"[OK] Session saved to {SESSION_FILE}")


def load_saved_session() -> dict | None:
    """Load the private session record if its cookie is still fresh."""
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text())
        cookie = data.get("cookie", "")
        saved_at = data.get("savedAt", 0)
        if time.time() - saved_at > 20 * 3600:
            return None
        if "claysession" not in cookie:
            return None
        return data
    except Exception:
        return None


def get_saved_session() -> str | None:
    data = load_saved_session()
    return data["cookie"] if data else None


def test_session(cookie: str, workspace_id: str) -> bool:
    """Check the session only against the caller-selected workspace."""
    workspace_id = validate_workspace_id(workspace_id)
    import requests
    try:
        # /v3/users/me returns 403; use workspace resources as a lightweight auth check
        resp = requests.get(
            "https://api.clay.com/v3/actions",
            params={"workspaceId": workspace_id},
            headers={"accept": "application/json", "cookie": cookie, "origin": "https://app.clay.com"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def get_clay_cookie_from_env() -> str | None:
    """Read CLAY_COOKIE from .env.deepline if it exists."""
    env_file = Path(".env.deepline")
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("CLAY_COOKIE="):
            val = line[len("CLAY_COOKIE="):]
            if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]
            return val
    return None


def do_auth(workspace_id=None, input_url=None):
    """Interactive auth: user pastes a cURL command."""
    print("Paste a cURL command from Chrome DevTools (any api.clay.com request):")
    print("  Chrome → DevTools (Cmd+Option+I) → Network → click any api.clay.com request")
    print("  → Right-click → Copy → Copy as cURL")
    print()

    lines = []
    print("Paste here (press Enter twice when done):")
    empty_count = 0
    while True:
        try:
            line = input()
            if not line.strip():
                empty_count += 1
                if empty_count >= 1 and lines:
                    break
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break

    curl_str = " ".join(lines)
    cookie = extract_cookie_from_curl(curl_str)

    if not cookie:
        print("[FAIL] Could not find claysession in the pasted cURL.")
        print("  Make sure you're copying from an api.clay.com request while logged in.")
        sys.exit(1)

    selected_workspace = resolve_workspace(workspace_id, input_url, curl_str)
    if test_session(cookie, selected_workspace):
        save_session(cookie, selected_workspace)
        print("[OK] Session is valid. You can now run extraction commands.")
    else:
        print("[FAIL] Cookie found but session is invalid/expired. Try copying a fresh cURL.")
        sys.exit(1)


def get_cookie(workspace_id: str) -> str:
    """Get a valid Clay session cookie."""
    workspace_id = validate_workspace_id(workspace_id)
    # 1. Saved session
    cookie = get_saved_session()
    if cookie and test_session(cookie, workspace_id):
        saved = load_saved_session()
        if (saved or {}).get("workspaceId") != workspace_id:
            save_session(cookie, workspace_id)
        print("[OK] Using saved Clay session")
        return cookie

    # 2. .env.deepline
    cookie = get_clay_cookie_from_env()
    if cookie and test_session(cookie, workspace_id):
        print("[OK] Using Clay session from .env.deepline")
        save_session(cookie, workspace_id)
        return cookie

    # 3. Need auth
    print("[AUTH] No valid session found. Run with --auth first:")
    print(f"  python3 {sys.argv[0]} --auth")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Clay API client
# ---------------------------------------------------------------------------

class ClayAPI:
    BASE = "https://api.clay.com"

    def __init__(self, cookie: str):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "content-type": "application/json",
            "cookie": cookie,
            "origin": "https://app.clay.com",
            "referer": "https://app.clay.com/",
        })

    def get(self, path: str):
        resp = self.session.get(f"{self.BASE}{path}")
        if resp.status_code == 401:
            print(f"[FAIL] 401 on {path} — session expired. Run: python3 {sys.argv[0]} --auth")
            sys.exit(1)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: dict = None):
        resp = self.session.post(f"{self.BASE}{path}", json=body or {})
        if resp.status_code == 401:
            print(f"[FAIL] 401 on {path} — session expired. Run: python3 {sys.argv[0]} --auth")
            sys.exit(1)
        resp.raise_for_status()
        return resp.json()

    def get_table_config(self, table_id: str) -> dict:
        print(f"  Fetching table config for {table_id}...")
        return self.get(f"/v3/tables/{table_id}")

    def get_table_schema_v2(self, table_id: str, view_id: str) -> dict:
        print(f"  Fetching schema + example records...")
        return self.get(f"/v3/tables/{table_id}/views/{view_id}/table-schema-v2")

    def list_workspace_resources(self, workspace_id: str) -> dict:
        print(f"  Listing workspace {workspace_id} resources...")
        return self.post(f"/v3/workspaces/{workspace_id}/resources_v2/")

    def list_workbook_tables(self, workbook_id: str) -> list[dict]:
        """Get tables from a workbook (returns list of {id, name})."""
        print(f"  Listing tables in workbook {workbook_id}...")
        tables = self.get(f"/v3/workbooks/{workbook_id}/tables")
        if isinstance(tables, list):
            return [{"id": t["id"], "name": t.get("name", "")} for t in tables if "id" in t]
        return []

    def search_workbooks(self, workspace_id: str, query: str) -> list[dict]:
        """Search workspace workbooks by name (case-insensitive substring match)."""
        resources = self.list_workspace_resources(workspace_id)
        workbooks = [
            r for r in resources.get("resources", [])
            if r.get("resourceType") == "WORKBOOK"
        ]
        q = query.lower()
        matches = [wb for wb in workbooks if q in wb.get("name", "").lower()]
        return matches

    def extract_table(self, table_id: str) -> dict:
        config = self.get_table_config(table_id)
        table = config.get("table", config)
        view_id = table.get("firstViewId")

        result = {
            "_meta": {
                "extractedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "method": "clay-extract.py",
                "tableId": table_id,
            },
            "table": {
                "id": table.get("id"),
                "name": table.get("name"),
                "workbookId": table.get("workbookId"),
                "workspaceId": table.get("workspaceId"),
                "firstViewId": view_id,
                "tableSettings": table.get("tableSettings"),
            },
            "fields": [],
            "exampleRecords": [],
        }

        for f in table.get("fields", []):
            result["fields"].append({
                "id": f.get("id"),
                "name": f.get("name"),
                "type": f.get("type"),
                "actionType": f.get("actionType"),
                "inputFieldIds": f.get("inputFieldIds", []),
                "typeSettings": f.get("typeSettings"),
            })

        if view_id:
            try:
                schema_data = self.get_table_schema_v2(table_id, view_id)
                result["tableSchema"] = schema_data.get("tableSchema")
                result["exampleRecords"] = schema_data.get("exampleRecords", [])
            except Exception as e:
                print(f"  [WARN] Could not fetch schema-v2: {e}")

        return result


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_clay_input(arg: str, workspace_id: str | None = None):
    # Direct table ID
    if re.match(r"^t_[a-zA-Z0-9]+$", arg):
        return {"type": "table", "table_id": arg}

    # Direct workbook ID
    if re.match(r"^wb_[a-zA-Z0-9]+$", arg):
        return {"type": "workbook", "workbook_id": arg, "workspace_id": workspace_id}

    # URL parsing
    parsed = urlparse(arg)
    path = parsed.path

    if path.startswith("/"):
        table_match = re.search(r"/tables/(t_[a-zA-Z0-9]+)", path)
        if table_match:
            return {"type": "table", "table_id": table_match.group(1)}

        wb_match = re.search(r"/workspaces/(\d+)/workbooks/(wb_[a-zA-Z0-9]+)", path)
        if wb_match:
            return {"type": "workbook", "workspace_id": wb_match.group(1), "workbook_id": wb_match.group(2)}

        folder_match = re.search(r"/workspaces/(\d+)/home/(f_[a-zA-Z0-9]+)", path)
        if folder_match:
            return {"type": "folder", "workspace_id": folder_match.group(1), "folder_id": folder_match.group(2)}

        ws_match = re.search(r"/workspaces/(\d+)", path)
        if ws_match:
            return {"type": "workspace", "workspace_id": ws_match.group(1)}

    # Name-based search — anything that's not an ID or URL
    return {"type": "search", "query": arg, "workspace_id": workspace_id}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_extract(extract: dict, output_dir: Path):
    table_name = extract["table"]["name"] or extract["table"]["id"]
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", table_name).strip("_").lower()
    filename = f"clay_extract_{safe_name}.json"
    output_path = output_dir / filename

    if output_path.exists():
        i = 2
        while True:
            alt = output_dir / f"clay_extract_{safe_name}_{i}.json"
            if not alt.exists():
                output_path = alt
                break
            i += 1

    output_path.write_text(json.dumps(extract, indent=2, default=str))
    return output_path


def print_summary(extract: dict):
    table = extract["table"]
    fields = extract["fields"]
    records = extract.get("exampleRecords", [])

    print(f"\n{'='*60}")
    print(f"Table: {table['name']} ({table['id']})")
    print(f"Fields: {len(fields)}  |  Example records: {len(records)}")
    print(f"{'='*60}")

    for f in fields:
        ts = f.get("typeSettings") or {}
        action_key = ts.get("actionKey", "")
        ftype = f["type"]
        marker = ""
        if ftype == "action":
            marker = f" [{action_key}]"
        elif ftype == "source":
            marker = " [source]"
        print(f"  {f['id'][:20]:20s}  {ftype:8s}  {f['name'][:40]}{marker}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Extract Clay table configs in a selected workspace.")
    parser.add_argument("--auth", action="store_true", help="Save a session from a pasted cURL command")
    parser.add_argument("--workspace", help="Caller-selected numeric Clay workspace ID")
    parser.add_argument("query", nargs="*", help="Full Clay URL, table/workbook ID, or name search")
    args = parser.parse_args()
    arg = " ".join(args.query)
    try:
        if args.auth:
            do_auth(args.workspace, arg or None)
            return
        if not arg:
            parser.error("provide a Clay URL, table/workbook ID, or name search")
        workspace_id = resolve_workspace(args.workspace, arg)
    except ValueError as error:
        parser.error(str(error))

    output_dir = Path("tmp")
    output_dir.mkdir(exist_ok=True)

    info = parse_clay_input(arg, workspace_id)
    print(f"[INPUT] Parsed as: {info['type']}")

    cookie = get_cookie(workspace_id)
    api = ClayAPI(cookie)

    extracts = []

    if info["type"] == "table":
        extracts.append(api.extract_table(info["table_id"]))

    elif info["type"] == "workbook":
        tables = api.list_workbook_tables(info["workbook_id"])
        if not tables:
            print("  [FAIL] No tables found in workbook.")
            sys.exit(1)
        print(f"  Found {len(tables)} table(s)")
        for t in tables:
            print(f"\n--- Extracting: {t['name'] or t['id']} ---")
            try:
                extracts.append(api.extract_table(t["id"]))
            except Exception as e:
                print(f"  [ERROR] {t['id']}: {e}")

    elif info["type"] == "search":
        ws_id = info.get("workspace_id")
        if not ws_id:
            print("[FAIL] Name search requires a workspace ID.")
            print("  Use: python3 scripts/clay-extract.py --workspace <WORKSPACE_ID> \"Demo Requests\"")
            print("  Or provide a full Clay URL instead.")
            sys.exit(1)

        query = info["query"]
        print(f"  Searching workspace {ws_id} for \"{query}\"...")
        matches = api.search_workbooks(ws_id, query)

        if not matches:
            print(f"  No workbooks matching \"{query}\"")
            # Also search table names inside all workbooks
            print("  Searching table names...")
            resources = api.list_workspace_resources(ws_id)
            all_wbs = [r for r in resources.get("resources", []) if r.get("resourceType") == "WORKBOOK"]
            for wb in all_wbs:
                try:
                    tables = api.list_workbook_tables(wb["id"])
                    for t in tables:
                        if query.lower() in t.get("name", "").lower():
                            print(f"  Found table: {t['name']} in workbook \"{wb['name']}\"")
                            extracts.append(api.extract_table(t["id"]))
                except Exception:
                    pass
            if not extracts:
                print(f"  [FAIL] No workbooks or tables matching \"{query}\"")
                sys.exit(1)
        else:
            print(f"  Found {len(matches)} workbook(s):")
            for m in matches:
                print(f"    {m['id']} — {m['name']}")

            for wb in matches:
                tables = api.list_workbook_tables(wb["id"])
                for t in tables:
                    print(f"\n--- Extracting: {t['name'] or t['id']} (from \"{wb['name']}\") ---")
                    try:
                        extracts.append(api.extract_table(t["id"]))
                    except Exception as e:
                        print(f"  [ERROR] {t['id']}: {e}")

    elif info["type"] in ("workspace", "folder"):
        try:
            resources = api.list_workspace_resources(info["workspace_id"])
            workbook_ids = [
                r["id"] for r in resources.get("resources", [])
                if r.get("resourceType") == "WORKBOOK"
            ]
        except Exception as e:
            workbook_ids = []
            print(f"  [WARN] resources_v2 failed: {e}")

        if info["type"] == "folder":
            print(f"  [NOTE] Folder children aren't in the API response.")
            print(f"  Found {len(workbook_ids)} top-level workbooks.")
            if not workbook_ids:
                sys.exit(1)

        print(f"  Resolving {len(workbook_ids)} workbooks to tables...")
        table_ids = []
        for wb_id in workbook_ids:
            try:
                tables = api.list_workbook_tables(wb_id)
                table_ids.extend([t["id"] for t in tables])
            except Exception:
                pass

        if not table_ids:
            print("  [FAIL] No tables found.")
            sys.exit(1)

        print(f"  Found {len(table_ids)} table(s) total")
        for tid in table_ids:
            print(f"\n--- Extracting: {tid} ---")
            try:
                extracts.append(api.extract_table(tid))
            except Exception as e:
                print(f"  [ERROR] {tid}: {e}")

    if not extracts:
        print("\n[FAIL] No tables extracted.")
        sys.exit(1)

    for extract in extracts:
        print_summary(extract)
        path = save_extract(extract, output_dir)
        print(f"  Saved to: {path}")

    print(f"\n[DONE] Extracted {len(extracts)} table(s)")


if __name__ == "__main__":
    main()
