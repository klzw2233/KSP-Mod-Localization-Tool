# Phase 2 规格：OpenAI Compatible 翻译 `zh-cn.cfg`

**状态：已锁定，未实现**（grill 2026-09-17/18）。本文是 Phase 2 的实现合同。与 `需求和设计文档.txt` §13–23 / §47 Phase 4–6 冲突时本文赢。

Phase 1 合同仍有效：[`docs/phase-1-spec.md`](phase-1-spec.md)。扫描、备份、rewrite、dry-run 零写入、单文件 `localizer.py`、stdlib unittest、零第三方依赖，一律不回退。

---

## 1. 范围

做：

- CLI：`--translate`（`--mod` / `--prefix` / `--dry-run` 不变）
- 每次正式跑对 `en-us.cfg` / `zh-cn.cfg` / `translation.csv` **合并写回**（不再按本次扫描整文件覆盖成英文副本）
- `--translate` 时用 OpenAI Compatible `chat/completions` 填待译条目
- 配置：`<tool_root>/translator.json` + `OPENAI_API_KEY`
- stdlib `urllib.request`，串行按批，有限次重试
- 日志事件（见第 11 节）
- mock HTTP 测试；不打真 API

明确不做：

- `openai` SDK / 任何新依赖 / `requirements.txt`
- translation cache / Translation Memory / glossary 文件
- `class Translator` / 多 provider 抽象
- `src/ksp_localizer/` 拆包
- 数字 / 单位 / 格式符深度校验（只做第 8 节的 JSON key 集合校验）
- `--restore` / `--force-retranslate` / `--diff` / manifest / JSONL
- 并行多 batch、按 token 自动拆批、`response_format`
- 从 loc 删除过期 key
- 一条文本一次 HTTP 请求

---

## 2. CLI

```text
python localizer.py --mod <dir> --prefix <PREFIX> [--dry-run] [--translate]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--mod` | 是 | Mod 根目录 |
| `--prefix` | 是 | LOC key 前缀 |
| `--dry-run` | 否 | 预览，零写入；**永不**打 API |
| `--translate` | 否 | 正式跑才打 API；默认不加则完全不请求 |

`run` seam：

```text
run(mod, prefix, dry_run=False, tool_root=None, translate=False) -> int
```

- 返回 `0` 或 `1`（见第 3 节）
- `main`：`sys.exit(run(...))`
- 测试仍注入 `tool_root`；`translator.json` 也相对 `tool_root`

无 `input()`。缺 `--mod` / `--prefix` 仍非零 + 用法（Phase 1）。

---

## 3. 触发与失败

默认正式跑 = Phase 1 的扫描 / 备份 / rewrite，然后按第 4 节 **合并写 loc**。不读 `translator.json`，不打 API。

`--translate` 才翻译。AI 不是核心路径：没加旗标时工具必须离线可跑。

| 情况 | rewrite | 写 loc | 退出码 |
|---|---|---|---|
| 正式跑，无 `--translate` | 做 | 合并写 | `0`（与 Phase 1 一样，即使有扫描/rewrite 失败） |
| 正式跑，`--translate`，全部 batch 成功或 0 条待译 | 做 | 合并写（含译文） | `0` |
| 正式跑，`--translate`，没配置 / 没源文 / loc 读失败 / 任一 batch 最终失败 | 做（读失败时仍做） | 见下 | `1` |
| `--dry-run`（含 `--translate`） | 不做 | 不写 | 恒 `0` |

翻译失败 **不回滚** 已成功 rewrite。不因单个 CFG 失败中止整次运行（Phase 1）。

`--translate` 的 `1` **不分级**：没配置、没源文、loc 读失败、部分 batch 失败，都是 `1`。扫描/rewrite 失败单独仍是 `0`。

0 条待译（并集里中文都已与英文不同）：**不打 HTTP**，打 `AI_NOTHING_PENDING`。正式 `--translate` **仍要求配置合法**；不合法 → `AI_CONFIG_INVALID`，按合并结果写 loc（待译保持英文占位），退出 `1`。

---

## 4. 源文并集与合并

第二次及以后再跑时，CFG 里安全字段已是 `#LOC_…`，扫描提取为空。英文以 **本次扫描 ∪ 已有 `en-us.cfg`** 为并集。

### 4.1 英文

- 同一 key：**本次扫描赢**（覆盖 `en-us.cfg` 里该 key 的英文）
- 只在 `en-us.cfg` 里的 key：保留
- 只在本次扫描里的 key：追加
- 不编造英文

### 4.2 中文

- 已有 `zh-cn.cfg` 里该 key 的值，若存在且 **与当前英文不完全相同** → 视为译文，保留
- 否则 → 英文占位（缺 key、或中文与英文完全相同）
- 不带 `--translate` 再跑：也走这套合并。**禁止**再把 `zh-cn.cfg` 整文件盖成英文副本

