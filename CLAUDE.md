# KSP Mod Localization Tool

Phase 1 已实现。合同：`docs/phase-1-spec.md`。产品是单文件 `localizer.py`。

Phase 2 合同已锁定、未实现：`docs/phase-2-spec.md`。tickets：`.scratch/phase-2-openai-translate/issues/`。未 claim ticket 前不要改 `localizer.py`。不要从 `需求和设计文档.txt` 的 Future 章节加 cache、glossary、拆包或 `--restore`。与已实现行为冲突时，代码和已锁定 spec 赢；备份在工具 `data/`，不是旁路 `.bak`。零第三方依赖；HTTP 用 stdlib `urllib`，禁止一条文本一次请求。

## Agent skills

### Issue tracker

Issues live as markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
