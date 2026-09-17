---
Status: ready-for-agent
Feature: phase-2-openai-translate
---

# Phase 2: OpenAI Compatible translate `zh-cn.cfg`

Contract details (HTTP body, retry numbers, merge rules, event names): [`docs/phase-2-spec.md`](../../docs/phase-2-spec.md). This file is the agent-facing spec. If they conflict, the contract wins.

## Problem Statement

Phase 1 can rewrite PART display fields to `#LOC_…` keys and write Localization files, but `zh-cn.cfg` is always an English clone of the current scan and `translation.csv`'s Chinese column is empty. A second real run overwrites any hand-filled Chinese. There is no way to fill Simplified Chinese through an OpenAI-compatible local proxy without adding an SDK, and sending one HTTP request per field would 429 that proxy.

The user needs: default runs stay offline; `--translate` fills pending Chinese in batches; already-translated text survives later runs; a failed batch leaves English and continues; translation failure never rolls back a successful CFG rewrite.

## Solution

Keep the single-file tool. Add `--translate`. Every real run **merges** `en-us.cfg` / `zh-cn.cfg` / `translation.csv` (scan ∪ existing English; keep Chinese that differs from current English). `--translate` then POSTs pending `{key, text}` batches to `{base_url}/chat/completions` via stdlib HTTP, serial, with bounded retry. Dry-run never calls the API. Invalid JSON from the model rejects the whole batch.

## User Stories

