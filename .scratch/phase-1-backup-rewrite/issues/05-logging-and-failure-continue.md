# 05: Write named run logs and continue after per-file failures

**What to build:** A real run writes `data/logs/run_<YYYYMMDD_HHMMSS>.log` with named events that tests can grep. Dry-run never writes a log and never creates or changes `data/`. A non-UTF-8 file is skipped (`SCAN_FILE_FAILED`) and the rest of the mod continues. A rewrite failure leaves that file's original bytes, emits `FILE_REWRITE_FAILED`, and continues. Same-second log names gain `_2`. Chinese paths work for scan, backup, and rewrite.

**Blocked by:** 04 Backup originals into tool data and rewrite only field values

**Status:** ready-for-agent

- [ ] Real run writes `<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log` as text only
- [ ] Log lines include level and the named events: `RUN_START`, `SCAN_START`, `SCAN_FILE`, `SCAN_FILE_FAILED`, `PART_FOUND`, `FIELD_FOUND`, `FIELD_SKIPPED`, `LOC_KEY_CREATED`, `LOC_KEY_DUPLICATE`, `BACKUP_CREATED`, `BACKUP_EXISTS`, `FILE_REWRITE_START`, `FILE_REWRITE_SUCCESS`, `FILE_REWRITE_FAILED`, `RUN_FINISHED`
- [ ] Same-second filename clash uses `_2`, `_3`
- [ ] Dry-run prints events to stdout only: no log file, no `data/` create or modify
- [ ] Strict UTF-8 read; a bad file is skipped with `SCAN_FILE_FAILED` and other files continue
- [ ] Rewrite failure: original bytes intact, `FILE_REWRITE_FAILED`, continue, failure list at end
- [ ] Chinese paths scan, backup, and rewrite successfully
- [ ] Section 48 log assertions: log exists and contains `BACKUP_CREATED` / `FILE_REWRITE_SUCCESS` / `RUN_FINISHED`
