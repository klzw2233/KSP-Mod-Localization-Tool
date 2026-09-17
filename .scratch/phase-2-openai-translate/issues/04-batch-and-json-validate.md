# 04: Batch pending keys and reject the whole batch on bad JSON

**What to build:** Split pending entries by `batch_size` (default 50). One in-flight request. User message is the JSON array `[{"key","text"},…]`. Strip optional ` ```json ` fences. Whole batch is valid iff length, key multiset, and non-empty single-line `text` all match. Any failure: whole batch stays English, `AI_BATCH_FAILED`, next batch still runs. 51 pending + size 50 → two POSTs.

**Blocked by:** 03 stdlib POST `/chat/completions` with bounded retry

**Status:** open

- [ ] Never one HTTP request per field
- [ ] 51 items / batch_size 50 → exactly two POSTs, serial
- [ ] Matching JSON array accepted; zh-cn gets those texts
- [ ] Fenced ` ```json ` payload accepted
- [ ] Missing key / extra key / duplicate key / empty text / newline in text → whole batch English
- [ ] Bad JSON / non-array / missing `choices[0].message.content` → whole batch English, no retry
- [ ] Later batch still sent after an earlier batch fails
- [ ] System prompt is the spec §9 text
