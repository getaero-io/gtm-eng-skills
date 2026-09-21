"""Offline workspace isolation checks. All cookies and workspace IDs are synthetic."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch


SPEC = importlib.util.spec_from_file_location("clay_extract", Path(__file__).with_name("clay-extract.py"))
clay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clay)

COOKIE = "claysession=synthetic-offline-fixture"
WORKSPACE = "101010"
OTHER_WORKSPACE = "202020"


class WorkspaceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous_cwd = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, previous_cwd)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.requests = types.ModuleType("requests")
        self.requests.get = Mock(return_value=types.SimpleNamespace(status_code=200))
        self.requests.Session = Mock(side_effect=AssertionError("Unexpected API session"))
        self.modules = patch.dict(sys.modules, {"requests": self.requests})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        for redirect in (contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr)):
            redirect.__enter__()
            self.addCleanup(redirect.__exit__, None, None, None)

    def saved_session(self, workspace=OTHER_WORKSPACE):
        record = {"cookie": COOKIE, "savedAt": time.time()}
        if workspace is not None:
            record["workspaceId"] = workspace
        Path(".clay-session.json").write_text(json.dumps(record))

    def main(self, *args):
        with patch.object(sys, "argv", ["clay-extract.py", *args]):
            clay.main()

    def assert_no_network(self):
        self.requests.get.assert_not_called()
        self.requests.Session.assert_not_called()

    def test_workspace_selection_order(self):
        self.saved_session()
        self.assertEqual(clay.resolve_workspace(), OTHER_WORKSPACE)
        os.environ["CLAY_WORKSPACE_ID"] = "303030"
        self.assertEqual(clay.resolve_workspace(), "303030")
        url = f"https://app.clay.com/workspaces/{WORKSPACE}/workbooks/wb_example"
        self.assertEqual(clay.resolve_workspace(input_url=url), WORKSPACE)
        self.assertEqual(clay.resolve_workspace(workspace_id="404040"), "404040")
        self.assertEqual(clay.resolve_workspace(workspace_id=WORKSPACE, input_url=url), WORKSPACE)
        self.assert_no_network()

    def test_selected_url_is_only_workspace_used_for_cookie_validation(self):
        self.saved_session()
        os.environ["CLAY_WORKSPACE_ID"] = "303030"
        url = f"https://app.clay.com/workspaces/{WORKSPACE}/workbooks/wb_example/tables/t_example"
        with patch.object(clay, "ClayAPI") as api, patch.object(clay, "print_summary"), patch.object(clay, "save_extract"):
            self.main(url)
            api.return_value.extract_table.assert_called_once_with("t_example")
        self.requests.get.assert_called_once_with(
            "https://api.clay.com/v3/actions",
            params={"workspaceId": WORKSPACE},
            headers={"accept": "application/json", "cookie": COOKIE, "origin": "https://app.clay.com"},
            timeout=10,
        )
        self.assertEqual(json.loads(Path(".clay-session.json").read_text())["workspaceId"], WORKSPACE)
        self.assertNotIn(COOKIE, self.stdout.getvalue() + self.stderr.getvalue())

    def test_explicit_workspace_selects_name_search_and_validation(self):
        self.saved_session()
        with patch.object(clay, "ClayAPI") as api, patch.object(clay, "print_summary"), patch.object(clay, "save_extract"):
            api.return_value.search_workbooks.return_value = [{"id": "wb_example", "name": "Example"}]
            api.return_value.list_workbook_tables.return_value = [{"id": "t_example", "name": "Example"}]
            self.main("--workspace", WORKSPACE, "Example")
            api.return_value.search_workbooks.assert_called_once_with(WORKSPACE, "Example")
        self.assertEqual(self.requests.get.call_args.kwargs["params"], {"workspaceId": WORKSPACE})

    def test_missing_workspace_does_not_probe_legacy_session(self):
        self.saved_session(workspace=None)
        with self.assertRaises(SystemExit):
            self.main("t_example")
        self.assert_no_network()

    def test_invalid_or_conflicting_workspace_stops_before_network(self):
        self.saved_session()
        cases = [
            ["--workspace", "", "t_example"],
            ["--workspace", "0", "t_example"],
            ["--workspace", "not-an-id", "t_example"],
            ["--workspace", "101010&workspaceId=202020", "t_example"],
            [f"https://app.clay.com/workspaces/invalid/workbooks/wb_example"],
            ["https://app.clay.com/workspaces"],
            ["--workspace", WORKSPACE, f"https://app.clay.com/workspaces/{OTHER_WORKSPACE}/workbooks/wb_example"],
            ["--workspace", WORKSPACE, f"/workspaces/{OTHER_WORKSPACE}/home/f_example"],
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.main(*args)
            self.assert_no_network()

    def test_invalid_environment_does_not_fall_back_to_saved_workspace(self):
        self.saved_session()
        os.environ["CLAY_WORKSPACE_ID"] = "not-an-id"
        with self.assertRaises(SystemExit):
            self.main("t_example")
        self.assert_no_network()

    def test_low_level_session_check_rejects_invalid_selection(self):
        for value in (None, "", "0", "-1", "1?other=2", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                clay.test_session(COOKIE, value)
        self.assert_no_network()

    def test_auth_infers_caller_workspace_from_pasted_curl(self):
        curl = f"curl 'https://api.clay.com/v3/actions?workspaceId={WORKSPACE}' -b '{COOKIE}'"
        with patch("builtins.input", side_effect=[curl, ""]):
            self.main("--auth")
        self.assertEqual(self.requests.get.call_args.kwargs["params"], {"workspaceId": WORKSPACE})
        self.assertEqual(json.loads(Path(".clay-session.json").read_text())["workspaceId"], WORKSPACE)
        self.assertNotIn(COOKIE, self.stdout.getvalue() + self.stderr.getvalue())

    def test_auth_without_workspace_does_not_probe(self):
        curl = f"curl 'https://api.clay.com/v3/tables/t_example' -b '{COOKIE}'"
        with patch("builtins.input", side_effect=[curl, ""]), self.assertRaises(SystemExit):
            self.main("--auth")
        self.assert_no_network()
        self.assertFalse(Path(".clay-session.json").exists())

    def test_auth_referer_inference_and_conflict_detection_are_offline(self):
        curl = f"curl 'https://api.clay.com/v3/tables/t_example' -H 'referer: https://app.clay.com/workspaces/{WORKSPACE}/'"
        self.assertEqual(clay.workspace_from_curl(curl), WORKSPACE)
        conflicting = curl + f" -H 'x-example: https://api.clay.com/v3/actions?workspaceId={OTHER_WORKSPACE}'"
        with self.assertRaises(ValueError):
            clay.resolve_workspace(curl_str=conflicting)
        self.assert_no_network()

    def test_session_permissions_and_gitignore_creation(self):
        clay.save_session(COOKIE, WORKSPACE)
        session = Path(".clay-session.json")
        self.assertEqual(stat.S_IMODE(session.stat().st_mode), 0o600)
        self.assertIn(".clay-session.json", Path(".gitignore").read_text().splitlines())
        session.chmod(0o644)
        clay.save_session(COOKIE, WORKSPACE)
        self.assertEqual(stat.S_IMODE(session.stat().st_mode), 0o600)
        self.assertEqual(Path(".gitignore").read_text().splitlines().count(".clay-session.json"), 1)
        self.assertNotIn(COOKIE, self.stdout.getvalue() + self.stderr.getvalue())
        self.assert_no_network()


if __name__ == "__main__":
    unittest.main()
