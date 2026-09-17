# KSP Mod Localization Tool

Phase 1 已实现（Backup + Rewrite + Logging + Dry-run）。合同：`docs/phase-1-spec.md`。产品是单文件 `localizer.py`。

下一阶段（OpenAI Compatible 翻译 `zh-cn.cfg`）还没有 spec。未锁定前不要从 `需求和设计文档.txt` 的 Future 章节实现 AI、cache、glossary、拆包或 `--restore`。与已实现行为冲突时，代码和 Phase 1 合同赢；备份在工具 `data/`，不是旁路 `.bak`。

## Agent skills

### Issue tracker

Issues live as markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
