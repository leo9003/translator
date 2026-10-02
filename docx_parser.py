from pathlib import Path
from typing import Optional

from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

from models import (
    Block,
    CellIR,
    DocumentIR,
    ParagraphBlock,
    ParagraphFormatIR,
    ParagraphNumberingIR,
    RowIR,
    RunIR,
    SectionIR,
    TableBlock,
    TableFormatIR,
)


class DocxParser:

    def __init__(self) -> None:

        self.paragraph_index = 0
        self.table_index = 0

    # =========================================================
    # Public API
    # =========================================================

    def parse(
        self,
        file_path: str,
    ) -> DocumentIR:

        path = Path(file_path)

        if not path.exists():

            raise FileNotFoundError(
                f"File not found: {path}"
            )

        if path.suffix.lower() != ".docx":

            raise ValueError(
                "Only .docx files are supported."
            )

        # -----------------------------------------------------
        # python-docx typing expects str / file-like.
        # -----------------------------------------------------

        document = Document(
            str(path)
        )

        # -----------------------------------------------------
        # Reset IDs for every document.
        # -----------------------------------------------------

        self.paragraph_index = 0
        self.table_index = 0

        # -----------------------------------------------------
        # Body
        # -----------------------------------------------------

        blocks = self._parse_container(
            document
        )

        # -----------------------------------------------------
        # Sections
        # -----------------------------------------------------

        sections = self._parse_sections(
            document
        )

        return DocumentIR(
            filename=path.name,
            blocks=blocks,
            sections=sections,
        )

    # =========================================================
    # Container
    # =========================================================

    def _parse_container(
        self,
        container: DocumentObject | _Cell,
    ) -> list[Block]:

        blocks: list[Block] = []

        # -----------------------------------------------------
        # Document body
        # -----------------------------------------------------

        if isinstance(
            container,
            DocumentObject,
        ):

            parent_element = (
                container.element.body
            )

        # -----------------------------------------------------
        # Table cell
        # -----------------------------------------------------

        elif isinstance(
            container,
            _Cell,
        ):

            parent_element = (
                container._tc
            )

        else:

            raise TypeError(
                "Unsupported container type: "
                f"{type(container)}"
            )

        # -----------------------------------------------------
        # Preserve XML order.
        # -----------------------------------------------------

        for child in (
            parent_element.iterchildren()
        ):

            # -------------------------------------------------
            # Paragraph
            # -------------------------------------------------

            if isinstance(
                child,
                CT_P,
            ):

                paragraph = Paragraph(
                    child,
                    container,
                )

                paragraph_ir = (
                    self._parse_paragraph(
                        paragraph
                    )
                )

                blocks.append(
                    paragraph_ir
                )

            # -------------------------------------------------
            # Table
            # -------------------------------------------------

            elif isinstance(
                child,
                CT_Tbl,
            ):

                table = Table(
                    child,
                    container,
                )

                table_ir = (
                    self._parse_table(
                        table
                    )
                )

                blocks.append(
                    table_ir
                )

        return blocks

    # =========================================================
    # Paragraph
    # =========================================================

    def _parse_paragraph(
        self,
        paragraph: Paragraph,
    ) -> ParagraphBlock:

        paragraph_id = (
            f"p_{self.paragraph_index:04d}"
        )

        self.paragraph_index += 1

        # -----------------------------------------------------
        # Runs
        # -----------------------------------------------------

        runs: list[RunIR] = []

        for run in paragraph.runs:

            if not run.text:
                continue

            # -------------------------------------------------
            # Font size
            # -------------------------------------------------

            font_size: Optional[
                float
            ] = None

            if (
                run.font.size
                is not None
            ):

                font_size = float(
                    run.font.size.pt
                )

            # -------------------------------------------------
            # Underline
            #
            # python-docx may return:
            #
            # bool
            # WD_UNDERLINE
            # None
            # -------------------------------------------------

            raw_underline = (
                run.underline
            )

            underline_value: Optional[
                bool
            ]

            if raw_underline is None:

                underline_value = None

            else:

                underline_value = bool(
                    raw_underline
                )

            # -------------------------------------------------
            # Run IR
            # -------------------------------------------------

            run_ir = RunIR(
                text=run.text,
                bold=run.bold,
                italic=run.italic,
                underline=underline_value,
                font_name=run.font.name,
                font_size=font_size,
            )

            runs.append(
                run_ir
            )

        # -----------------------------------------------------
        # Style
        # -----------------------------------------------------

        style: Optional[
            str
        ] = None

        if (
            paragraph.style
            is not None
        ):

            style = (
                paragraph.style.name
            )

        # -----------------------------------------------------
        # Paragraph format
        # -----------------------------------------------------

        paragraph_format = (
            paragraph.paragraph_format
        )

        (
            line_spacing,
            line_spacing_pt,
        ) = self._parse_line_spacing(
            paragraph_format.line_spacing
        )

        formatting = (
            ParagraphFormatIR(
                alignment=(
                    int(
                        paragraph.alignment
                    )
                    if (
                        paragraph.alignment
                        is not None
                    )
                    else None
                ),

                space_before=(
                    float(
                        paragraph_format
                        .space_before
                        .pt
                    )
                    if (
                        paragraph_format
                        .space_before
                        is not None
                    )
                    else None
                ),

                space_after=(
                    float(
                        paragraph_format
                        .space_after
                        .pt
                    )
                    if (
                        paragraph_format
                        .space_after
                        is not None
                    )
                    else None
                ),

                line_spacing=(
                    line_spacing
                ),

                line_spacing_pt=(
                    line_spacing_pt
                ),

                left_indent=(
                    float(
                        paragraph_format
                        .left_indent
                        .pt
                    )
                    if (
                        paragraph_format
                        .left_indent
                        is not None
                    )
                    else None
                ),

                right_indent=(
                    float(
                        paragraph_format
                        .right_indent
                        .pt
                    )
                    if (
                        paragraph_format
                        .right_indent
                        is not None
                    )
                    else None
                ),

                first_line_indent=(
                    float(
                        paragraph_format
                        .first_line_indent
                        .pt
                    )
                    if (
                        paragraph_format
                        .first_line_indent
                        is not None
                    )
                    else None
                ),

                # ---------------------------------------------
                # Pagination
                # ---------------------------------------------

                keep_together=(
                    paragraph_format
                    .keep_together
                ),

                keep_with_next=(
                    paragraph_format
                    .keep_with_next
                ),

                page_break_before=(
                    paragraph_format
                    .page_break_before
                ),

                widow_control=(
                    paragraph_format
                    .widow_control
                ),
            )
        )

        # -----------------------------------------------------
        # Numbering / List
        # -----------------------------------------------------

        numbering = (
            self._parse_numbering(
                paragraph
            )
        )

        return ParagraphBlock(
            id=paragraph_id,
            type="paragraph",
            text=paragraph.text,
            style=style,
            formatting=formatting,
            numbering=numbering,
            runs=runs,
        )

    # =========================================================
    # Numbering
    # =========================================================

    def _parse_numbering(
        self,
        paragraph: Paragraph,
    ) -> ParagraphNumberingIR:

        num_id: Optional[int] = None
        level: Optional[int] = None

        # -----------------------------------------------------
        # Paragraph XML
        #
        # <w:p>
        #   <w:pPr>
        #       <w:numPr>
        #           <w:ilvl w:val="0"/>
        #           <w:numId w:val="1"/>
        #       </w:numPr>
        #   </w:pPr>
        # </w:p>
        # -----------------------------------------------------

        p = paragraph._p

        p_pr = p.pPr

        if p_pr is None:

            return ParagraphNumberingIR()

        num_pr = p_pr.numPr

        if num_pr is None:

            return ParagraphNumberingIR()

        # -----------------------------------------------------
        # numId
        # -----------------------------------------------------

        if (
            num_pr.numId
            is not None
        ):

            raw_num_id = (
                num_pr.numId.val
            )

            if raw_num_id is not None:

                num_id = int(
                    raw_num_id
                )

        # -----------------------------------------------------
        # ilvl
        # -----------------------------------------------------

        if (
            num_pr.ilvl
            is not None
        ):

            raw_level = (
                num_pr.ilvl.val
            )

            if raw_level is not None:

                level = int(
                    raw_level
                )

        return ParagraphNumberingIR(
            num_id=num_id,
            level=level,
        )

    # =========================================================
    # Table
    # =========================================================

    def _parse_table(
        self,
        table: Table,
    ) -> TableBlock:

        table_id = (
            f"t_{self.table_index:04d}"
        )

        self.table_index += 1

        # -----------------------------------------------------
        # Table style
        # -----------------------------------------------------

        table_style: Optional[
            str
        ] = None

        if table.style is not None:

            table_style = (
                table.style.name
            )

        # -----------------------------------------------------
        # Alignment
        # -----------------------------------------------------

        table_alignment: Optional[
            int
        ] = None

        if (
            table.alignment
            is not None
        ):

            table_alignment = int(
                table.alignment
            )

        # -----------------------------------------------------
        # Formatting
        # -----------------------------------------------------

        formatting = TableFormatIR(
            style=table_style,
            alignment=table_alignment,
            autofit=table.autofit,
        )

        # -----------------------------------------------------
        # OOXML tblGrid
        # -----------------------------------------------------

        column_widths = (
            self._get_table_column_widths(
                table
            )
        )

        # -----------------------------------------------------
        # Rows
        # -----------------------------------------------------

        rows: list[RowIR] = []

        for row in table.rows:

            cells: list[
                CellIR
            ] = []

            for cell in row.cells:

                # ---------------------------------------------
                # Width
                # ---------------------------------------------

                cell_width: Optional[
                    float
                ] = None

                if (
                    cell.width
                    is not None
                ):

                    cell_width = float(
                        cell.width.pt
                    )

                # ---------------------------------------------
                # Vertical alignment
                # ---------------------------------------------

                vertical_alignment: Optional[
                    int
                ] = None

                if (
                    cell.vertical_alignment
                    is not None
                ):

                    vertical_alignment = int(
                        cell.vertical_alignment
                    )

                # ---------------------------------------------
                # Recursive content
                # ---------------------------------------------

                cell_blocks = (
                    self._parse_container(
                        cell
                    )
                )

                cell_ir = CellIR(
                    blocks=cell_blocks,
                    width=cell_width,
                    vertical_alignment=(
                        vertical_alignment
                    ),
                )

                cells.append(
                    cell_ir
                )

            rows.append(
                RowIR(
                    cells=cells
                )
            )

        return TableBlock(
            id=table_id,
            type="table",
            formatting=formatting,
            column_widths=column_widths,
            rows=rows,
        )

    # =========================================================
    # Table Column Widths
    # =========================================================

    def _get_table_column_widths(
        self,
        table: Table,
    ) -> list[float]:

        widths: list[
            float
        ] = []

        tbl = table._tbl

        tbl_grid = (
            tbl.tblGrid
        )

        if tbl_grid is None:

            return widths

        for grid_col in (
            tbl_grid.gridCol_lst
        ):

            width = (
                grid_col.w
            )

            if width is None:
                continue

            widths.append(
                float(
                    width.pt
                )
            )

        return widths

    # =========================================================
    # Line Spacing
    # =========================================================

    def _parse_line_spacing(
        self,
        line_spacing,
    ) -> tuple[
        Optional[float],
        Optional[float],
    ]:

        if line_spacing is None:

            return (
                None,
                None,
            )

        # -----------------------------------------------------
        # Relative multiplier
        # -----------------------------------------------------

        if isinstance(
            line_spacing,
            (int, float),
        ):

            return (
                float(
                    line_spacing
                ),
                None,
            )

        # -----------------------------------------------------
        # Absolute pt
        # -----------------------------------------------------

        if hasattr(
            line_spacing,
            "pt",
        ):

            return (
                None,
                float(
                    line_spacing.pt
                ),
            )

        return (
            None,
            None,
        )

    # =========================================================
    # Sections
    # =========================================================

    def _parse_sections(
        self,
        document: DocumentObject,
    ) -> list[SectionIR]:

        sections: list[
            SectionIR
        ] = []

        for section in (
            document.sections
        ):

            section_ir = SectionIR(

                page_width=(
                    float(
                        section.page_width.pt
                    )
                    if (
                        section.page_width
                        is not None
                    )
                    else None
                ),

                page_height=(
                    float(
                        section.page_height.pt
                    )
                    if (
                        section.page_height
                        is not None
                    )
                    else None
                ),

                orientation=(
                    int(
                        section.orientation
                    )
                    if (
                        section.orientation
                        is not None
                    )
                    else None
                ),

                top_margin=(
                    float(
                        section.top_margin.pt
                    )
                    if (
                        section.top_margin
                        is not None
                    )
                    else None
                ),

                bottom_margin=(
                    float(
                        section.bottom_margin.pt
                    )
                    if (
                        section.bottom_margin
                        is not None
                    )
                    else None
                ),

                left_margin=(
                    float(
                        section.left_margin.pt
                    )
                    if (
                        section.left_margin
                        is not None
                    )
                    else None
                ),

                right_margin=(
                    float(
                        section.right_margin.pt
                    )
                    if (
                        section.right_margin
                        is not None
                    )
                    else None
                ),

                header_distance=(
                    float(
                        section.header_distance.pt
                    )
                    if (
                        section.header_distance
                        is not None
                    )
                    else None
                ),

                footer_distance=(
                    float(
                        section.footer_distance.pt
                    )
                    if (
                        section.footer_distance
                        is not None
                    )
                    else None
                ),

                start_type=(
                    int(
                        section.start_type
                    )
                    if (
                        section.start_type
                        is not None
                    )
                    else None
                ),
            )

            sections.append(
                section_ir
            )

        return sections