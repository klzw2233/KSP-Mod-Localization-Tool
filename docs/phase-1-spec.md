# Phase 1 规格：Backup + Rewrite + Logging + Dry-run

**状态：已实现**（`main` @ `3a15ac9`，2026-09-17）。本文是 Phase 1 的锁定合同，不是下一阶段任务。下一阶段（OpenAI Compatible 翻译 `zh-cn.cfg`）另开 spec。

上游愿景见仓库根目录 `需求和设计文档.txt`。其中：

- Phase 1 范围当时由 **§50** 定义；现已完成
- 与长文档冲突时本文赢（备份在工具 `data/`，不是旁路 `.bak`）
- §3 / §47 其余 Phase（AI、cache、glossary、manifest、node rules 等）不在本合同内

第一版扫描语义保留：只处理 `PART` 第一层字段 `title` / `description` / `manufacturer` / `tags`，不提取 `MODULE` 内部字段。

继续单文件 `localizer.py`，不拆包。

---

## 1. 范围

做：

- CLI：`--mod` / `--prefix` / `--dry-run`
- 扫描 PART 第一层安全字段
- 稳定 Localization Key（含跨文件 / 同文件冲突）
- 备份到工具数据目录（不污染 Mod）
- 二次扫描 rewrite，只替换目标字段的 value
- 正式跑覆盖写 `en-us.cfg` / `zh-cn.cfg` / `translation.csv`
- 文本日志（事件名可断言）
- `tests/` + stdlib `unittest`

明确不做：

- AI 翻译、OpenAI SDK、`translator.json`
- translation cache / Translation Memory / glossary
- manifest / JSONL 日志
- `--restore` / `--diff` / `--force-backup` / `--verbose` / `--log-dir`
- ConfigNode 真 parser
- 扩展到 `RESOURCE_DEFINITION` / `VARIANT` / `SUBTYPE` 等节点
- `src/ksp_localizer/` 包结构
- 新第三方依赖（含 pytest）

---

## 2. CLI

```text
python localizer.py --mod <dir> --prefix <PREFIX> [--dry-run]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--mod` | 是 | Mod 根目录 |
| `--prefix` | 是 | LOC key 前缀，例如 `MYMOD` |
| `--dry-run` | 否 | 预览，零写入 |

缺 `--mod` 或 `--prefix` → 非零退出，打印用法。无 `input()` 回退。无参数交互模式。

---

## 3. 扫描

- 用 `Path(mod).rglob("*.cfg")` 递归扫描
- **UTF-8 严格读取**（不加 `errors="ignore"`）
- 读失败（编码错误、权限、其它 IO）→ 记 `SCAN_FILE_FAILED`，跳过该文件，继续扫其余文件
- 写回 UTF-8、无 BOM
- 中文路径必须可用（`pathlib`）

提取规则（与第一版相同的深度模型）：

- 只认 `PART` 块
- 只用大括号深度读取 PART **第一层** 字段
- 目标字段：`title`、`description`、`manufacturer`、`tags`
- 嵌套 `MODULE`（或其它子节点）内同名字段不提取、不改写

跳过（提取和 rewrite 都不碰）：

- 空字段，或 `=` 右侧去掉空白后为空
- `value.lstrip().startswith("#")`（已本地化）。包括 `#LOC_`、`#autoLOC_`、其它 `#...`

行内注释：

```cfg
    title = Super Engine // shown in VAB
```

value 取 `=` 与行尾 `//` 之间（去掉首尾空白）。`//` 及之后保留在原行，rewrite 不吞注释。

---

## 4. Localization Key

干净 key：

```text
#LOC_<PREFIX>_<partName>_<field>
```

例：`#LOC_BDB_fooEngine_title`

### 4.1 跨文件同名 PART

相对路径用 `as_posix()` 排序后：

- 第一个 PART 拿干净 key
- 其余：

```text
#LOC_<PREFIX>_<partName>_<field>__<rel>
```

`<rel>` = 该 cfg 相对 `--mod` 的路径，去掉 `.cfg` 后缀，把 `/` 和 key 非法字符替换为 `_`。

例：`Parts/engine.cfg` → `Parts_engine`  
得到：`#LOC_BDB_engine_title__Parts_engine`

### 4.2 同一文件内同名 PART

在该文件已确定的 key 基础上追加 `__2`、`__3`…（按文件内出现顺序，从 2 起）。单文件内顺序稳定。

### 4.3 冲突日志

任何备用 key 都必须打 `LOC_KEY_DUPLICATE` WARNING。禁止静默覆盖。

---

## 5. Rewrite

