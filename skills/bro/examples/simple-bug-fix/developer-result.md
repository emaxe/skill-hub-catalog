# Developer Result — simple-bug-fix

## Changed Files
- `utils/pagination.py` — line 42: changed `start = (page - 1) * per_page + 1` to `start = (page - 1) * per_page`
- `tests/test_pagination.py` — added regression test `test_paginate_exact_boundary`

## Key Decisions
- The off-by-one was caused by adding +1 to the slice start index. `list[0:10]` is correct for the first 10 items; `list[1:10]` would drop the first item.
- No other callers are affected because `paginate_results` is the only entry point for pagination.