### 4.3 待译过滤器（只在 `--translate` 时送 API）

送出「`zh-cn` 缺失，或 `zh-cn` 文本与当前 `en-us` 完全相同」的 key。

- 上次失败留下的英文占位会再送
- 人工改过且与英文不同的不重译
- 本阶段无 `--force-retranslate`，也无「英文变了就清掉中文」

### 4.4 写回顺序

- `en-us.cfg`：**已有文件的 key 顺序不变**，新 key 按本次扫描顺序追加
- `zh-cn.cfg` 与 `translation.csv` 对 **en-us 那份 key 列表** 使用同一顺序
- **永不从 loc 删除 key**（零件删了译文可残留）

### 4.5 孤儿中文

只存在于 `zh-cn.cfg`、扫描和 `en-us.cfg` 都没有的 key：

- 留在 `zh-cn.cfg`（追加在文件末尾、语言块关闭之前，相对已有 zh 顺序不变）
- 不编英文；`en-us.cfg` 不补假行
- **不进 csv**
- 这是本阶段唯一允许的 en/zh key 集不一致

### 4.6 没源文

英文并集为空（扫描无提取字段，且没有可读的 `en-us.cfg` 条目）：

- **三份 loc 都不写**（避免写空壳盖掉东西；若 loc 本就不存在则不创建）
- 已有 `zh-cn.cfg` 原字节保留
- `--translate` → `AI_NO_SOURCE`，退出 `1`
- 无 `--translate` → 退出 `0`，不写 loc

---

## 5. 读已有 loc

路径（相对 `--mod`）：

```text
Localization/en-us.cfg
Localization/zh-cn.cfg
```

| 磁盘 | 行为 |
|---|---|
| 文件不存在 | 该语言视为空 dict |
| 存在但非 UTF-8 / IO 失败 | **读失败** |
| 存在、UTF-8、但找不到 `Localization { <lang> { … } }` 结构 | **读失败** |
| 结构合法、0 条 key | 空 dict，合法 |

`<lang>` 分别是 `en-us` / `zh-cn`。语言块内第一层 `key = value`；value 取 `=` 到行尾 `//` 之间（trim），与 CFG 规则一致。

**en-us 或 zh-cn 任一方读失败：**

- 三份 loc **都不写**
- rewrite 仍按 Phase 1 做（若尚未做）
- 打 `AI_LOC_READ_FAILED`
- `--translate` → 退出 `1`；否则 `0`

禁止在读失败时「用扫描结果覆盖写出 3 条」。csv 不是源，每次由合并结果整文件重写；读失败时 csv 也不写。

---

## 6. 配置

路径：`<tool_root>/translator.json`（与 `localizer.py` 同级，测试里即注入的 `tool_root`）。**gitignore 该文件名**。不提交 example。

```json
{
  "base_url": "http://127.0.0.1:8317/v1",
  "api_key": "sk-xxxx",
  "model": "model-name",
  "batch_size": 50,
  "temperature": 0.1,
  "max_retries": 3,
  "timeout_seconds": 120
}
```

| 字段 | 必填 | 默认 | 非法则整份配置无效 |
|---|---|---|---|
| `base_url` | 是 | — | 缺、空、非字符串 |
| `model` | 是 | — | 缺、空、非字符串 |
| `api_key` | 否 | 见下 | 有则须为字符串 |
| `batch_size` | 否 | `50` | 非 int，或 `<= 0` |
| `temperature` | 否 | `0.1` | 非 number |
| `max_retries` | 否 | `3` | 非 int，或 `< 0`（`0` = 不重试，只正试 1 次） |
| `timeout_seconds` | 否 | `120` | 非 number，或 `<= 0` |

未知字段忽略。文件缺失、非法 JSON、缺必填 → **没配置** → `AI_CONFIG_INVALID`。

`api_key`：环境变量 `OPENAI_API_KEY` 覆盖 json。都没有 → 请求头仍发 `Authorization: Bearer sk-dummy`，**不当失败**。本地兼容代理可以不校验 key。

`--translate` 正式跑才读配置。`--dry-run` 不读、不要求该文件存在。

---

## 7. HTTP

- stdlib `urllib.request`，零新依赖
- `POST {base_url 去尾斜杠}/chat/completions`
- **不**自动补 `/v1`（调用方自己把 `base_url` 写对）
- **一次只在飞一个请求**（串行；禁止并行 batch）
- 超时：`timeout_seconds`
- 请求头：`Content-Type: application/json`、`Authorization: Bearer <key或sk-dummy>`
- **不要** `response_format`

body：

```json
{
  "model": "<model>",
  "temperature": 0.1,
  "messages": [
    {"role": "system", "content": "<第 9 节原文>"},
    {"role": "user", "content": "<本批 JSON 数组文本>"}
  ]
}
```

