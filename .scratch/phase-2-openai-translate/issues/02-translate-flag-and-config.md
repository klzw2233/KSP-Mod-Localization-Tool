# 02: `--translate` flag, config, dry-run pending list, exit codes

**What to build:** CLI `--translate`. `run(..., translate=False) -> int`. `main` `sys.exit`s that int. Real `--translate` reads `<tool_root>/translator.json`; missing/invalid → `AI_CONFIG_INVALID`, loc still merged with English placeholders, return 1. `OPENAI_API_KEY` overlays json `api_key`; neither present is OK (dummy bearer later). `--dry-run --translate` never hits HTTP, never requires json, prints pending count + keys, returns 0. Zero pending on a real `--translate` with valid config: `AI_NOTHING_PENDING`, no HTTP, return 0. Invalid config on real `--translate` still returns 1 even if zero pending. Scan/rewrite failures alone still return 0.

**Blocked by:** 01 Merge Localization instead of English overwrite

**Status:** open

- [ ] `--translate` is accepted; `--mod` / `--prefix` still required
- [ ] `run` returns 0/1; `main` uses it as process status
- [ ] Real `--translate` without json: rewrite happens, loc merged, return 1, `AI_CONFIG_INVALID`
- [ ] `--dry-run --translate`: zero writes, no json required, pending keys on stdout, return 0
- [ ] Pending filter: zh missing or zh == en; human zh kept
- [ ] Zero pending + valid config: `AI_NOTHING_PENDING`, no HTTP, return 0
- [ ] Empty English union + `--translate`: `AI_NO_SOURCE`, no loc write, return 1
- [ ] Loc read failure + `--translate`: `AI_LOC_READ_FAILED`, no loc write, return 1
- [ ] `.gitignore` includes `translator.json`
- [ ] No HTTP client required to close this ticket (may stub the call site)