二次扫描。scan 与 rewrite 共用同一个「PART 第一层字段」迭代器，禁止两套 walker。

只替换目标字段 `=` 右侧、行尾 `//` 之前的那段文本。必须保留：

- 缩进
- 空行
- 整行注释
- 行尾 `//` 注释
- 其它字段
- ConfigNode 结构
- 该文件原来的换行符（`\n` 或 `\r\n`）
- 无 BOM

无实际改动的文件：不备份、不写 tmp、不替换。

有改动的文件，按文件处理：

1. 若 mapping 尚无该相对路径 → `shutil.copy2` 原始字节到数据目录
2. 写到同目录 `*.cfg.tmp`
3. `os.replace` 成原文件
4. 删除 tmp（若 replace 已原子覆盖则无需残留）

单文件失败：该文件保持原样（允许残留可删的 tmp）、记 `FILE_REWRITE_FAILED`、继续下一个文件。不自动回滚已经成功改写的文件。

---

## 6. 备份（不污染 Mod）

备份和日志都在 **`localizer.py` 所在目录**，不使用进程 cwd。

```text
<tool>/data/backups/<mod_id>/
  mapping.json
  files/                      # 镜像 Mod 内相对路径，原文件名不变
    Parts/engine.cfg
```

- `mod_id` = `sha256(normcase(resolve(--mod)))` 的十六进制前 12 位
- Windows 下 `normcase` + `resolve`，避免同一路径因大小写裂成两棵树
- 备份使用 `shutil.copy2`，保留时间戳等元数据
- mapping 已有该相对路径 → **不覆盖**备份（语义：第一次修改之前的原件）
- 新文件只追加 mapping 条目
- 本阶段无 `--restore`。mapping 即还原说明书

`mapping.json` 形状：

```json
{
  "mod_root": "E:/Games/.../GameData/Bluedog_DB",
  "files": {
    "Parts/engine.cfg": {
      "original": "E:/Games/.../GameData/Bluedog_DB/Parts/engine.cfg",
      "backup": "files/Parts/engine.cfg",
      "created_at": "2026-09-16T21:54:01"
    }
  }
}
```

`backup` 为相对该 `mod_id` 目录的路径。`created_at` 用 ISO-8601 本地时间，精确到秒即可。

---

## 7. Localization 产物

仅正式跑覆盖写入（第一版出口不变）：

```text
<mod>/Localization/en-us.cfg
<mod>/Localization/zh-cn.cfg
<mod>/Localization/translation.csv
```

- `zh-cn.cfg` 本阶段仍是英文副本（无 AI）
- csv 编码 `utf-8-sig`，表头 `key,en-us,zh-cn`，`zh-cn` 列为空或与英文相同（与第一版一致：空字符串）
- dry-run 不写这三份
- 增量合并是后续 Phase，本阶段整文件覆盖

---

## 8. 日志

```text
<tool>/data/logs/run_<YYYYMMDD_HHMMSS>.log
```

- 只写文本，不写 JSONL，不写 manifest
- 级别：DEBUG / INFO / WARNING / ERROR
- 同一秒文件名冲突 → `run_<id>_2.log`、`_3`…
- dry-run **不写** log，也不创建 `data/`（若 `data/` 已存在则不得新增或改写其中任何文件）

建议行格式：

```text
2026-09-16 21:54:01 INFO  RUN_START
2026-09-16 21:54:01 INFO  SCAN_START path=...
```

Phase 1 必须出现的事件名（测试按事件名断言）：

| 事件 | 级别 | 何时 |
|---|---|---|
| `RUN_START` | INFO | 启动 |
| `SCAN_START` | INFO | 开始扫描，带 path |
| `SCAN_FILE` | INFO | 每打开一个 cfg |
| `SCAN_FILE_FAILED` | ERROR | 读失败，跳过 |
| `PART_FOUND` | INFO | 识别到 PART，带 name |
| `FIELD_FOUND` | INFO | 提取到可本地化字段 |
| `FIELD_SKIPPED` | INFO | `#` 前缀或空字段 |
| `LOC_KEY_CREATED` | INFO | 生成 key |
| `LOC_KEY_DUPLICATE` | WARNING | 使用备用 key |
| `BACKUP_CREATED` | INFO | 新建备份 |
| `BACKUP_EXISTS` | INFO | mapping 已有，跳过覆盖 |
| `FILE_REWRITE_START` | INFO | 开始改某 cfg |
| `FILE_REWRITE_SUCCESS` | INFO | 该 cfg 改写成功 |
| `FILE_REWRITE_FAILED` | ERROR | 该 cfg 改写失败，继续 |
| `RUN_FINISHED` | INFO | 结束，可带汇总 |

