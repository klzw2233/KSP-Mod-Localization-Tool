import io
import subprocess
import sys
import tempfile
import unittest
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
        original = (self.mod / "part.cfg").read_text(encoding="utf-8")
        self.assertIn("title = Test Engine", original)

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


if __name__ == "__main__":
    unittest.main()
