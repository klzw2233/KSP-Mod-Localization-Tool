# 04: Backup originals into tool data and rewrite only field values

**What to build:** A real run copies each not-yet-backed-up CFG into the tool's `data/backups/<mod_id>/files/` tree with `mapping.json`, then rewrites only the safe-field values in the original (indent, comments, other fields, braces, and newline style preserved). The mod tree never gains a sibling `.bak`. A second run does not overwrite an existing backup. Rewrite uses tmp then replace. Dry-run still writes nothing. Section 48 acceptance minus the log file is met.

**Blocked by:** 03 Skip localized/empty fields and assign stable collision keys

**Status:** resolved

- [x] Backups live under the script directory's `data/backups/<mod_id>/`, not beside the CFG
- [x] `mod_id` is the first 12 hex chars of SHA-256 of `normcase(resolve(mod))`
- [x] `mapping.json` records `mod_root` and per-file `original`, `backup`, `created_at`
- [x] First rewrite of a file `copy2`s original bytes; a later run does not overwrite that backup
- [x] Newly seen files on a later run are appended to the mapping and backed up
- [x] Only target field values are replaced; indent, blank lines, comments, other fields, structure, and original newlines remain
- [x] Unchanged files are not backed up and not rewritten
- [x] Rewrite writes `*.cfg.tmp` then `os.replace`; a failed file is left intact and the run continues
- [x] Dry-run still writes nothing (no backup, no tmp, no rewrite, no Localization, no `data/`)
- [x] Tests inject `tool_root` so backups land in a temp dir, not the repo `data/`
- [x] Section 48 minus log-file assertions: rewritten CFG, MODULE title untouched, mapping present, no sibling `.bak`, Localization three files, keys consistent

## Answer

Scan and rewrite share `_iter_part_blocks` + `_iter_first_level_fields`. A real `run()` copies changed CFGs with `copy2` to `<tool_root>/data/backups/<mod_id>/files/<rel>`, records `mapping.json`, then writes `*.cfg.tmp` and `os.replace`s only the safe-field value span (comment, indent, braces, other fields, original newlines kept). Mapping hits skip the copy. Unchanged files are skipped. `os.replace` failure leaves the original and continues. Dry-run still writes nothing.

Seam stays `run(mod, prefix, dry_run, tool_root)`. Logs / `SCAN_FILE_FAILED` / strict UTF-8 skip are ticket 05. `python -m unittest discover -s tests` green (31 tests).
