# 01: Merge Localization instead of English overwrite

**What to build:** Real runs stop covering `zh-cn.cfg` with an English clone of the current scan. Union English from this scan plus existing `en-us.cfg` (scan wins on conflict). Keep existing Chinese that differs from current English; otherwise English placeholder. Write-back keeps existing `en-us.cfg` key order and appends new scan keys. Never delete loc keys. CSV `zh-cn` column equals the `zh-cn.cfg` value (Phase 1 empty column is gone). No HTTP in this ticket.

**Blocked by:** None (can start immediately)

**Status:** open

- [ ] Existing Chinese survives a real run without `--translate`
- [ ] New scanned keys append as English placeholders in `zh-cn.cfg`
- [ ] CSV `zh-cn` column matches `zh-cn.cfg` (English on first run)
- [ ] Scan-empty + existing `en-us.cfg` still writes the union (does not empty loc)
- [ ] Scan-empty + no `en-us.cfg` writes no loc files
- [ ] Unreadable existing loc: rewrite may happen, loc files not overwritten
- [ ] Orphan zh-only keys stay in `zh-cn.cfg`, not invented in `en-us`, not in CSV
- [ ] Phase 1 tests still green
