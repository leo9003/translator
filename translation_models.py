from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranslationContext:
    block_type: str

    table_id: Optional[str] = None
    row_index: Optional[int] = None
    cell_index: Optional[int] = None


@dataclass
class TranslationUnit:
    id: str
    block_id: str
    source_text: str
    context: TranslationContext


@dataclass
class TranslationResult:
    id: str

    # "translate" or "preserve"
    action: str

    translated_text: str


@dataclass
class TranslationBatch:
    units: list[TranslationUnit] = field(
        default_factory=list
    )


@dataclass
class TranslationResultBatch:
    results: list[TranslationResult] = field(
        default_factory=list
    )