dry-run 这些事件只出现在 stdout，不落盘。

---

## 9. Dry-run

零写入合同：

- 不创建 `.bak`、`.tmp`
- 不改原始 CFG
- 不写 Localization 三份产物
- 不写 log
- 不创建 `data/`；若已存在则不改其中文件

stdout 固定输出：

1. 扫描到的 PART 数
2. 将修改的文件列表
3. 每条 `原value → #LOC_key`
4. 将生成的 key 列表
5. WARNING（含重复 key）
6. ERROR（含坏文件）

正式跑：同样内容打一份到 stdout，并写 `data/logs/`。

---

## 10. 失败模型

- 单文件读失败 → 跳过该文件
- 单文件 rewrite 失败 → 该文件保持原样，继续
- 跑完汇总失败列表（stdout；正式跑同时进 log）
- 不因单个失败中止整次运行
- 不自动从备份还原已成功文件

---

## 11. 测试

目录：`tests/`。框架：stdlib `unittest`。零新依赖。

```text
python -m unittest discover -s tests
```

必须覆盖：

| 用例 | 断言要点 |
|---|---|
| 简单 PART | 四个字段都提取，key 形状正确 |
| 多 PART | 各自独立 key |
| 嵌套 MODULE | `MODULE.title` 不提取、不改写 |
| 已有 `#LOC_` / `#autoLOC_` / 其它 `#` | 跳过 |
| 空字段 / 只有空白 | 跳过 |
| 行尾 `//` 注释 | value 不含注释；rewrite 后注释仍在 |
| 跨文件同名 PART | 排序后第一个干净 key，其余路径后缀 |
| 同文件同名 PART | `__2`、`__3` |
| backup 首次 | `data/backups/<mod_id>/files/...` 存在，mapping 有条目 |
| backup 不覆盖 | 第二次跑备份字节不变 |
| rewrite 只改 value | 缩进、其它字段、结构不变 |
| 换行符 | CRLF 文件写回仍是 CRLF |
| dry-run 零写入 | 工作区与 `data/` 无新文件、原 cfg 字节不变 |
| 中文路径 | 能扫描、能备份、能 rewrite |
| 坏字节 / 非 UTF-8 | 跳过该文件，其它文件继续 |
| tmp 失败 | 原文件不被写成半截 CFG |
| 缺 CLI 参数 | 非零退出 |

先为现有 `parse_parts` / `extract_part` 补 characterization 测试，锁第一版扫描语义，再测 backup / rewrite / dry-run。

---

## 12. 实现顺序（历史，已完成）

tickets 01–05 按此顺序做完。不要再当待办：

1. 把 `input()` 换成 argparse（`--mod` / `--prefix` / `--dry-run`）
2. 抽出 PART 第一层字段迭代器；scan 复用它
3. 修编码：UTF-8 严格；跳过 `#` 与空字段；行尾 `//`
4. Key 生成：干净 key + 路径后缀 + 文件内 `__N`
5. 数据目录 backup + mapping（不覆盖）
6. rewrite：tmp → replace；失败继续
7. 正式跑仍写 Localization 三份；dry-run 跳过所有写入
8. 文本日志 + stdout 预览
9. 按第 11 节补测试并跑通

每完成一块就跑已有测试，不攒到最后。

---

## 13. 验收（对照 §48，砍掉 AI）

给定：

```cfg
PART
{
    name = testEngine

    title = Test Engine
    manufacturer = Test Company
    description = Very powerful engine.
    tags = engine rocket

    MODULE
    {
        name = TestModule
        title = Internal Module Name
    }
}
```

正式跑后：

- 原 cfg 的四个安全字段变为对应 `#LOC_<PREFIX>_testEngine_<field>`
- `MODULE.title` 仍是 `Internal Module Name`
- `<tool>/data/backups/<mod_id>/files/...` 有该文件第一次的原件
- mapping 记录相对路径映射
- 原 Mod 树内 **没有** `engine.cfg.bak`
- 生成 `Localization/en-us.cfg`、`zh-cn.cfg`、`translation.csv`
- key 在 cfg、en-us、csv 中一致
- `data/logs/run_*.log` 存在，含 `BACKUP_CREATED` / `FILE_REWRITE_SUCCESS` / `RUN_FINISHED`

dry-run 同一输入：stdout 能看到将进行的改动，磁盘上原 cfg、Localization、`data/` 均无新写入。

实测：`测试文件夹/001KerbalActuators`（未跟踪）已按此合同跑通。`zh-cn.cfg` 本阶段仍是英文副本。
