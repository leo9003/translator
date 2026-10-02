from dataclasses import dataclass, field
from typing import Optional, Union


# =========================================================
# Run
# =========================================================


@dataclass
class RunIR:
    text: str

    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None

    font_name: Optional[str] = None
    font_size: Optional[float] = None


# =========================================================
# Paragraph Numbering
# =========================================================


@dataclass
class ParagraphNumberingIR:
    """
    Word list / numbering metadata.

    Example OOXML:

    <w:numPr>
        <w:ilvl w:val="0"/>
        <w:numId w:val="3"/>
    </w:numPr>
    """

    num_id: Optional[int] = None
    level: Optional[int] = None


# =========================================================
# Paragraph Formatting
# =========================================================


@dataclass
class ParagraphFormatIR:

    alignment: Optional[int] = None

    space_before: Optional[float] = None
    space_after: Optional[float] = None

    # Relative line spacing:
    #
    # 1.0
    # 1.5
    # 2.0
    #
    line_spacing: Optional[float] = None

    # Absolute line spacing in pt.
    line_spacing_pt: Optional[float] = None

    left_indent: Optional[float] = None
    right_indent: Optional[float] = None
    first_line_indent: Optional[float] = None

    # -----------------------------------------------------
    # Pagination properties
    # -----------------------------------------------------

    keep_together: Optional[bool] = None
    keep_with_next: Optional[bool] = None
    page_break_before: Optional[bool] = None
    widow_control: Optional[bool] = None


# =========================================================
# Paragraph
# =========================================================


@dataclass
class ParagraphBlock:
    id: str
    type: str
    text: str

    style: Optional[str] = None

    formatting: ParagraphFormatIR = field(
        default_factory=ParagraphFormatIR
    )

    numbering: ParagraphNumberingIR = field(
        default_factory=ParagraphNumberingIR
    )

    runs: list[RunIR] = field(
        default_factory=list
    )


# =========================================================
# Table Cell
# =========================================================


@dataclass
class CellIR:

    blocks: list["Block"] = field(
        default_factory=list
    )

    width: Optional[float] = None

    vertical_alignment: Optional[int] = None


# =========================================================
# Table Row
# =========================================================


@dataclass
class RowIR:

    cells: list[CellIR] = field(
        default_factory=list
    )


# =========================================================
# Table Formatting
# =========================================================


@dataclass
class TableFormatIR:

    style: Optional[str] = None

    alignment: Optional[int] = None

    autofit: Optional[bool] = None


# =========================================================
# Table
# =========================================================


@dataclass
class TableBlock:

    id: str
    type: str

    formatting: TableFormatIR = field(
        default_factory=TableFormatIR
    )

    column_widths: list[float] = field(
        default_factory=list
    )

    rows: list[RowIR] = field(
        default_factory=list
    )


# =========================================================
# Block
# =========================================================


Block = Union[
    ParagraphBlock,
    TableBlock,
]


# =========================================================
# Section
# =========================================================


@dataclass
class SectionIR:

    # -----------------------------------------------------
    # Page
    # -----------------------------------------------------

    page_width: Optional[float] = None
    page_height: Optional[float] = None

    orientation: Optional[int] = None

    # -----------------------------------------------------
    # Margins
    # -----------------------------------------------------

    top_margin: Optional[float] = None
    bottom_margin: Optional[float] = None

    left_margin: Optional[float] = None
    right_margin: Optional[float] = None

    # -----------------------------------------------------
    # Header / Footer position
    # -----------------------------------------------------

    header_distance: Optional[float] = None
    footer_distance: Optional[float] = None

    # -----------------------------------------------------
    # Section start type
    # -----------------------------------------------------

    start_type: Optional[int] = None


# =========================================================
# Document
# =========================================================


@dataclass
class DocumentIR:

    filename: str

    blocks: list[Block] = field(
        default_factory=list
    )

    sections: list[SectionIR] = field(
        default_factory=list
    )