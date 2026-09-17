# 03: stdlib POST `/chat/completions` with bounded retry

**What to build:** One serial `urllib.request` POST to `{base_url.rstrip("/")}/chat/completions`. No SDK, no `response_format`, no auto `/v1`. Timeout from config. `Authorization: Bearer <key or sk-dummy>`. Retry only 429 / 5xx / network; 400/401/403/other 4xx do not retry. `max_retries` extra attempts (default 3). Wait `Retry-After` integer seconds or 2/4/8. Emit `AI_RETRY`. Mock `urlopen` and `time.sleep` in tests. Do not send one request per field.

**Blocked by:** 02 `--translate` flag, config, dry-run pending list, exit codes

**Status:** open

- [ ] POST body has `model`, `temperature`, `messages` (system + user)
- [ ] Missing api_key still POSTs `Bearer sk-dummy`
- [ ] 429 then 200 succeeds; `AI_RETRY` logged; sleep mocked
- [ ] 400 does not retry; batch fails
- [ ] Network error retries then `AI_BATCH_FAILED` after exhaustion
- [ ] `Retry-After: 7` waits 7 seconds, not 2
- [ ] Non-integer `Retry-After` falls back to 2/4/8
- [ ] Timeout uses `timeout_seconds`
- [ ] Zero new dependencies
