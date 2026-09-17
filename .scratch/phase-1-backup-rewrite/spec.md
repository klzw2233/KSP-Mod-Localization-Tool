---
Status: implemented
Feature: phase-1-backup-rewrite
---

# Phase 1: Backup, Rewrite, Logging, Dry-run

## Problem Statement

The first-version tool can scan a Kerbal Space Program mod folder, find PART display fields, and write Localization files. It cannot safely change the original CFG files. It still asks for paths with `input()`, swallows bad bytes, re-extracts fields that are already localization keys, and has no tests on disk.

The user needs to run one command against a real mod (including large ones such as Restock / BDB / Near Future), preview every change, then apply those changes without destroying the mod: original bytes recoverable, nested MODULE fields untouched, comments and line endings preserved, and a log of what happened.

## Solution

Keep the single-file scanner. Replace the interactive prompt with `--mod` / `--prefix` / `--dry-run`. Scan PART first-level safe fields only. Generate stable localization keys (with deterministic suffixes on collisions). On a real run: copy each not-yet-backed-up CFG into the tool's own `data/` tree (never a sibling `.bak` in the mod), rewrite only the target field values, overwrite the three Localization artifacts, and write a text log of named events. `--dry-run` prints the same preview and writes nothing.

## User Stories

1. As a mod localizer, I want to pass `--mod` and `--prefix` on the command line, so that I can script and test the tool without typing at a prompt.
2. As a mod localizer, I want the tool to exit with a non-zero status and print usage when `--mod` or `--prefix` is missing, so that a bad invocation is obvious.
3. As a mod localizer, I want `--dry-run` to show every pending change without writing any file, so that I can review a large mod before committing to rewrite.
4. As a mod localizer, I want dry-run to refuse to create `data/` and refuse to change `data/` if it already exists, so that a preview cannot pollute the tool directory.
5. As a mod localizer, I want dry-run stdout to list PART count, files that would change, each `original value → key` pair, the keys that would be generated, warnings, and errors, so that the preview is enough to audit without opening a diff.
6. As a mod localizer, I want a real run to print the same preview to stdout as dry-run, so that I do not have to remember two output formats.
7. As a mod localizer, I want the tool to recurse through every `*.cfg` under the mod root, including folders with Chinese names, so that a typical GameData tree is fully covered.
8. As a mod localizer, I want CFG files read as strict UTF-8, so that a non-UTF-8 file is not silently corrupted into a "successful" rewrite.
9. As a mod localizer, I want a file that fails to read (encoding, permissions, IO) to be skipped with `SCAN_FILE_FAILED`, so that one bad file does not abort a 400-file mod.
10. As a mod localizer, I want only `PART` nodes to be considered, so that random ConfigNodes are not treated as player-facing parts.
11. As a mod localizer, I want only first-level PART fields `title`, `description`, `manufacturer`, and `tags` extracted, so that internal module fields cannot be rewritten.
12. As a mod localizer, I want a `title` (or other safe field) inside `MODULE` to stay as plain text, so that part-switch / module logic is not turned into a localization key.
13. As a mod localizer, I want fields whose value starts with `#` (after stripping leading space) to be skipped for both extract and rewrite, so that `#LOC_`, `#autoLOC_`, and other existing keys are not wrapped a second time.
14. As a mod localizer, I want empty or whitespace-only field values skipped, so that the tool does not invent keys for blank titles.
15. As a mod localizer, I want the value to be the text between `=` and a trailing `//` comment, so that inline comments are not stored as part of the English string.
16. As a mod localizer, I want rewrite to leave that trailing `//` comment on the line, so that author notes in the CFG survive.
17. As a mod localizer, I want whole-line comments, blank lines, indentation, other fields, and ConfigNode braces left untouched, so that ModuleManager and diffs stay readable.
18. As a mod localizer, I want the original newline style (`\n` or `\r\n`) preserved on rewrite, so that Git and MM do not mark the entire file as changed.
19. As a mod localizer, I want rewritten files written as UTF-8 without a BOM, so that KSP and other tools do not see a surprise prefix.
20. As a mod localizer, I want a clean key of the form `#LOC_<PREFIX>_<partName>_<field>` when the part name is unique, so that the first-version key shape is preserved.
21. As a mod localizer, I want two parts with the same `name` in different files to get deterministic keys: relative paths sorted with `as_posix()`, first wins the clean key, others get `__<sanitized-rel-path>`, so that re-running on another machine does not reshuffle keys.
22. As a mod localizer, I want two parts with the same `name` in the same file to get `__2`, `__3`, … in file order, so that copy-paste mistakes still produce unique keys.
23. As a mod localizer, I want every fallback key logged as `LOC_KEY_DUPLICATE` at WARNING, so that collisions are never silent overwrites.
24. As a mod localizer, I want scan and rewrite to share one PART-first-level field iterator, so that the two passes cannot disagree about which lines are safe.
25. As a mod localizer, I want files with no actual field changes left completely untouched (no backup, no tmp, no replace), so that already-localized or empty-of-safe-fields CFGs are not churned.
26. As a mod localizer, I want a backup of the original bytes before the first rewrite of a file, so that a bad run is recoverable.
27. As a mod localizer, I want that backup stored under the tool directory, not as `engine.cfg.bak` beside the original, so that ModuleManager, CKAN, and the mod tree stay clean.
28. As a mod localizer, I want the backup tree to hang off the script's directory rather than the process cwd, so that launching the tool from inside GameData cannot dump `data/` into the mod.
29. As a mod localizer, I want backups laid out as `data/backups/<mod_id>/files/<relative-path>` plus `mapping.json`, so that I can find the original file without guessing.
30. As a mod localizer, I want `mod_id` to be the first 12 hex characters of `sha256(normcase(resolve(mod)))`, so that two folders both named `MyMod` do not share a backup tree and Windows case differences do not split one tree in two.
31. As a mod localizer, I want `mapping.json` to record `mod_root` and, per relative path, `original`, `backup`, and `created_at`, so that the mapping is the restore instruction even without a restore command.
32. As a mod localizer, I want a second run to refuse to overwrite an existing mapping entry's backup bytes, so that the backup remains "the file before the first rewrite".
33. As a mod localizer, I want a newly seen CFG on a later run appended to the mapping and backed up, so that a mod update that adds files is still protected.
34. As a mod localizer, I want backups created with `copy2` so timestamps and metadata ride along with the bytes.
35. As a mod localizer, I want rewrite to write `*.cfg.tmp` then `os.replace` onto the original, so that a crash mid-write does not leave a truncated CFG as the only copy.
36. As a mod localizer, I want a rewrite failure on one file to keep that file as it was, log `FILE_REWRITE_FAILED`, and continue with the rest, so that a 400-file mod can finish even if file 87 is locked.
37. As a mod localizer, I do not want the tool to auto-restore already-rewritten files from backup on a later failure, so that a partial success stays a partial success I can inspect.
38. As a mod localizer, I want a real run to overwrite `Localization/en-us.cfg`, `Localization/zh-cn.cfg`, and `Localization/translation.csv` under the mod, so that the first-version artifacts still appear.
39. As a mod localizer, I want `zh-cn.cfg` to still be an English copy in this phase, so that missing AI does not block localization file generation.
40. As a mod localizer, I want `translation.csv` written as UTF-8 with BOM, header `key,en-us,zh-cn`, and an empty zh-cn column matching the first version, so that Excel review still works.
41. As a mod localizer, I want dry-run to skip writing those three Localization files, so that a preview cannot clobber a hand-edited csv.
42. As a mod localizer, I want a real run to write `data/logs/run_<YYYYMMDD_HHMMSS>.log` as text only, so that I can audit the run after the terminal is gone.
43. As a mod localizer, I want log lines to carry `DEBUG` / `INFO` / `WARNING` / `ERROR` and the named events (`RUN_START`, `SCAN_START`, `SCAN_FILE`, `SCAN_FILE_FAILED`, `PART_FOUND`, `FIELD_FOUND`, `FIELD_SKIPPED`, `LOC_KEY_CREATED`, `LOC_KEY_DUPLICATE`, `BACKUP_CREATED`, `BACKUP_EXISTS`, `FILE_REWRITE_START`, `FILE_REWRITE_SUCCESS`, `FILE_REWRITE_FAILED`, `RUN_FINISHED`), so that tests and humans can grep the same tokens.
44. As a mod localizer, I want a colliding log filename in the same second to become `run_<id>_2.log`, so that two runs do not overwrite each other.
45. As a mod localizer, I want dry-run events on stdout only, never in a log file, so that the zero-write contract is absolute.
46. As a mod localizer, I want a run that hits mixed success and failure to print a failure list at the end, so that I know which files to look at.
47. As a developer, I want stdlib `unittest` tests under `tests/` with CFG fixtures, so that Phase 1 can be verified without new dependencies.
48. As a developer, I want characterization tests on the existing PART parser before rewrite tests, so that nested-MODULE behavior cannot regress while backup is added.
49. As a developer, I want tests to pass `tool_root` into the run function, so that backups and logs land in a temp dir instead of the repo `data/`.
50. As a developer, I want to run `python -m unittest discover -s tests` and see the Phase 1 table (simple PART, multi PART, nested MODULE, hash keys, empty fields, trailing comments, cross-file and in-file key collisions, first backup, backup no-overwrite, value-only rewrite, CRLF, dry-run zero writes, Chinese paths, bad bytes skipped, tmp failure does not truncate, missing CLI args) all green.

