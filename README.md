# KSP Mod Localization Tool

扫描 Kerbal Space Program（KSP1）Mod 的 `.cfg`，提取 `PART` 第一层显示字段，生成 Localization 文件。目标是安全、可回滚、可预览地改写原 CFG，而不是随便批量替换字符串。

Phase 1 已完成：扫描 + 稳定 key + dry-run + 备份 + 只改 value 的 rewrite + 命名事件日志。

## 现在能做什么

```text
python localizer.py --mod <Mod目录> --prefix <PREFIX> [--dry-run]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--mod` | 是 | Mod 根目录 |
| `--prefix` | 是 | LOC key 前缀，例如 `WBI` |
| `--dry-run` | 否 | 预览事件和将生成的 key，零写入 |

缺 `--mod` 或 `--prefix` 会打印用法并以非零退出。没有交互式 `input()`。

正式跑会覆盖写入：

```text
<mod>/Localization/en-us.cfg
<mod>/Localization/zh-cn.cfg          # 本阶段仍是英文副本
<mod>/Localization/translation.csv    # utf-8-sig，表头 key,en-us,zh-cn
```

正式跑还会把有改动的 CFG 备份到工具目录（不是 Mod 旁的 `.bak`），再只替换目标字段的 value：

```text
<tool>/data/backups/<mod_id>/files/<相对路径>
<tool>/data/backups/<mod_id>/mapping.json
```

`mod_id` 是 `sha256(normcase(resolve(--mod)))` 的十六进制前 12 位。mapping 里已有的相对路径不会被覆盖。无改动的文件不备份、不写 tmp。

正式跑还会写文本日志：

```text
<tool>/data/logs/run_<YYYYMMDD_HHMMSS>.log
```

同一秒冲突变成 `run_<id>_2.log`。行里带级别和可 grep 的事件名（`RUN_START`、`SCAN_FILE_FAILED`、`BACKUP_CREATED`、`FILE_REWRITE_FAILED`、`RUN_FINISHED` 等）。

`--dry-run` 不写 Localization、不改原 CFG、不备份、不写 log、不创建 `data/`。事件只打 stdout。坏 UTF-8 文件记 `SCAN_FILE_FAILED` 并跳过；单文件 rewrite 失败记 `FILE_REWRITE_FAILED`，原字节保留，跑完打印失败列表。

## 扫描规则

- 递归扫描 `*.cfg`
- 只认 `PART` 块，只用大括号深度读 **第一层** 字段：`title` / `description` / `manufacturer` / `tags`
- 嵌套 `MODULE`（或其它子节点）里的同名字段不提取
- 跳过：空 / 纯空白；`value.lstrip().startswith("#")`（`#LOC_`、`#autoLOC_`、其它 `#…`）
- 行尾 `//` 不算进 value

干净 key：

```text
#LOC_<PREFIX>_<partName>_<field>
```

同名 PART 冲突：相对路径 `as_posix()` 排序，第一个拿干净 key，其它文件 `__<sanitized-rel>`，同一文件内后续 `__2`、`__3`。备用 key 会在 stdout 打 `LOC_KEY_DUPLICATE`。

## 测试

无第三方依赖。stdlib `unittest`（41 tests）：

```text
python -m unittest discover -s tests
```

## 仓库布局

| 路径 | 作用 |
|---|---|
| `localizer.py` | 全部产品代码（单文件，不拆包） |
| `tests/` | 测试 |
| `docs/phase-1-spec.md` | Phase 1 锁定合同（已实现） |
| `.scratch/phase-1-backup-rewrite/` | Phase 1 spec + tickets（全部 resolved） |
| `需求和设计文档.txt` | 上游愿景；与已实现行为冲突时以代码和 Phase 1 合同为准 |

不要提交 `data/`、`测试文件夹/`、`.cfg.tmp`。

## 还没做

- OpenAI Compatible API 填写 `zh-cn.cfg`（下一阶段，先讨论再写 spec，未锁定前不要实现）
- translation cache / glossary / manifest / `--restore` / 拆包

交接细节见 [`HANDOFF.md`](HANDOFF.md)。
