from typing import Any

# NOTE: This is a minimal example helper. Real logic can be extended later.

def merge(raw_output: Any) -> Any:  # noqa: ANN401 – raw_output is tool-defined
    """Return *raw_output* unchanged.

    The articulation-match tool already returns a JSON-serialisable structure, so
    no additional normalisation is required at this point.
    """

    return raw_output 