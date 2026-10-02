from models import (
    Block,
    DocumentIR,
    ParagraphBlock,
    TableBlock,
)

from translation_models import (
    TranslationBatch,
    TranslationContext,
    TranslationUnit,
)


class TranslationUnitBuilder:

    def __init__(self) -> None:
        self.unit_index = 0

    # =========================================================
    # Public API
    # =========================================================

    def build(
        self,
        document_ir: DocumentIR,
    ) -> TranslationBatch:

        # Reset every build so IDs are deterministic.
        self.unit_index = 0

        units: list[TranslationUnit] = []

        # =====================================================
        # Top-level document blocks
        # =====================================================

        for block in document_ir.blocks:

            self._collect_block(
                block=block,
                units=units,
                table_id=None,
                row_index=None,
                cell_index=None,
            )

        return TranslationBatch(
            units=units
        )

    # =========================================================
    # Block Traversal
    # =========================================================

    def _collect_block(
        self,
        block: Block,
        units: list[TranslationUnit],
        table_id: str | None,
        row_index: int | None,
        cell_index: int | None,
    ) -> None:

        # =====================================================
        # Paragraph
        # =====================================================

        if isinstance(
            block,
            ParagraphBlock,
        ):

            self._collect_paragraph(
                paragraph=block,
                units=units,
                table_id=table_id,
                row_index=row_index,
                cell_index=cell_index,
            )

            return

        # =====================================================
        # Table
        # =====================================================

        if isinstance(
            block,
            TableBlock,
        ):

            self._collect_table(
                table=block,
                units=units,
            )

            return

        raise TypeError(
            "Unsupported block type: "
            f"{type(block)}"
        )

    # =========================================================
    # Paragraph
    # =========================================================

    def _collect_paragraph(
        self,
        paragraph: ParagraphBlock,
        units: list[TranslationUnit],
        table_id: str | None,
        row_index: int | None,
        cell_index: int | None,
    ) -> None:

        # =====================================================
        # Empty paragraph
        #
        # There is no semantic content for the LLM.
        # Formatting still remains in DocumentIR.
        # =====================================================

        text = paragraph.text.strip()

        if not text:
            return

        # =====================================================
        # Determine context
        # =====================================================

        if table_id is None:

            block_type = "paragraph"

        else:

            block_type = "table_cell_paragraph"

        context = TranslationContext(
            block_type=block_type,
            table_id=table_id,
            row_index=row_index,
            cell_index=cell_index,
        )

        # =====================================================
        # Translation Unit
        # =====================================================

        unit = TranslationUnit(
            id=self._next_unit_id(),
            block_id=paragraph.id,

            # IMPORTANT:
            #
            # Do not use the stripped text as source_text.
            #
            # strip() above is only used to determine whether
            # the paragraph is empty.
            #
            # The original paragraph text is preserved here.
            source_text=paragraph.text,

            context=context,
        )

        units.append(
            unit
        )

    # =========================================================
    # Table
    # =========================================================

    def _collect_table(
        self,
        table: TableBlock,
        units: list[TranslationUnit],
    ) -> None:

        # =====================================================
        # Rows
        # =====================================================

        for (
            row_index,
            row,
        ) in enumerate(
            table.rows
        ):

            # =================================================
            # Cells
            # =================================================

            for (
                cell_index,
                cell,
            ) in enumerate(
                row.cells
            ):

                # =============================================
                # Recursive blocks
                #
                # A cell can contain:
                #
                # Paragraph
                # Table
                # Paragraph
                #
                # =============================================

                for block in cell.blocks:

                    # -----------------------------------------
                    # Paragraph inside current table
                    # -----------------------------------------

                    if isinstance(
                        block,
                        ParagraphBlock,
                    ):

                        self._collect_block(
                            block=block,
                            units=units,
                            table_id=table.id,
                            row_index=row_index,
                            cell_index=cell_index,
                        )

                    # -----------------------------------------
                    # Nested table
                    #
                    # The nested table has its own table ID,
                    # row indexes and cell indexes.
                    # -----------------------------------------

                    elif isinstance(
                        block,
                        TableBlock,
                    ):

                        self._collect_table(
                            table=block,
                            units=units,
                        )

                    else:

                        raise TypeError(
                            "Unsupported cell block type: "
                            f"{type(block)}"
                        )

    # =========================================================
    # Translation Unit ID
    # =========================================================

    def _next_unit_id(
        self,
    ) -> str:

        unit_id = (
            f"tu_{self.unit_index:04d}"
        )

        self.unit_index += 1

        return unit_id