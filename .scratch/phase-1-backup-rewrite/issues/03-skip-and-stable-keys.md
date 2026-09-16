# 03: Skip localized/empty fields and assign stable collision keys

**What to build:** Fields that are already localization keys (`value` starting with `#` after stripping leading space) and empty/whitespace-only fields are neither extracted nor rewritten. A trailing `//` comment is not part of the value. When two PARTs share a name, keys are stable: files ordered by relative `as_posix()` path, first wins the clean `#LOC_<PREFIX>_<part>_<field>` key, later files get `__<sanitized-rel-path>`, and later same-name PARTs in one file get `__2`, `__3`. Collisions emit `LOC_KEY_DUPLICATE` as a warning. Dry-run stdout and Localization files show these keys. Nested `MODULE` fields remain untouched.

**Blocked by:** 01 Lock v1 PART scanner with characterization tests; 02 Replace prompts with CLI and dry-run that writes nothing

**Status:** ready-for-agent

- [ ] `#LOC_`, `#autoLOC_`, and any other `#…` value is skipped for extract and rewrite
- [ ] Empty or whitespace-only values are skipped
- [ ] Value is the text between `=` and trailing `//`; the comment stays on the line
- [ ] Cross-file same-name PARTs: posix-sorted relative path, first clean key, others `__<rel>`
- [ ] In-file same-name PARTs append `__2`, `__3` in file order
- [ ] Every fallback key is a `LOC_KEY_DUPLICATE` warning, never a silent overwrite
- [ ] Dry-run and Localization artifacts show the assigned keys
- [ ] Nested `MODULE` fields are still not extracted
