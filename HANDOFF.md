# HANDOFF

给下一个 agent。读完再动手。

## 现在停在哪

- 分支：`main`（Phase 1 已合入，`3a15ac9`）
- Phase 1 合同（已实现）：[`docs/phase-1-spec.md`](docs/phase-1-spec.md)
- Phase 1 tickets：`.scratch/phase-1-backup-rewrite/issues/`（01–05 全部 resolved）
- 上游愿景：[`需求和设计文档.txt`](需求和设计文档.txt)。**不要从 §3 / §47 Future 章节直接开工。** 与已实现行为冲突时，代码和 Phase 1 合同赢。备份在工具 `data/`，不是旁路 `.bak`。

产品仍是单文件 `localizer.py`。入口：`run(mod, prefix, dry_run, tool_root=None)`。测试注入 `tool_root`，不要用仓库目录当备份根。

## 已锁定的行为（不要回退）

扫描：`PART` 第一层 `title` / `description` / `manufacturer` / `tags`。`MODULE` 内同名字段不提取。

跳过：空 / 空白；`value.lstrip().startswith("#")`。value 是 `=` 到行尾 `//` 之间（trim）。key 按 `(part name, field)` 分组，文件按相对路径 `as_posix()` 排序，再按扫描序号。备用 key 打 `WARNING LOC_KEY_DUPLICATE`。

CLI：`--mod` / `--prefix` 必填，`--dry-run` 零写入（含不创建/不改 `data/`）。正式跑覆盖 Localization 三份；`zh-cn` 仍是英文副本；csv `utf-8-sig`，zh-cn 列空字符串。

备份 / rewrite：有改动的 CFG 先 `copy2` 到 `<tool_root>/data/backups/<mod_id>/files/<rel>`，写 `mapping.json`；再 `*.cfg.tmp` + `os.replace`，只换安全字段 value。mapping 已有则不覆盖备份。无改动不备份不写。失败则该文件保持原样并继续。scan 与 rewrite 共用 `_iter_part_blocks` / `_iter_first_level_fields`。`_iter_first_level_entries` + `_is_extractable` 给扫描日志打 `FIELD_SKIPPED`。

日志：正式跑写 `<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log`。同一秒冲突 `_2`、`_3`。事件打 stdout；正式跑同时落盘。失败列表 stdout + log。dry-run 不写 log。严格 UTF-8；读失败 `SCAN_FILE_FAILED` 跳过。rewrite 失败 `FILE_REWRITE_FAILED`。不自动从备份还原已成功文件。

测试 seams：

- `parse_parts`：扫描语义 + skip / `//`（`tests/test_scanner.py`）
- `run(mod, prefix, dry_run, tool_root)`：CLI、key、产物、日志（`tests/test_cli.py`）
- 不要把 `_assign_keys` 做成公共 seam
- `python -m unittest discover -s tests`（41 tests）。stdlib only，不加 pytest。

## 下一个要做

用户要讨论如何接入 **OpenAI Compatible API**，用来填写 `zh-cn.cfg`（本阶段仍是英文副本）。

未 grill / 未写 Phase 2 spec 之前：

- 不要写 translator、不要加 SDK 或第三方依赖
- 不要拆 `src/ksp_localizer/`
- 不要做 cache / glossary / manifest / `--restore` / `--translate` 旗标（除非新 spec 明确要）
- 不要回退 Phase 1 的备份位置、skip 规则、dry-run 零写入

新功能开 `feat/*`，不要直接在 `main` 上实现（文档同步除外）。

## 实测样本

仓库根有未跟踪的 `测试文件夹/001KerbalActuators`（WildBlue KerbalActuators）。工具 `data/` 里已有该模组的备份和 `run_*.log`。**不要 git add `测试文件夹/` 或 `data/`。**

```text
python localizer.py --mod 测试文件夹/001KerbalActuators --prefix WBI --dry-run
python localizer.py --mod 测试文件夹/001KerbalActuators --prefix WBI
```

2 个 PART。`title` / `description` 已改成 `#LOC_WBI_…`；`manufacturer = #autoLOC_501646` 跳过；MODULE 未碰；Mod 树没有 `.bak`。

## 工作方式

- 规格驱动；实现前读 / 写 spec，不要从长设计文档的 Future 章节开工
- 能 TDD 就 TDD：先确认 seam，红 → 绿
- 做完跑全量 `python -m unittest discover -s tests`
- 用 `/code-review`（Standards + Spec 两轴）
- 提交当前 feature 分支，合 `main` 前先问
- 单文件 `localizer.py`，直到 spec 明确要求拆包
