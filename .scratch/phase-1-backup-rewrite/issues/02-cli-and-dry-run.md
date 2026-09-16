# 02: Replace prompts with CLI and dry-run that writes nothing

**What to build:** The tool is invoked as `python localizer.py --mod <dir> --prefix <PREFIX> [--dry-run]`. Missing `--mod` or `--prefix` prints usage and exits non-zero; there is no `input()` prompt. A real run still writes the three first-version Localization artifacts. `--dry-run` prints PART count and the keys that would be generated, and writes nothing: original CFGs unchanged, no Localization files, no `data/` created or modified.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `--mod` and `--prefix` are required; missing either is a non-zero exit with usage text
- [x] There is no interactive `input()` fallback
- [x] A real run still overwrites `Localization/en-us.cfg`, `zh-cn.cfg`, and `translation.csv` under the mod
- [x] `--dry-run` prints PART count and pending keys to stdout
- [x] `--dry-run` does not change original CFGs, does not write Localization files, and does not create or modify `data/`

## Answer

CLI is argparse `--mod` / `--prefix` / `--dry-run`; `main` calls `run(mod, prefix, dry_run, tool_root=None)`. No `input()`. Tests in `tests/test_cli.py`: missing-args subprocess, `run()` real vs dry-run (temp `tool_root`), `--dry-run` accepted. `python -m unittest discover -s tests` green. Backup, rewrite, skip, and logs remain tickets 03–05.
