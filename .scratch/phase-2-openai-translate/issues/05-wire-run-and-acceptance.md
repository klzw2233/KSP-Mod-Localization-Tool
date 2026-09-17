# 05: Wire into `run()` and close Phase 2 acceptance

**What to build:** End-to-end `run(..., translate=True)` with mocked HTTP: rewrite + merge + batches + loc + csv + log events + exit code. Re-run without `--translate` keeps Chinese. Second `--translate` with all zh ≠ en sends zero HTTP. Spec §14 table green. `python -m unittest discover -s tests` green. README / HANDOFF / CLAUDE.md already point at the spec; only touch them if behavior notes drifted.

**Blocked by:** 04 Batch pending keys and reject the whole batch on bad JSON

**Status:** open

- [ ] Already-rewritten mod with `en-us.cfg` translates from en-us
- [ ] Failed batch keys stay English in both `zh-cn.cfg` and csv
- [ ] Successful keys match in cfg and csv
- [ ] Log has `AI_BATCH_START` / `AI_BATCH_SUCCESS` or `AI_BATCH_FAILED` and `RUN_FINISHED`
- [ ] Second run without `--translate` keeps Chinese
- [ ] Second `--translate` with nothing pending: no urlopen
- [ ] `python localizer.py --translate` process exit 1 on config/batch failure
- [ ] Full unittest suite green
- [ ] Still single-file `localizer.py`, no SDK
