# KSP Mod Localization Tool

扫描 Kerbal Space Program（KSP1）Mod 的 `.cfg`，提取 `PART` 第一层显示字段，生成 Localization 文件。目标是安全、可回滚、可预览地改写原 CFG，而不是随便批量替换字符串。

当前还在 Phase 1：扫描 + 稳定 key + dry-run。**不会改原始 CFG。** 备份、rewrite、日志是后续票。

## 现在能做什么

```text
python localizer.py --mod <Mod目录> --prefix <PREFIX> [--dry-run]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--mod` | 是 | Mod 根目录 |
| `--prefix` | 是 | LOC key 前缀，例如 `WBI` |
| `--dry-run` | 否 | 只打印将生成的 key，零写入 |

缺 `--mod` 或 `--prefix` 会打印用法并以非零退出。没有交互式 `input()`。

正式跑会覆盖写入：

```text
<mod>/Localization/en-us.cfg
<mod>/Localization/zh-cn.cfg          # 本阶段仍是英文副本
<mod>/Localization/translation.csv    # utf-8-sig，表头 key,en-us,zh-cn
```

`--dry-run` 不写这三份，不改原 CFG，不创建 `data/`。

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

无第三方依赖。stdlib `unittest`：

```text
python -m unittest discover -s tests
```

## 仓库布局

| 路径 | 作用 |
|---|---|
| `localizer.py` | 全部产品代码（单文件，不拆包） |
| `tests/` | 测试 |
| `docs/phase-1-spec.md` | Phase 1 实现合同，冲突时以它为准 |
| `.scratch/phase-1-backup-rewrite/` | 本阶段 spec + tickets |
| `需求和设计文档.txt` | 上游愿景；与 Phase 1 冲突时 spec 赢 |

不要提交 `data/`、`测试文件夹/`、`.cfg.tmp`。

## 还没做（Phase 1 剩余）

- 备份到工具 `data/backups/`（不是 Mod 旁的 `.bak`）
- 改写原 CFG 的字段 value
- 文本运行日志
- AI 翻译（不在 Phase 1）

交接细节见 [`HANDOFF.md`](HANDOFF.md)。