user 内容就是本批 `[{"key":"#LOC_…","text":"…"}, …]` 的 JSON 文本（`ensure_ascii=False`）。

成功响应：HTTP 200，JSON 路径 `choices[0].message.content` 为字符串。缺字段 / 非 JSON → 本批失败，**不重试**。

### 7.1 重试

只对 **429 / 5xx / 网络错误**（`URLError`、`TimeoutError`、连接失败）重试。

**400 / 401 / 403 / 404 / 其它 4xx 不重试**，本批失败。

`max_retries` = 额外次数。默认 3 → 最多 **1 次正试 + 3 次重试 = 4 次**。

等待：有 `Retry-After` 且能解析为 **非负整数秒** → 用它；否则第 1/2/3 次重试前等 **2s / 4s / 8s**。`Retry-After` 不是整数秒（HTTP-date 等）→ 当没有，走 2/4/8。测试 mock `time.sleep`。

打满仍失败 → `AI_BATCH_FAILED`，这批 key **留当前英文占位**，继续下一批。

每次重试打 `AI_RETRY`。

---

## 8. Batch 与校验

**禁止一条文本一次请求。** 按 `batch_size` 切待译列表（最后一批可以不足）。顺序 = 第 4.4 节待译 key 顺序。

响应 `content`：

1. strip
2. 若以 \`\`\` 开头：去掉第一行围栏（\`\`\` 或 \`\`\`json）和末尾 \`\`\`
3. 再 strip
4. `json.loads` 必须得到 **数组**

整批合格当且仅当：

- 数组长度 = 本批输入条数
- `key` 多重集合与输入完全一致（排序后相等；输出有重复 key 且输入无重复 → 不合格）
- 每项是 object，含 `key` 与 `text`
- `text` 为字符串，strip 后非空，且不含 `\n` / `\r`

任何一条不满足 → **整批作废**，这批全留英文占位，`AI_BATCH_FAILED`，继续下一批。不做数字/单位校验。不部分采纳。

---

## 9. System prompt（写死在代码里）

不进 json。本阶段无 glossary。四个字段同一套规则（tags 译成简体中文、空格分隔；不特判 manufacturer）。

```text
You are a professional KSP mod localization translator.

Translate English into Simplified Chinese.

Rules:

1. Preserve every localization key.
2. Do not add or remove entries.
3. Return valid JSON only.
4. Do not explain your answer.
5. Preserve numbers, units, identifiers and technical names.
6. Preserve KSP terminology consistently.
7. Do not translate internal identifiers.
8. Translate player-facing text naturally.
9. title, description, manufacturer, and tags use the same rules. Translate tags as space-separated Simplified Chinese keywords.
```

---

## 10. 产物

正式跑且第 4–5 节允许写时，覆盖写入：

```text
<mod>/Localization/en-us.cfg
<mod>/Localization/zh-cn.cfg
<mod>/Localization/translation.csv
```

格式与 Phase 1 相同（`Localization { lang { key = value } }`，UTF-8 无 BOM；csv `utf-8-sig`，表头 `key,en-us,zh-cn`）。

**Phase 1 行为变化（有意）：**

- csv 的 `zh-cn` 列 = 该 key 在 `zh-cn.cfg` 里的值（英文占位或中文），不再是空字符串
- 不带 `--translate` 的正式跑也不再把已有中文整文件盖成英文副本

成功译文写入 `zh-cn.cfg` 对应 value；失败/未译保持英文占位。

---

## 11. 日志

仍只写文本：`<tool_root>/data/logs/run_<YYYYMMDD_HHMMSS>.log`。dry-run 不写 log、不创建/改 `data/`（Phase 1）。

Phase 1 事件全部保留。新增：

| 事件 | 级别 | 何时 |
|---|---|---|
| `AI_CONFIG_INVALID` | ERROR | `--translate` 正式跑配置无效/缺失 |
| `AI_NO_SOURCE` | ERROR | `--translate` 且英文并集为空 |
| `AI_LOC_READ_FAILED` | ERROR | 已有 loc 读失败（正式跑；dry-run 只 stdout） |
| `AI_NOTHING_PENDING` | INFO | 过滤器后 0 条待译 |
| `AI_BATCH_START` | INFO | 某批发出前，带 `batch=` `count=` |
| `AI_RETRY` | WARNING | 将重试，带 `batch=` |
| `AI_BATCH_SUCCESS` | INFO | 某批校验通过 |
| `AI_BATCH_FAILED` | ERROR | 某批最终失败（含 4xx、校验失败、打满重试） |

dry-run 这些事件只出现在 stdout。0 条待译不打 HTTP，也不打 `AI_BATCH_*`。

---

## 12. Dry-run

Phase 1 零写入合同不变。额外：

- `--dry-run --translate` **不**要求 `translator.json`，**不**打 API
- 只读已有 loc（读不是写）；合并在内存里算待译
- stdout 在 Phase 1 预览之外增加：待译条数 + 那些 key
- loc 读失败：stdout 打 `AI_LOC_READ_FAILED`，不假装待译列表完整，退出 `0`
- 恒退出 `0`

---

## 13. `run` 顺序

1. `scan_mod` + `_assign_keys`；stdout 打 Phase 1 的 PART 数 / 扫描 key
2. **dry-run**：若 `translate`，只读 loc、算待译、打印、`return 0`。否则 Phase 1 dry-run，`return 0`
3. `_rewrite_mod`（失败进 Failures 列表，继续）
4. 读已有 loc；失败 → `AI_LOC_READ_FAILED`，不写 loc，`return 1 if translate else 0`
5. 内存合并（第 4 节）
6. 英文并集为空 → 不写 loc；`translate` 则 `AI_NO_SOURCE` 且 `return 1`；否则 `return 0`
7. 若非 `translate`：写三份 loc，`return 0`
8. 读配置；无效 → `AI_CONFIG_INVALID`，写三份 loc（待译英文占位），`return 1`
9. 过滤器；0 条 → `AI_NOTHING_PENDING`，写 loc，`return 0`
10. 串行 batch；成功的 key 写入内存中文
11. 写三份 loc
12. 任一批最终失败 → `return 1`，否则 `0`

---

## 14. 测试

目录 `tests/`，stdlib `unittest`，mock HTTP（`urllib.request.urlopen`）和 `time.sleep`。禁止测试打真网络。

```text
python -m unittest discover -s tests
```

Phase 1 用例必须仍绿。额外至少：

| 用例 | 断言要点 |
|---|---|
| 首次正式跑无 `--translate` | csv `zh-cn` 列 = 英文（不再空） |
| 已有中文，无 `--translate` 再跑 | `zh-cn.cfg` 中文保留；新扫描 key 以英文占位追加 |
| 已 rewrite、有 `en-us.cfg`、`--translate` | 从 en-us 取源文，不因扫描为空而空译 |
| 已 rewrite、无 `en-us.cfg`、`--translate` | 不写空 loc；`AI_NO_SOURCE`；退出 1 |
| 待译过滤器 | 中英相同再送；中英不同不送 |
| 0 条待译 | 不调用 urlopen；`AI_NOTHING_PENDING`；配置合法时退出 0 |
| `--translate` 缺配置 | rewrite 发生；loc 合并写英文占位；`AI_CONFIG_INVALID`；`run` 返回 1 |
| `--dry-run --translate` | 零写入；不读配置也可；stdout 有待译条数；不 urlopen；返回 0 |
| batch_size 切批 | 51 条待译 + size 50 → 两次 POST，串行 |
| 非法 JSON / 缺 key / 多 key / 空 text / 换行 | 整批英文占位，下一批仍发 |
| 围栏 \`\`\`json | 剥掉后合格则成功 |
| 429 后成功 | 有 `AI_RETRY`；最终成功；mock sleep |
| 400 | 不重试；本批失败 |
| 缺 api_key | 仍 POST，`Bearer sk-dummy` |
| loc 坏字节 | 不覆盖三份；rewrite 可已发生；`--translate` 返回 1 |
| `main --translate` 失败 | 进程退出码 1 |

---

## 15. 实现顺序

tickets 在 `.scratch/phase-2-openai-translate/issues/`。按号做，每块跑全量测试。

1. 合并写 loc（无 API）：打破「整文件英文覆盖」和「csv 空列」
2. `--translate` CLI + 读 `translator.json` + dry-run 待译列表 + 退出码（尚可不发真 HTTP）
3. `urllib` POST + 重试
4. 按批 + JSON 校验 + 整批作废
5. 接入 `run()` + 第 14 节端到端 mock 测试

---

## 16. 验收

在已 Phase 1 处理过的 Mod（CFG 已是 `#LOC_…`，`en-us.cfg` 有英文，`zh-cn.cfg` 仍是英文副本）上：

```text
python localizer.py --mod <Mod> --prefix <PREFIX> --dry-run --translate
```

stdout 能看到待译条数；磁盘无新写入。

配置好 `translator.json` 后：

```text
python localizer.py --mod <Mod> --prefix <PREFIX> --translate
```

- `zh-cn.cfg` 对应 key 变为中文（失败项仍英文）
- csv `zh-cn` 列与 cfg 一致
- 原 CFG / 备份不被翻译失败回滚
- log 含 `AI_BATCH_*` 与 `RUN_FINISHED`
- 再跑一次不带 `--translate`：中文仍在
- 再跑一次带 `--translate`：已译 key 不发 HTTP（0 待译或只发新增）

缺配置跑 `--translate`：CFG rewrite 该做的仍做，退出 1，中文不丢（若已有）。
