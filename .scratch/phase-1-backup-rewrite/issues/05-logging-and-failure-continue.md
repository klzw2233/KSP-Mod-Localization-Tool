# 05: Write named run logs and continue after per-file failures

**What to build:** A real run writes `data/logs/run_<YYYYMMDD_HHMMSS>.log` with named events that tests can grep. Dry-run never writes a log and never creates or changes `data/`. A non-UTF-8 file is skipped (`SCAN_FILE_FAILED`) and the rest of the mod continues. A rewrite failure leaves that file's original bytes, emits `FILE_REWRITE_FAILED`, and continues. Same-second log names gain `_2`. Chinese paths work for scan, backup, and rewrite.

**Blocked by:** 04 Backup originals into tool data and rewrite only field values

**Status:** resolved

- [x] Real run writes `<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log` as text only
- [x] Log lines include level and the named events: `RUN_START`, `SCAN_START`, `SCAN_FILE`, `SCAN_FILE_FAILED`, `PART_FOUND`, `FIELD_FOUND`, `FIELD_SKIPPED`, `LOC_KEY_CREATED`, `LOC_KEY_DUPLICATE`, `BACKUP_CREATED`, `BACKUP_EXISTS`, `FILE_REWRITE_START`, `FILE_REWRITE_SUCCESS`, `FILE_REWRITE_FAILED`, `RUN_FINISHED`
- [x] Same-second filename clash uses `_2`, `_3`
- [x] Dry-run prints events to stdout only: no log file, no `data/` create or modify
- [x] Strict UTF-8 read; a bad file is skipped with `SCAN_FILE_FAILED` and other files continue
- [x] Rewrite failure: original bytes intact, `FILE_REWRITE_FAILED`, continue, failure list at end
- [x] Chinese paths scan, backup, and rewrite successfully
- [x] Section 48 log assertions: log exists and contains `BACKUP_CREATED` / `FILE_REWRITE_SUCCESS` / `RUN_FINISHED`

## Answer

`run()` 正式跑打开 `<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log`（文本，非 JSONL）。`_emit` 打级别 + 事件名到 stdout；有 log file 时同时落盘。同一秒冲突 `_2`、`_3`。dry-run 不创建 `data/`、不写 log。扫描改严格 UTF-8；坏文件 `SCAN_FILE_FAILED` 并继续。rewrite 失败 `FILE_REWRITE_FAILED`，原字节保留，跑完打印 `Failures:`。`FIELD_SKIPPED` 走 `_iter_first_level_entries`（rewrite 仍用 skip 后的 field iterator）。中文路径沿用 04 的 backup/rewrite 测试。

Seam 仍是 `run(mod, prefix, dry_run, tool_root)`。`python -m unittest discover -s tests` 绿（41 tests）。