## Implementation Decisions

- Stay in one module. Do not split backup / rewriter / logging into packages. Capabilities, not directories.
- CLI is argparse only: `--mod`, `--prefix`, `--dry-run`. No `input()` fallback.
- After parsing flags, CLI calls one function `run(mod, prefix, dry_run, tool_root=None)`. Default `tool_root` is the directory containing the script. Tests pass a temporary `tool_root`.
- Introduce one shared iterator over PART first-level candidate fields (file, part name, field, value, raw line context needed to replace only the value span). Scan and rewrite both use it. Do not test the iterator as a public seam.
- Skip rules applied in that iterator: empty / whitespace value; `value.lstrip().startswith("#")`.
- Value span for extraction and rewrite: text after `=` up to trailing `//` if present, trimmed. The comment stays on the line.
- Key assignment is computed once per run after a full scan, then consumed by rewrite and Localization writers:
  - Group by `(part name, field)`.
  - Order files by relative path `as_posix()`.
  - First PART in that order gets the clean key; later files get `__` + relative path without `.cfg`, with `/` and illegal key characters replaced by `_`.
  - Within one file, later same-name PARTs append `__2`, `__3`, … on top of whatever key that file already earned.
- `mod_id` = first 12 hex chars of SHA-256 of `os.path.normcase(str(Path(mod).resolve()))`.
- Backup destination: `<tool_root>/data/backups/<mod_id>/files/<posix-relative-path>`. Mapping file: `<tool_root>/data/backups/<mod_id>/mapping.json` with `mod_root` and `files[rel] = {original, backup, created_at}`. `backup` is relative to the `mod_id` directory. `created_at` is local ISO-8601 to the second.
- If `files[rel]` already exists in mapping, do not copy again; emit `BACKUP_EXISTS`.
- Rewrite per changed file: backup if needed, write sibling `*.cfg.tmp` as UTF-8 no BOM with original newline style, `os.replace` onto the original. On failure, leave the original bytes, allow a leftover tmp, emit `FILE_REWRITE_FAILED`, continue.
- Localization output on real runs only, overwrite, first-version format. `zh-cn` values are still the English source. CSV `utf-8-sig`, zh-cn column empty string.
- Logging on real runs only, to `<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log`. Same-second clash suffixes `_2`, `_3`. Named events as in the Phase 1 contract. Dry-run must not create `data/` and must not add or change files under an existing `data/`.
- No restore command, no JSONL, no manifest, no AI, no cache, no glossary, no extra flags.
- Stdlib only.

