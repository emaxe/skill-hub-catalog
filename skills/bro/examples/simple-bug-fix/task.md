# Task: Fix off-by-one error in pagination helper

**User request:**
> The `paginate_results` helper in `utils/pagination.py` returns an empty page when `page=1` and `per_page=10` but there are exactly 10 items. It should return the full page, not empty.

**Scope:** Small bug fix — single function, one test file.
