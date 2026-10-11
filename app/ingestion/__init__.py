from dataclasses import dataclass, field
from typing import Literal, Any

Kind = Literal["prose", "markdown", "records"]


@dataclass
class RawDoc:
    kind: Kind
    payload: Any          # str for prose/markdown, list[dict] for records
    meta: dict = field(default_factory=dict)