## Testing Decisions

- Test observable behavior: process/function results, stdout, file bytes, mapping JSON, log event names. Do not assert on helper names, call counts, or walker internals.
- Primary seam: `run(mod, prefix, dry_run, tool_root)`. Fixture mods live under `tests/` (or a temp dir built by the test). `tool_root` is a temp directory. After each test, assert the fixture mod and `tool_root` against the contract (including "no sibling `.bak`").
- Existing seam: `parse_parts` / `extract_part` characterization for first-version scan semantics (simple PART, multiple PARTs, nested MODULE not extracted), plus the new skip rules (hash prefix, empty, trailing `//` not part of value).
- Do not add a public key-allocator seam unless `run` fixtures prove too clumsy; cross-file sort and in-file `__N` should be visible through rewritten CFG and Localization keys.
- CLI missing-args: invoke the module as a subprocess (or the argparse entry) and assert non-zero exit. Do not use the real script directory as `tool_root` in tests.
- Framework: stdlib `unittest`, `python -m unittest discover -s tests`. No pytest.
- There is no prior test suite; these tests are the suite. Fixtures should include a nested MODULE, a CRLF file, a UTF-8-invalid file, a Chinese folder name, an already-hashed field, and two files sharing a PART name.

## Out of Scope

- OpenAI-compatible translation, retries, batching, cache, glossary, translation memory
- `--restore`, `--diff`, `--force-backup`, `--verbose`, `--log-dir`, `--scan-only`, `--translate`
- JSONL logs, manifest, incremental merge of Localization files
- Real ConfigNode parser; node-type rule files; RESOURCE_DEFINITION / VARIANT / SUBTYPE
- Splitting into `src/ksp_localizer/` or `backup.py` / `rewriter.py`
- pytest or any new third-party dependency
- Auto-rollback of successful rewrites
- Detecting encoding besides strict UTF-8

## Further Notes

- Implementation contract (authoritative for this phase, **now implemented**): `docs/phase-1-spec.md`. This spec is the agent-facing restatement plus the agreed test seams.
- Upstream vision: `需求和设计文档.txt`. Where it conflicts with Phase 1, `docs/phase-1-spec.md` wins.
- Backup-beside-cfg (`.bak`) from the long design doc is deliberately rejected: backups live under the tool `data/` tree.
- Implementation order in section 12 of `docs/phase-1-spec.md` is historical; tickets 01–05 are resolved on `main`.
- Next work is a new feature (OpenAI Compatible fill of `zh-cn.cfg`). Grill and write a new spec first. Do not implement from this file.
