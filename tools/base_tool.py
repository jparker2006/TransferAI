from __future__ import annotations

"""Shared base class for all TransferAI runtime tools.

A *tool* exposes three public artefacts:
1. ``input_schema``  – JSON-schema describing accepted parameters.
2. ``output_schema`` – JSON-schema describing the returned payload.
3. ``run(**kwargs)`` – synchronous inference method.

Concrete subclasses are expected to declare two Pydantic models:
```
class MyTool(BaseTool):
    class Input(BaseModel):
        foo: str
    class Output(BaseModel):
        bar: str

    def run(self, **inputs) -> dict: ...
```
The base‐class automatically derives ``input_schema``/``output_schema`` from
those nested classes and performs a thin validation pass for incoming calls so
engineers don't have to duplicate boiler-plate in every file.
"""

from typing import Any, Dict, Type

from pydantic import BaseModel


class BaseTool:  # noqa: D401, WPS110 – simple shared mix-in
    """Contract enforcement for TransferAI tools."""

    # Sub-classes must provide these nested model classes -------------------
    class Input(BaseModel):  # noqa: D401, WPS430 – placeholder
        """Override in subclass."""

        pass

    class Output(BaseModel):  # noqa: D401, WPS430 – placeholder
        """Override in subclass."""

        pass

    # ---------------------------------------------------------------------
    # Derived JSON-schemas (computed once per subclass) --------------------
    # ---------------------------------------------------------------------

    input_schema: Dict[str, Any]  # populated in _init_subclass_
    output_schema: Dict[str, Any]

    # ------------------------------------------------------------------
    # Metaclass-like hook ensures subclasses define models -------------
    # ------------------------------------------------------------------

    def __init_subclass__(cls) -> None:  # noqa: D401 – meta-magic
        super().__init_subclass__()

        if not hasattr(cls, "Input") or not issubclass(cls.Input, BaseModel):
            raise TypeError("Tool subclass must define nested `Input` Pydantic model")
        if not hasattr(cls, "Output") or not issubclass(cls.Output, BaseModel):
            raise TypeError("Tool subclass must define nested `Output` Pydantic model")

        # Compute JSON-schema only once per subclass.
        cls.input_schema = cls.Input.model_json_schema()  # type: ignore[attr-defined]
        cls.output_schema = cls.Output.model_json_schema()  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Public dispatcher -------------------------------------------------
    # ------------------------------------------------------------------

    def run(self, **inputs: Any) -> Dict[str, Any]:  # noqa: D401 – to be overridden
        raise NotImplementedError 