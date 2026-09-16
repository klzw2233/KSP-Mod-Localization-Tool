# 02: Replace prompts with CLI and dry-run that writes nothing

**What to build:** The tool is invoked as `python localizer.py --mod <dir> --prefix <PREFIX> [--dry-run]`. Missing `--mod` or `--prefix` prints usage and exits non-zero; there is no `input()` prompt. A real run still writes the three first-version Localization artifacts. `--dry-run` prints PART count and the keys that would be generated, and writes nothing: original CFGs unchanged, no Localization files, no `data/` created or modified.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `--mod` and `--prefix` are required; missing either is a non-zero exit with usage text
- [ ] There is no interactive `input()` fallback
- [ ] A real run still overwrites `Localization/en-us.cfg`, `zh-cn.cfg`, and `translation.csv` under the mod
- [ ] `--dry-run` prints PART count and pending keys to stdout
- [ ] `--dry-run` does not change original CFGs, does not write Localization files, and does not create or modify `data/`
