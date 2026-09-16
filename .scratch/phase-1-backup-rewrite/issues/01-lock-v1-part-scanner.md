# 01: Lock v1 PART scanner with characterization tests

**What to build:** Running `python -m unittest discover -s tests` covers the first-version scanner as it behaves today: a simple PART yields the four safe fields, multiple PARTs stay independent, and a `title` nested inside `MODULE` is not extracted. Product behavior does not change. Later tickets that change skip rules or rewrite will watch these tests go red first.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `python -m unittest discover -s tests` is green against the current scanner
- [x] A simple PART extracts `title`, `description`, `manufacturer`, and `tags`
- [x] Multiple PARTs in one file are returned as separate parts with their own fields
- [x] A `title` inside nested `MODULE` is not extracted
- [x] No product code change is required for this ticket to pass

## Answer

Characterization tests live in `tests/test_scanner.py`, seam `parse_parts`. Three cases: simple PART four fields, independent multi-PART, nested MODULE `title` not extracted. `python -m unittest discover -s tests` green. `localizer.py` unchanged.
