import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from localizer import run

SCRIPT = Path(__file__).resolve().parents[1] / "localizer.py"

SIMPLE_CFG = """
PART
{
    name = testEngine
    title = Test Engine
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket
}
"""


def invoke(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        timeout=10,
    )
    result.stdout = result.stdout.decode("utf-8", errors="replace")
    result.stderr = result.stderr.decode("utf-8", errors="replace")
    return result


class MissingArgsTests(unittest.TestCase):
    def test_no_args_exits_nonzero_with_usage(self):
        result = invoke()
        self.assertNotEqual(result.returncode, 0)
        usage = result.stdout + result.stderr
        self.assertIn("--mod", usage)
        self.assertIn("--prefix", usage)

    def test_missing_mod_exits_nonzero_with_usage(self):
        result = invoke("--prefix", "MYMOD")
        self.assertNotEqual(result.returncode, 0)
        usage = result.stdout + result.stderr
        self.assertIn("--mod", usage)

    def test_missing_prefix_exits_nonzero_with_usage(self):
        result = invoke("--mod", "some-dir")
        self.assertNotEqual(result.returncode, 0)
        usage = result.stdout + result.stderr
        self.assertIn("--prefix", usage)

    def test_dry_run_flag_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_mod = Path(tmp)
            result = invoke(
                "--mod", str(empty_mod), "--prefix", "MYMOD", "--dry-run"
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Found", result.stdout)
        self.assertIn("PART", result.stdout.upper())


class RunAndDryRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mod = self.root / "mod"
        self.mod.mkdir()
        (self.mod / "part.cfg").write_text(SIMPLE_CFG, encoding="utf-8")
        self.tool_root = self.root / "tool"
        self.tool_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self, path):
        files = {}
        if not path.exists():
            return files
        for item in path.rglob("*"):
            if item.is_file():
                files[item.relative_to(path).as_posix()] = item.read_bytes()
        return files

    def test_real_run_writes_three_localization_artifacts(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run(str(self.mod), "MYMOD", dry_run=False, tool_root=self.tool_root)

        loc = self.mod / "Localization"
        self.assertTrue((loc / "en-us.cfg").is_file())
        self.assertTrue((loc / "zh-cn.cfg").is_file())
        self.assertTrue((loc / "translation.csv").is_file())
        en = (loc / "en-us.cfg").read_text(encoding="utf-8")
        self.assertIn("#LOC_MYMOD_testEngine_title", en)
        self.assertIn("Test Engine", en)

    def _dry_run(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run(str(self.mod), "MYMOD", dry_run=True, tool_root=self.tool_root)
        return buf.getvalue()

    def test_dry_run_prints_part_count_and_keys_and_writes_nothing(self):
        before_mod = self.snapshot(self.mod)
        before_tool = self.snapshot(self.tool_root)

        out = self._dry_run()

        self.assertIn("1", out)
        self.assertIn("PART", out.upper())
        self.assertIn("#LOC_MYMOD_testEngine_title", out)
        self.assertIn("#LOC_MYMOD_testEngine_description", out)
        self.assertIn("#LOC_MYMOD_testEngine_manufacturer", out)
        self.assertIn("#LOC_MYMOD_testEngine_tags", out)

        self.assertEqual(self.snapshot(self.mod), before_mod)
        self.assertFalse((self.mod / "Localization").exists())
        self.assertEqual(self.snapshot(self.tool_root), before_tool)
        self.assertFalse((self.tool_root / "data").exists())

    def test_dry_run_does_not_modify_existing_data_dir(self):
        data_dir = self.tool_root / "data"
        data_dir.mkdir()
        (data_dir / "keep-me.txt").write_bytes(b"untouched")
        before_tool = self.snapshot(self.tool_root)

        self._dry_run()

        self.assertEqual(self.snapshot(self.tool_root), before_tool)


class StableKeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mod = self.root / "mod"
        self.mod.mkdir()
        self.tool_root = self.root / "tool"
        self.tool_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _capture_run(self, dry_run=True):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run(str(self.mod), "BDB", dry_run=dry_run, tool_root=self.tool_root)
        return buf.getvalue()

    def test_cross_file_same_name_parts_get_posix_sorted_keys(self):
        (self.mod / "z_last.cfg").write_text(
            """
PART
{
    name = engine
    title = Last Engine
}
""",
            encoding="utf-8",
        )
        parts_dir = self.mod / "Parts"
        parts_dir.mkdir()
        (parts_dir / "engine.cfg").write_text(
            """
PART
{
    name = engine
    title = First Engine
}
""",
            encoding="utf-8",
        )

        out = self._capture_run(dry_run=True)

        self.assertIn("#LOC_BDB_engine_title", out)
        self.assertIn("#LOC_BDB_engine_title__z_last", out)
        self.assertIn("LOC_KEY_DUPLICATE", out)
        self.assertNotIn("#LOC_BDB_engine_title__Parts_engine", out)

        self._capture_run(dry_run=False)
        en = (self.mod / "Localization" / "en-us.cfg").read_text(encoding="utf-8")
        self.assertIn("#LOC_BDB_engine_title = First Engine", en)
        self.assertIn("#LOC_BDB_engine_title__z_last = Last Engine", en)

    def test_in_file_same_name_parts_get_numbered_suffixes(self):
        (self.mod / "twins.cfg").write_text(
            """
PART
{
    name = engine
    title = First Copy
}
PART
{
    name = engine
    title = Second Copy
}
PART
{
    name = engine
    title = Third Copy
}
""",
            encoding="utf-8",
        )

        out = self._capture_run(dry_run=True)

        self.assertIn("#LOC_BDB_engine_title", out)
        self.assertIn("#LOC_BDB_engine_title__2", out)
        self.assertIn("#LOC_BDB_engine_title__3", out)
        self.assertEqual(out.count("LOC_KEY_DUPLICATE"), 2)

        self._capture_run(dry_run=False)
        en = (self.mod / "Localization" / "en-us.cfg").read_text(encoding="utf-8")
        self.assertIn("#LOC_BDB_engine_title = First Copy", en)
        self.assertIn("#LOC_BDB_engine_title__2 = Second Copy", en)
        self.assertIn("#LOC_BDB_engine_title__3 = Third Copy", en)

    def test_nested_module_fields_are_not_extracted_or_keyed(self):
        (self.mod / "part.cfg").write_text(
            """
PART
{
    name = testEngine
    title = Test Engine
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket
    MODULE
    {
        name = TestModule
        title = Internal Module Name
    }
}
""",
            encoding="utf-8",
        )

        out = self._capture_run(dry_run=True)
        self.assertNotIn("Internal Module Name", out)
        self.assertIn("#LOC_BDB_testEngine_title", out)
        self.assertNotIn("TestModule", out)

        self._capture_run(dry_run=False)
        en = (self.mod / "Localization" / "en-us.cfg").read_text(encoding="utf-8")
        self.assertIn("#LOC_BDB_testEngine_title = Test Engine", en)
        self.assertNotIn("Internal Module Name", en)
        original = (self.mod / "part.cfg").read_text(encoding="utf-8")
        self.assertIn("title = Internal Module Name", original)

    def test_cross_file_and_in_file_collision_stack(self):
        parts_dir = self.mod / "Parts"
        parts_dir.mkdir()
        (parts_dir / "engine.cfg").write_text(
            """
PART
{
    name = engine
    title = Canonical
}
""",
            encoding="utf-8",
        )
        (self.mod / "z_last.cfg").write_text(
            """
PART
{
    name = engine
    title = Later First
}
PART
{
    name = engine
    title = Later Second
}
""",
            encoding="utf-8",
        )

        out = self._capture_run(dry_run=True)
        self.assertIn("#LOC_BDB_engine_title", out)
        self.assertIn("#LOC_BDB_engine_title__z_last", out)
        self.assertIn("#LOC_BDB_engine_title__z_last__2", out)
        self.assertEqual(out.count("LOC_KEY_DUPLICATE"), 2)

        self._capture_run(dry_run=False)
        en = (self.mod / "Localization" / "en-us.cfg").read_text(encoding="utf-8")
        self.assertIn("#LOC_BDB_engine_title = Canonical", en)
        self.assertIn("#LOC_BDB_engine_title__z_last = Later First", en)
        self.assertIn("#LOC_BDB_engine_title__z_last__2 = Later Second", en)

    def test_skipped_fields_do_not_appear_in_keys_or_localization(self):
        (self.mod / "part.cfg").write_text(
            """
PART
{
    name = mixed
    title = #LOC_OLD_mixed_title
    description =
    manufacturer = Super Co // keep this note
    tags = leftover
}
""",
            encoding="utf-8",
        )

        out = self._capture_run(dry_run=True)
        self.assertNotIn("#LOC_BDB_mixed_title", out)
        self.assertNotIn("#LOC_BDB_mixed_description", out)
        self.assertIn("#LOC_BDB_mixed_manufacturer", out)
        self.assertIn("#LOC_BDB_mixed_tags", out)
        self.assertNotIn("keep this note", out)

        self._capture_run(dry_run=False)
        en = (self.mod / "Localization" / "en-us.cfg").read_text(encoding="utf-8")
        self.assertNotIn("mixed_title", en)
        self.assertNotIn("mixed_description", en)
        self.assertIn("#LOC_BDB_mixed_manufacturer = Super Co", en)
        self.assertIn("#LOC_BDB_mixed_tags = leftover", en)
        csv_text = (self.mod / "Localization" / "translation.csv").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("#LOC_BDB_mixed_manufacturer", csv_text)
        self.assertNotIn("keep this note", csv_text)

    def test_keys_are_grouped_by_part_name_and_field(self):
        (self.mod / "a.cfg").write_text(
            """
PART
{
    name = engine
    title = Title Only
}
""",
            encoding="utf-8",
        )
        (self.mod / "b.cfg").write_text(
            """
PART
{
    name = engine
    description = Description Only
}
""",
            encoding="utf-8",
        )

        out = self._capture_run(dry_run=True)
        self.assertIn("#LOC_BDB_engine_title", out)
        self.assertIn("#LOC_BDB_engine_description", out)
        self.assertNotIn("#LOC_BDB_engine_description__b", out)
        self.assertNotIn("LOC_KEY_DUPLICATE", out)

        self._capture_run(dry_run=False)
        en = (self.mod / "Localization" / "en-us.cfg").read_text(encoding="utf-8")
        self.assertIn("#LOC_BDB_engine_title = Title Only", en)
        self.assertIn("#LOC_BDB_engine_description = Description Only", en)


ACCEPTANCE_CFG = """
PART
{
    name = testEngine

    title = Test Engine
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket

    MODULE
    {
        name = TestModule
        title = Internal Module Name
    }
}
"""


class BackupAndRewriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mod = self.root / "mod"
        self.mod.mkdir()
        self.tool_root = self.root / "tool"
        self.tool_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, dry_run=False):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run(str(self.mod), "MYMOD", dry_run=dry_run, tool_root=self.tool_root)
        return buf.getvalue()

    def test_real_run_rewrites_safe_field_values_only(self):
        cfg = self.mod / "part.cfg"
        cfg.write_text(ACCEPTANCE_CFG, encoding="utf-8")

        self._run(dry_run=False)

        text = cfg.read_text(encoding="utf-8")
        self.assertIn("title = #LOC_MYMOD_testEngine_title", text)
        self.assertIn("manufacturer = #LOC_MYMOD_testEngine_manufacturer", text)
        self.assertIn("description = #LOC_MYMOD_testEngine_description", text)
        self.assertIn("tags = #LOC_MYMOD_testEngine_tags", text)
        self.assertIn("title = Internal Module Name", text)
        self.assertIn("name = testEngine", text)
        self.assertIn("name = TestModule", text)

    def _mod_id(self):
        return hashlib.sha256(
            os.path.normcase(str(self.mod.resolve())).encode("utf-8")
        ).hexdigest()[:12]

    def _backup_root(self):
        return self.tool_root / "data" / "backups" / self._mod_id()

    def test_first_rewrite_backs_up_original_bytes_under_tool_data(self):
        cfg = self.mod / "part.cfg"
        original = ACCEPTANCE_CFG.encode("utf-8")
        cfg.write_bytes(original)

        self._run(dry_run=False)

        backup_root = self._backup_root()
        backup_file = backup_root / "files" / "part.cfg"
        mapping_path = backup_root / "mapping.json"

        self.assertTrue(backup_file.is_file())
        self.assertEqual(backup_file.read_bytes(), original)
        self.assertFalse((self.mod / "part.cfg.bak").exists())

        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        self.assertEqual(mapping["mod_root"], str(self.mod.resolve()))
        entry = mapping["files"]["part.cfg"]
        self.assertEqual(entry["original"], str(cfg.resolve()))
        self.assertEqual(entry["backup"], "files/part.cfg")
        self.assertRegex(entry["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")

    def test_second_run_does_not_overwrite_existing_backup(self):
        cfg = self.mod / "part.cfg"
        original = ACCEPTANCE_CFG.encode("utf-8")
        cfg.write_bytes(original)

        self._run(dry_run=False)
        backup = self._backup_root() / "files" / "part.cfg"
        first_bytes = backup.read_bytes()
        first_mtime = backup.stat().st_mtime
        mapping = json.loads((self._backup_root() / "mapping.json").read_text(encoding="utf-8"))
        created_at = mapping["files"]["part.cfg"]["created_at"]

        cfg.write_bytes(original)
        self._run(dry_run=False)

        self.assertEqual(backup.read_bytes(), first_bytes)
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(backup.stat().st_mtime, first_mtime)
        mapping = json.loads((self._backup_root() / "mapping.json").read_text(encoding="utf-8"))
        self.assertEqual(mapping["files"]["part.cfg"]["created_at"], created_at)
        self.assertIn("title = #LOC_MYMOD_testEngine_title", cfg.read_text(encoding="utf-8"))

    def test_later_run_appends_newly_seen_files_to_mapping(self):
        first = self.mod / "first.cfg"
        first.write_text(
            """
PART
{
    name = firstEngine
    title = First Engine
}
""",
            encoding="utf-8",
        )
        self._run(dry_run=False)

        second = self.mod / "second.cfg"
        second_bytes = b"""
PART
{
    name = secondEngine
    title = Second Engine
}
"""
        second.write_bytes(second_bytes)
        self._run(dry_run=False)

        mapping = json.loads((self._backup_root() / "mapping.json").read_text(encoding="utf-8"))
        self.assertIn("first.cfg", mapping["files"])
        self.assertIn("second.cfg", mapping["files"])
        self.assertEqual(
            (self._backup_root() / "files" / "second.cfg").read_bytes(),
            second_bytes,
        )
        self.assertIn("title = #LOC_MYMOD_secondEngine_title", second.read_text(encoding="utf-8"))

    def test_trailing_comment_indent_and_other_fields_survive_rewrite(self):
        cfg = self.mod / "part.cfg"
        cfg.write_text(
            """
PART
{
    name = commentedEngine
    // keep this whole-line comment

    title = Super Engine // shown in VAB
    mass = 1.25
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket
}
""",
            encoding="utf-8",
        )

        self._run(dry_run=False)

        text = cfg.read_text(encoding="utf-8")
        self.assertIn("    title = #LOC_MYMOD_commentedEngine_title // shown in VAB", text)
        self.assertIn("    // keep this whole-line comment", text)
        self.assertIn("    mass = 1.25", text)
        self.assertIn("    name = commentedEngine", text)
        self.assertIn("\n\n    title =", text)

    def test_unchanged_file_is_not_backed_up_or_rewritten(self):
        hashed = self.mod / "already.cfg"
        hashed_text = """
PART
{
    name = alreadyLocalized
    title = #LOC_OLD_alreadyLocalized_title
    description = #autoLOC_12345
}
"""
        hashed.write_text(hashed_text, encoding="utf-8")
        before = hashed.read_bytes()

        self._run(dry_run=False)

        self.assertEqual(hashed.read_bytes(), before)
        self.assertFalse((self._backup_root() / "files" / "already.cfg").exists())
        mapping_path = self._backup_root() / "mapping.json"
        if mapping_path.exists():
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            self.assertNotIn("already.cfg", mapping.get("files", {}))

    def test_crlf_file_keeps_crlf_after_rewrite(self):
        cfg = self.mod / "crlf.cfg"
        cfg.write_bytes(
            b"PART\r\n{\r\n    name = crlfEngine\r\n    title = CRLF Engine\r\n}\r\n"
        )

        self._run(dry_run=False)

        data = cfg.read_bytes()
        self.assertIn(b"title = #LOC_MYMOD_crlfEngine_title", data)
        self.assertIn(b"\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    def test_dry_run_does_not_backup_or_rewrite(self):
        cfg = self.mod / "part.cfg"
        cfg.write_text(ACCEPTANCE_CFG, encoding="utf-8")
        before = cfg.read_bytes()

        self._run(dry_run=True)

        self.assertEqual(cfg.read_bytes(), before)
        self.assertFalse((self.tool_root / "data").exists())
        self.assertFalse((self.mod / "Localization").exists())
        self.assertFalse(list(self.mod.rglob("*.tmp")))
        self.assertFalse(list(self.mod.rglob("*.bak")))

    def test_chinese_relative_path_is_backed_up_and_rewritten(self):
        folder = self.mod / "零件"
        folder.mkdir()
        cfg = folder / "引擎.cfg"
        original = (
            "PART\n{\n    name = chineseEngine\n    title = Chinese Engine\n}\n"
        ).encode("utf-8")
        cfg.write_bytes(original)

        self._run(dry_run=False)

        self.assertIn(
            "title = #LOC_MYMOD_chineseEngine_title",
            cfg.read_text(encoding="utf-8"),
        )
        backup = self._backup_root() / "files" / "零件" / "引擎.cfg"
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), original)
        mapping = json.loads((self._backup_root() / "mapping.json").read_text(encoding="utf-8"))
        self.assertIn("零件/引擎.cfg", mapping["files"])
        self.assertEqual(mapping["files"]["零件/引擎.cfg"]["backup"], "files/零件/引擎.cfg")

    def test_rewrite_failure_leaves_original_and_continues(self):
        locked = self.mod / "locked.cfg"
        locked.write_text(
            """
PART
{
    name = lockedEngine
    title = Locked Engine
}
""",
            encoding="utf-8",
        )
        ok = self.mod / "ok.cfg"
        ok.write_text(
            """
PART
{
    name = okEngine
    title = Ok Engine
}
""",
            encoding="utf-8",
        )
        locked_before = locked.read_bytes()

        real_replace = os.replace

        def boom(src, dst):
            if Path(dst).name == "locked.cfg":
                raise OSError("simulated replace failure")
            return real_replace(src, dst)

        with patch("localizer.os.replace", side_effect=boom):
            self._run(dry_run=False)

        self.assertEqual(locked.read_bytes(), locked_before)
        self.assertIn("title = #LOC_MYMOD_okEngine_title", ok.read_text(encoding="utf-8"))
        self.assertTrue((self._backup_root() / "files" / "ok.cfg").is_file())
        mapping = json.loads((self._backup_root() / "mapping.json").read_text(encoding="utf-8"))
        self.assertIn("locked.cfg", mapping["files"])
        self.assertEqual(
            (self._backup_root() / "files" / "locked.cfg").read_bytes(),
            locked_before,
        )
        self.assertTrue((self.mod / "locked.cfg.tmp").exists())

    def test_bad_bytes_file_does_not_abort_other_rewrites(self):
        bad = self.mod / "bad.cfg"
        bad.write_bytes(
            b"PART\n{\n    name = badEngine\n    title = Bad Engine\n    // \xff\n}\n"
        )
        ok = self.mod / "ok.cfg"
        ok.write_text(
            """
PART
{
    name = okEngine
    title = Ok Engine
}
""",
            encoding="utf-8",
        )
        bad_before = bad.read_bytes()

        self._run(dry_run=False)

        self.assertEqual(bad.read_bytes(), bad_before)
        self.assertIn("title = #LOC_MYMOD_okEngine_title", ok.read_text(encoding="utf-8"))
        mapping_path = self._backup_root() / "mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        self.assertNotIn("bad.cfg", mapping["files"])
        self.assertIn("ok.cfg", mapping["files"])

    def test_section_13_acceptance_minus_log_file(self):
        cfg = self.mod / "engine.cfg"
        cfg.write_text(ACCEPTANCE_CFG, encoding="utf-8")

        self._run(dry_run=False)

        text = cfg.read_text(encoding="utf-8")
        self.assertIn("title = #LOC_MYMOD_testEngine_title", text)
        self.assertIn("manufacturer = #LOC_MYMOD_testEngine_manufacturer", text)
        self.assertIn("description = #LOC_MYMOD_testEngine_description", text)
        self.assertIn("tags = #LOC_MYMOD_testEngine_tags", text)
        self.assertIn("title = Internal Module Name", text)
        self.assertFalse((self.mod / "engine.cfg.bak").exists())

        loc = self.mod / "Localization"
        en = (loc / "en-us.cfg").read_text(encoding="utf-8")
        zh = (loc / "zh-cn.cfg").read_text(encoding="utf-8")
        csv_text = (loc / "translation.csv").read_text(encoding="utf-8-sig")
        for key in (
            "#LOC_MYMOD_testEngine_title",
            "#LOC_MYMOD_testEngine_manufacturer",
            "#LOC_MYMOD_testEngine_description",
            "#LOC_MYMOD_testEngine_tags",
        ):
            self.assertIn(key, text)
            self.assertIn(key, en)
            self.assertIn(key, zh)
            self.assertIn(key, csv_text)
        self.assertIn("Test Engine", en)
        self.assertIn("Test Engine", zh)

        mapping = json.loads((self._backup_root() / "mapping.json").read_text(encoding="utf-8"))
        self.assertIn("engine.cfg", mapping["files"])
        self.assertTrue((self._backup_root() / "files" / "engine.cfg").is_file())


class LoggingAndFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mod = self.root / "mod"
        self.mod.mkdir()
        self.tool_root = self.root / "tool"
        self.tool_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, dry_run=False):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run(str(self.mod), "MYMOD", dry_run=dry_run, tool_root=self.tool_root)
        return buf.getvalue()

    def _log_files(self):
        log_dir = self.tool_root / "data" / "logs"
        if not log_dir.exists():
            return []
        return sorted(p for p in log_dir.iterdir() if p.is_file())

    def test_real_run_writes_named_event_log(self):
        (self.mod / "part.cfg").write_text(ACCEPTANCE_CFG, encoding="utf-8")

        self._run(dry_run=False)

        logs = self._log_files()
        self.assertEqual(len(logs), 1)
        self.assertRegex(logs[0].name, r"^run_\d{8}_\d{6}\.log$")
        text = logs[0].read_text(encoding="utf-8")
        self.assertFalse(text.lstrip().startswith("{"))
        self.assertIn("BACKUP_CREATED", text)
        self.assertIn("FILE_REWRITE_SUCCESS", text)
        self.assertIn("RUN_FINISHED", text)
        self.assertIn("RUN_START", text)
        self.assertIn("INFO", text)

    def test_dry_run_prints_events_and_writes_no_log(self):
        (self.mod / "part.cfg").write_text(ACCEPTANCE_CFG, encoding="utf-8")

        out = self._run(dry_run=True)

        self.assertIn("RUN_START", out)
        self.assertIn("RUN_FINISHED", out)
        self.assertEqual(self._log_files(), [])
        self.assertFalse((self.tool_root / "data").exists())

    def test_same_second_log_name_uses_numeric_suffix(self):
        (self.mod / "part.cfg").write_text(ACCEPTANCE_CFG, encoding="utf-8")
        log_dir = self.tool_root / "data" / "logs"
        log_dir.mkdir(parents=True)
        (log_dir / "run_20260917_123045.log").write_text("taken\n", encoding="utf-8")

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 9, 17, 12, 30, 45)

        with patch("localizer.datetime", FrozenDateTime):
            self._run(dry_run=False)

        names = {p.name for p in self._log_files()}
        self.assertIn("run_20260917_123045.log", names)
        self.assertIn("run_20260917_123045_2.log", names)
        second = log_dir / "run_20260917_123045_2.log"
        self.assertIn("RUN_START", second.read_text(encoding="utf-8"))
        self.assertEqual((log_dir / "run_20260917_123045.log").read_text(encoding="utf-8"), "taken\n")

    def test_bad_utf8_emits_scan_file_failed_and_continues(self):
        (self.mod / "bad.cfg").write_bytes(
            b"PART\n{\n    name = badEngine\n    title = Bad Engine\n    // \xff\n}\n"
        )
        (self.mod / "ok.cfg").write_text(
            """
PART
{
    name = okEngine
    title = Ok Engine
}
""",
            encoding="utf-8",
        )

        out = self._run(dry_run=False)
        log = self._log_files()[0].read_text(encoding="utf-8")

        self.assertIn("SCAN_FILE_FAILED", out)
        self.assertIn("SCAN_FILE_FAILED", log)
        self.assertNotIn("SCAN_FILE path=bad.cfg", log)
        self.assertIn("Failures:", out)
        self.assertIn("Failures:", log)
        self.assertIn("bad.cfg", out)
        self.assertIn("FILE_REWRITE_SUCCESS", log)
        self.assertIn("title = #LOC_MYMOD_okEngine_title", (self.mod / "ok.cfg").read_text(encoding="utf-8"))
        self.assertEqual(
            (self.mod / "bad.cfg").read_bytes(),
            b"PART\n{\n    name = badEngine\n    title = Bad Engine\n    // \xff\n}\n",
        )

    def test_rewrite_failure_emits_event_and_prints_failure_list(self):
        (self.mod / "locked.cfg").write_text(
            """
PART
{
    name = lockedEngine
    title = Locked Engine
}
""",
            encoding="utf-8",
        )
        (self.mod / "ok.cfg").write_text(
            """
PART
{
    name = okEngine
    title = Ok Engine
}
""",
            encoding="utf-8",
        )
        locked_before = (self.mod / "locked.cfg").read_bytes()
        real_replace = os.replace

        def boom(src, dst):
            if Path(dst).name == "locked.cfg":
                raise OSError("simulated replace failure")
            return real_replace(src, dst)

        with patch("localizer.os.replace", side_effect=boom):
            out = self._run(dry_run=False)

        log = self._log_files()[0].read_text(encoding="utf-8")
        self.assertIn("FILE_REWRITE_FAILED", log)
        self.assertIn("FILE_REWRITE_FAILED", out)
        self.assertIn("Failures:", out)
        self.assertIn("Failures:", log)
        self.assertIn("locked.cfg", out)
        self.assertIn("locked.cfg", log)
        self.assertEqual((self.mod / "locked.cfg").read_bytes(), locked_before)
        self.assertIn("title = #LOC_MYMOD_okEngine_title", (self.mod / "ok.cfg").read_text(encoding="utf-8"))

    def test_skipped_fields_emit_field_skipped(self):
        (self.mod / "part.cfg").write_text(
            """
PART
{
    name = mixed
    title = #LOC_OLD_mixed_title
    description =
    manufacturer = Super Co
    tags = leftover
}
""",
            encoding="utf-8",
        )

        out = self._run(dry_run=True)
        self.assertIn("FIELD_SKIPPED", out)
        self.assertIn("FIELD_FOUND", out)

    def test_second_run_emits_backup_exists(self):
        (self.mod / "part.cfg").write_text(ACCEPTANCE_CFG, encoding="utf-8")
        self._run(dry_run=False)
        (self.mod / "part.cfg").write_text(ACCEPTANCE_CFG, encoding="utf-8")
        out = self._run(dry_run=False)
        log = self._log_files()[-1].read_text(encoding="utf-8")
        self.assertIn("BACKUP_EXISTS", out)
        self.assertIn("BACKUP_EXISTS", log)
        self.assertNotIn("BACKUP_CREATED", log)

    def test_duplicate_keys_emit_warning_event(self):
        (self.mod / "twins.cfg").write_text(
            """
PART
{
    name = engine
    title = First Copy
}
PART
{
    name = engine
    title = Second Copy
}
""",
            encoding="utf-8",
        )
        out = self._run(dry_run=True)
        self.assertIn("LOC_KEY_DUPLICATE", out)
        self.assertIn("WARNING", out)

    def test_section_13_log_contains_required_events(self):
        (self.mod / "engine.cfg").write_text(ACCEPTANCE_CFG, encoding="utf-8")
        self._run(dry_run=False)
        text = self._log_files()[0].read_text(encoding="utf-8")
        for event in (
            "RUN_START",
            "SCAN_START",
            "SCAN_FILE",
            "PART_FOUND",
            "FIELD_FOUND",
            "LOC_KEY_CREATED",
            "BACKUP_CREATED",
            "FILE_REWRITE_START",
            "FILE_REWRITE_SUCCESS",
            "RUN_FINISHED",
        ):
            self.assertIn(event, text)


if __name__ == "__main__":
    unittest.main()