1. As a mod localizer, I want a real run without `--translate` to stay fully offline, so that backup and rewrite still work with no network and no `translator.json`.
2. As a mod localizer, I want `--translate` to be the only switch that calls the API, so that I cannot accidentally spend tokens on a normal rewrite.
3. As a mod localizer, I want `--mod` and `--prefix` to stay required, so that Phase 1 invocations do not change.
4. As a mod localizer, I want missing `--mod` or `--prefix` to still print usage and exit non-zero, so that a bad command is obvious.
5. As a mod localizer, I want `--dry-run` to keep writing nothing (no Localization, no CFG rewrite, no `data/`, no log), so that a preview cannot clobber a hand-edited `zh-cn.cfg`.
6. As a mod localizer, I want `--dry-run --translate` to never call the API and never require `translator.json`, so that I can preview pending work on a machine with no proxy.
7. As a mod localizer, I want `--dry-run --translate` to print how many keys are pending and list those keys, so that I know what would be sent before I pay for it.
8. As a mod localizer, I want `--dry-run` (with or without `--translate`) to always exit 0, so that a preview is not a failed script.
9. As a mod localizer, I want a real run to rewrite original CFGs exactly as Phase 1 does, so that translation is not a second rewriter.
10. As a mod localizer, I want translation failure to leave successful CFG rewrites in place, so that a dead proxy does not undo localization keys.
11. As a mod localizer, I want scan or rewrite failures alone to still exit 0, so that Phase 1 scripts that grep `Failures:` do not break.
12. As a mod localizer, I want a real `--translate` that hits missing config, no English source, unreadable loc, or any failed batch to exit 1, so that a wrapper knows Chinese is incomplete.
13. As a mod localizer, I do not want distinct exit codes for those translation failures, so that I do not have to memorize 2 vs 3 vs 4.
14. As a mod localizer, I want English to be the union of this scan and existing `en-us.cfg`, so that a second run on an already-rewritten mod still has source text.
15. As a mod localizer, I want this scan to win when the same key's English disagrees, so that a part title change in the CFG is the source of truth.
16. As a mod localizer, I want existing `zh-cn.cfg` values kept when they differ from current English, so that a later run without `--translate` cannot wipe Chinese.
17. As a mod localizer, I want a missing Chinese value, or a Chinese value identical to English, treated as pending, so that last run's failed English placeholders are retried.
18. As a mod localizer, I want human-edited Chinese that differs from English left unsent, so that the model cannot overwrite a reviewed line.
19. As a mod localizer, I want existing `en-us.cfg` key order preserved, with new scan keys appended, so that Git diffs stay small.
20. As a mod localizer, I want `zh-cn.cfg` and `translation.csv` to follow that same English key order, so that the three artifacts line up.
21. As a mod localizer, I do not want the tool to delete loc keys when a PART disappears, so that leftover translations are not silently destroyed.
22. As a mod localizer, I want a Chinese-only orphan key kept in `zh-cn.cfg`, not invented in `en-us.cfg`, and omitted from csv, so that junk English is not created.
23. As a mod localizer, I want an empty English union to write no Localization files at all, so that an already-rewritten mod without `en-us.cfg` is not replaced by an empty shell.
24. As a mod localizer, I want `--translate` on that empty-union case to log `AI_NO_SOURCE` and exit 1, so that I know there is nothing to translate.
25. As a mod localizer, I want a missing loc file treated as empty, so that the first Phase 2 run on a fresh mod still works.
26. As a mod localizer, I want a loc file that is not UTF-8, or that lacks a `Localization { <lang> { … } }` block, treated as read failure, so that a truncated file is not "successfully" merged down to three keys.
27. As a mod localizer, I want loc read failure to skip writing all three artifacts (including csv), after rewrite has already run, so that the previous loc bytes survive.
28. As a mod localizer, I want loc read failure with `--translate` to log `AI_LOC_READ_FAILED` and exit 1, and without `--translate` to exit 0, so that only translation mode is a hard failure.
29. As a mod localizer, I want `translator.json` next to the tool (under `tool_root` in tests), gitignored, so that secrets never sit in the mod tree or in git.
30. As a mod localizer, I want `base_url` and `model` required, so that a half-written json cannot silently hit the wrong host.
31. As a mod localizer, I want missing file, invalid JSON, empty required fields, `batch_size <= 0`, negative retries, or non-positive timeout to count as invalid config, so that bad numbers fail closed.
32. As a mod localizer, I want `OPENAI_API_KEY` to override json `api_key`, so that I can keep the url/model in a file and the secret in the environment.
33. As a mod localizer, I want a missing api key to still send `Authorization: Bearer sk-dummy`, so that a local proxy that does not check keys still works.
34. As a mod localizer, I want `--dry-run` not to read `translator.json`, so that a preview does not depend on a secret file.
35. As a mod localizer, I want HTTP done with the standard library, so that the tool stays zero-dependency.
36. As a mod localizer, I never want one field per HTTP request, so that a 200-string mod does not 429 a local proxy.
37. As a mod localizer, I want pending keys split by `batch_size` (default 50), last batch allowed short, so that I can turn the knob in json when a model chokes on long descriptions.
38. As a mod localizer, I want only one HTTP request in flight, so that parallel batches cannot stampede the proxy.
39. As a mod localizer, I want POST `{base_url stripped of trailing slash}/chat/completions` with no automatic `/v1` suffix, so that a gateway already ending in `/v1` is not doubled.
40. As a mod localizer, I want no `response_format` field, so that picky local proxies do not 400.
41. As a mod localizer, I want the user message to be the JSON array of `{key, text}` for that batch, so that the model can return structured rows.
42. As a mod localizer, I want 429, 5xx, and network/timeout errors retried, and 400/401/403/404/other 4xx not retried, so that a bad prompt is not hammered and a blip is.
43. As a mod localizer, I want `max_retries` extra attempts (default 3 → four tries total), so that retry cannot loop forever.
44. As a mod localizer, I want wait time to honor integer `Retry-After` seconds, otherwise 2/4/8, so that a 429 with a server hint is respected.
45. As a mod localizer, I want a batch that still fails after retries to keep English placeholders, log `AI_BATCH_FAILED`, and continue the next batch, so that one bad batch does not abort the rest.
46. As a mod localizer, I want model output that is fenced ` ```json ` stripped, then parsed as a JSON array, so that chatty models still count as success.
47. As a mod localizer, I want a batch rejected unless length, key multiset, and non-empty single-line `text` all match the input, so that a missing key cannot silently stay English while neighbors commit.
48. As a mod localizer, I want 51 pending keys with `batch_size` 50 to send exactly two POSTs, so that batching is observable.
49. As a mod localizer, I want title, description, manufacturer, and tags translated with the same rules, tags as space-separated Simplified Chinese, so that VAB search still works in Chinese.
50. As a mod localizer, I want the system prompt fixed in code, so that json cannot silently change translation policy.
51. As a mod localizer, I want csv `zh-cn` to equal the `zh-cn.cfg` value (English placeholder or Chinese), so that Excel review matches the game file.
52. As a mod localizer, I want a first real run without `--translate` to write English in that csv column (no longer empty), so that the three artifacts stop disagreeing.
53. As a mod localizer, I want zero pending translations (all zh already differ from en) to skip HTTP, log `AI_NOTHING_PENDING`, and exit 0 when config is valid, so that a second `--translate` is cheap.
54. As a mod localizer, I want real `--translate` with invalid config to still exit 1 even if nothing is pending, so that "configured" is checked before I assume the pipeline is ready.
55. As a developer, I want `run(mod, prefix, dry_run, tool_root, translate) -> int` as the only product seam, so that tests inject `tool_root` and never write the repo `data/`.
56. As a developer, I want `main` to `sys.exit` that int, so that a subprocess `--translate` failure is exit 1.
57. As a developer, I want HTTP and sleep mocked in tests, never a live API, so that CI stays offline.
58. As a developer, I want Phase 1 tests to stay green, so that merge/csv changes cannot regress backup, rewrite, or dry-run zero-write.
59. As a developer, I want named log events `AI_CONFIG_INVALID`, `AI_NO_SOURCE`, `AI_LOC_READ_FAILED`, `AI_NOTHING_PENDING`, `AI_BATCH_START`, `AI_RETRY`, `AI_BATCH_SUCCESS`, `AI_BATCH_FAILED` grep-able on stdout and in the real-run log, so that tests assert tokens not prose.

## Implementation Decisions

- Stay in one module. Do not add a Translator class, a cache module, or a package split.
- CLI argparse gains `--translate` only. After parse, call `run(mod, prefix, dry_run, tool_root=None, translate=False)` and exit with its 0/1.
- Default `tool_root` remains the script directory. Tests pass a temp `tool_root`. Config is `<tool_root>/translator.json`.
- Merge runs on every real run, with or without `--translate`. Scan English union existing `en-us.cfg`; scan wins on conflict. Chinese kept if present and not identical to current English; else English placeholder.
- Pending filter (API only): zh missing or zh == current en.
- Write-back order: existing en-us keys first, new scan keys appended. zh-cn and csv follow that list. Never delete keys. zh-only orphans append at end of zh-cn, skip csv, skip en-us.
- Loc read: missing file = empty. Unreadable encoding/IO or missing `Localization { lang { } }` structure = read failure for that language; either language failing blocks all three writes.
- Empty English union: write nothing, including not creating Localization if absent.
- HTTP: stdlib only, one in-flight POST, no SDK, no `response_format`, no auto `/v1`.
- Retry only 429 / 5xx / network; 4xx other than 429 fail the batch immediately. `max_retries` is extra attempts. Sleep `Retry-After` integer seconds or 2/4/8. Tests mock sleep.
- Batch validation is all-or-nothing. Partial apply is forbidden. A later batch still runs after an earlier failure.
- System prompt is the contract §9 text, in code, not in json.
- Log files and dry-run zero-write remain Phase 1. New event names as in the contract.
- `run` order is the contract §13 sequence (scan → dry-run return or rewrite → read loc → merge → config/batches → write).

## Testing Decisions

- Test observable behavior: `run` return value, process exit code, stdout event names, loc/csv bytes, original CFG bytes, whether `urlopen` was called and with which URL/headers/body. Do not assert on helper names, batch-slicer internals, or prompt string assembly except as visible in the POST body.
- Primary seam: `run(mod, prefix, dry_run, tool_root, translate)`. Same pattern as Phase 1 `tests/test_cli.py`: temp mod + temp `tool_root`, capture stdout.
- CLI / `main` exit: subprocess on the script for missing args (existing) and for `--translate` failure → exit 1.
- Mock `urllib.request.urlopen` (and `time.sleep` for retry tests). Never hit a real network.
- Do not add a public translator seam unless `run` fixtures cannot express "51 keys → two POSTs". Prefer one extra test file over a new exported function.
- Framework: stdlib `unittest`, `python -m unittest discover -s tests`. No pytest. No new dependencies.
- Phase 1 table must remain green. New cases at least match contract §14 (merge without API, pending filter, dry-run translate, config invalid, no source, loc read failure, batching, JSON reject, fence strip, 429 retry, 400 no retry, dummy bearer, `main` exit 1).

## Out of Scope

- `openai` SDK, `requirements.txt`, any third-party package
- translation cache / Translation Memory / glossary file
- `class Translator` / extra providers
- package split into `src/ksp_localizer/`
- number/unit/format-string deep validation
- `--restore`, `--force-retranslate`, `--diff`, manifest, JSONL
- parallel batches, token-based splitting, `response_format`
- deleting stale loc keys
- one HTTP request per field

## Further Notes

- Implement on `feat/*`, not `main`. Claim tickets 01–05 in order under `.scratch/phase-2-openai-translate/issues/`.
- Ticket 01 is merge-only (no HTTP). Ticket 02 can stub the call site. Tickets 03–04 add POST/retry/batch. Ticket 05 closes contract §14 / §16.
- Do not git-add `测试文件夹/` or `data/`. `translator.json` is gitignored.
- Phase 1 empty csv `zh-cn` column is an intentional break; existing tests do not assert the empty column.
