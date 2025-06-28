"""Per-tool merge helpers for agent.helper.

Each module in this package should expose a ``merge(raw_output)`` function that
converts the raw tool output into a JSON-serialisable structure suitable for
inclusion in the canonical summary produced by :pyfunc:`agent.helper.merge_results`.
""" 