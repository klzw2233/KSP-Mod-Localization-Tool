# HANDOFF

给下一个 agent。读完再动手。

## 现在停在哪

- 分支：`main`（Phase 1 tickets 01–05 已合入，`3a15ac9`）
- Phase 1 合同：[`docs/phase-1-spec.md`](docs/phase-1-spec.md)（grill 锁定，实现以它为准）
- Agent 向 restatement + seams：[`.scratch/phase-1-backup-rewrite/spec.md`](.scratch/phase-1-backup-rewrite/spec.md)
- 上游愿景：[`需求和设计文档.txt`](需求和设计文档.txt)。**§3 / §47 其余 Phase 不要做。** 与 Phase 1 冲突时 spec 赢。备份进工具 `data/`，不要旁路 `.bak`。

产品仍是单文件 `localizer.py`。入口：`run(mod, prefix, dry_run, tool_root=None)`。测试注入 `tool_root`，不要用仓库目录当备份根。

## Tickets

目录：`.scratch/phase-1-backup-rewrite/issues/`

| # | 文件 | 状态 |
|---|---|---|
| 01 | `01-lock-v1-part-scanner.md` | resolved（`e19f705`） |
| 02 | `02-cli-and-dry-run.md` | resolved（`c66f715`） |
| 03 | `03-skip-and-stable-keys.md` | resolved（`35743a4`） |
| 04 | `04-backup-and-rewrite.md` | resolved |
| 05 | `05-logging-and-failure-continue.md` | resolved |

认领：把 `Status:` 改成 `claimed` 再写代码。做完：勾 checkbox、写 `## Answer`、`Status: resolved`。新代码开 `feat/*`，不要直接在 `main` 上实现。

## 已锁定的行为（不要回退）

扫描：`PART` 第一层 `title` / `description` / `manufacturer` / `tags`。`MODULE` 内同名字段不提取。

跳过：空 / 空白；`value.lstrip().startswith("#")`。value 是 `=` 到行尾 `//` 之间（trim）。key 按 `(part name, field)` 分组，文件按相对路径 `as_posix()` 排序，再按扫描序号。备用 key 打 `WARNING LOC_KEY_DUPLICATE`。

CLI：`--mod` / `--prefix` 必填，`--dry-run` 零写入（含不创建/不改 `data/`）。正式跑覆盖 Localization 三份；`zh-cn` 仍是英文副本；csv `utf-8-sig`，zh-cn 列空字符串。

备份 / rewrite：有改动的 CFG 先 `copy2` 到 `<tool_root>/data/backups/<mod_id>/files/<rel>`，写 `mapping.json`；再 `*.cfg.tmp` + `os.replace`，只换安全字段 value。mapping 已有则不覆盖备份。无改动不备份不写。`os.replace` 失败则该文件保持原样并继续。scan 与 rewrite 共用 `_iter_part_blocks` / `_iter_first_level_fields`。`_iter_first_level_entries` 给扫描日志打 `FIELD_SKIPPED`；rewrite 仍走 skip 后的 field iterator。

日志：正式跑写 `<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log`。同一秒冲突 `_2`、`_3`。事件打 stdout；正式跑同时落盘。dry-run 不写 log、不创建/不改 `data/`。严格 UTF-8；读失败 `SCAN_FILE_FAILED` 跳过。rewrite 失败 `FILE_REWRITE_FAILED` + 失败列表。不自动从备份还原已成功文件。

测试 seams：

- `parse_parts`：扫描语义 + skip / `//`（`tests/test_scanner.py`）
- `run(mod, prefix, dry_run, tool_root)`：CLI 行为、key、产物、日志（`tests/test_cli.py`）
- 不要把 `_assign_keys` 做成公共 seam
- `python -m unittest discover -s tests`（当前 41 tests）。stdlib only，不加 pytest。

## 下一个要做

Phase 1 tickets 全部 resolved，已合 `main`。不要开始 AI / cache / glossary / `--restore`。

## 实测样本

仓库根有未跟踪的 `测试文件夹/001KerbalActuators`（WildBlue KerbalActuators）。**不要 git add。**

已 dry-run：

```text
python localizer.py --mod 测试文件夹/001KerbalActuators --prefix WBI --dry-run
```

2 个 PART。抽出 `title` / `description`；`manufacturer = #autoLOC_501646 //…` 被跳过；MODULE 未碰。正式跑：原 cfg 的 title/description 变为 `#LOC_WBI_…`，`#autoLOC_` 行和 MODULE 不动，工具 `data/` 里有备份和 `data/logs/run_*.log`，Mod 树里没有 `.bak`。**不要 git add 测试文件夹。**

## 工作方式

- 规格驱动；实现前读 spec，不要从长设计文档的 Future 章节开工
- 能 TDD 就 TDD：先确认 seam，红 → 绿，一次一条
- 做完跑全量 `python -m unittest discover -s tests`
- 用 `/code-review`（Standards + Spec 两轴）
- 提交当前 feature 分支，合 `main` 前先问
- 单文件 `localizer.py`。最短能用的 diff。
