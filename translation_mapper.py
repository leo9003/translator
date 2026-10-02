from copy import deepcopy

from models import (
    Block,
    CellIR,
    DocumentIR,
    ParagraphBlock,
    RunIR,
    TableBlock,
)

from translation_models import (
    TranslationBatch,
    TranslationResultBatch,
)


class TranslationMapper:

    # =========================================================
    # Public API
    # =========================================================

    def apply(
        self,
        document_ir: DocumentIR,
        translation_batch: TranslationBatch,
        result_batch: TranslationResultBatch,
    ) -> DocumentIR:

        # -----------------------------------------------------
        # Work on a copy.
        #
        # This prevents translation from modifying the original
        # DocumentIR in-place.
        # -----------------------------------------------------

        translated_document = deepcopy(
            document_ir
        )

        # -----------------------------------------------------
        # Build:
        #
        # translation unit id
        #       ↓
        # paragraph block id
        #
        # Example:
        #
        # tu_0008 → p_0008
        # -----------------------------------------------------

        unit_to_block_id = {
            unit.id: unit.block_id
            for unit in translation_batch.units
        }

        # -----------------------------------------------------
        # Validate TranslationResult IDs
        # -----------------------------------------------------

        result_ids = {
            result.id
            for result in result_batch.results
        }

        unit_ids = {
            unit.id
            for unit in translation_batch.units
        }

        if result_ids != unit_ids:

            missing_ids = (
                unit_ids
                - result_ids
            )

            extra_ids = (
                result_ids
                - unit_ids
            )

            raise ValueError(
                "Translation result ID mismatch.\n"
                f"Missing IDs: {sorted(missing_ids)}\n"
                f"Extra IDs: {sorted(extra_ids)}"
            )

        # -----------------------------------------------------
        # Find every paragraph in DocumentIR.
        #
        # block_id → ParagraphBlock
        #
        # This also recursively searches table cells.
        # -----------------------------------------------------

        paragraph_map: dict[
            str,
            ParagraphBlock,
        ] = {}

        self._collect_paragraphs(
            blocks=translated_document.blocks,
            paragraph_map=paragraph_map,
        )

        # -----------------------------------------------------
        # Apply translation results
        # -----------------------------------------------------

        for result in result_batch.results:

            block_id = unit_to_block_id.get(
                result.id
            )

            if block_id is None:

                raise ValueError(
                    "Cannot find block mapping for "
                    f"translation unit {result.id}"
                )

            paragraph = paragraph_map.get(
                block_id
            )

            if paragraph is None:

                raise ValueError(
                    "Cannot find ParagraphBlock "
                    f"{block_id} for "
                    f"translation unit {result.id}"
                )

            # -------------------------------------------------
            # Preserve
            #
            # Do absolutely nothing.
            #
            # Original:
            #
            # text
            # runs
            # formatting
            #
            # all remain unchanged.
            # -------------------------------------------------

            if result.action == "preserve":
                continue

            # -------------------------------------------------
            # Translate
            # -------------------------------------------------

            if result.action == "translate":

                self._apply_translation(
                    paragraph=paragraph,
                    translated_text=(
                        result.translated_text
                    ),
                )

                continue

            # -------------------------------------------------
            # Unknown action
            # -------------------------------------------------

            raise ValueError(
                "Unsupported translation action: "
                f"{result.action}"
            )

        return translated_document

    # =========================================================
    # Recursive Paragraph Collection
    # =========================================================

    def _collect_paragraphs(
        self,
        blocks: list[Block],
        paragraph_map: dict[
            str,
            ParagraphBlock,
        ],
    ) -> None:

        for block in blocks:

            # -------------------------------------------------
            # Paragraph
            # -------------------------------------------------

            if isinstance(
                block,
                ParagraphBlock,
            ):

                if block.id in paragraph_map:

                    raise ValueError(
                        "Duplicate paragraph ID: "
                        f"{block.id}"
                    )

                paragraph_map[
                    block.id
                ] = block

                continue

            # -------------------------------------------------
            # Table
            # -------------------------------------------------

            if isinstance(
                block,
                TableBlock,
            ):

                self._collect_table_paragraphs(
                    table=block,
                    paragraph_map=paragraph_map,
                )

                continue

            raise TypeError(
                "Unsupported block type: "
                f"{type(block)}"
            )

    # =========================================================
    # Table Traversal
    # =========================================================

    def _collect_table_paragraphs(
        self,
        table: TableBlock,
        paragraph_map: dict[
            str,
            ParagraphBlock,
        ],
    ) -> None:

        for row in table.rows:

            for cell in row.cells:

                self._collect_cell_paragraphs(
                    cell=cell,
                    paragraph_map=paragraph_map,
                )

    # =========================================================
    # Cell Traversal
    # =========================================================

    def _collect_cell_paragraphs(
        self,
        cell: CellIR,
        paragraph_map: dict[
            str,
            ParagraphBlock,
        ],
    ) -> None:

        self._collect_paragraphs(
            blocks=cell.blocks,
            paragraph_map=paragraph_map,
        )

    # =========================================================
    # Apply Translation
    # =========================================================

    def _apply_translation(
        self,
        paragraph: ParagraphBlock,
        translated_text: str,
    ) -> None:

        # -----------------------------------------------------
        # Update semantic paragraph text.
        # -----------------------------------------------------

        paragraph.text = (
            translated_text
        )

        # -----------------------------------------------------
        # Select formatting for the translated run.
        #
        # v1 strategy:
        #
        # Use the first meaningful original run as the
        # formatting template.
        # -----------------------------------------------------

        template_run = (
            self._find_template_run(
                paragraph
            )
        )

        # -----------------------------------------------------
        # No original run exists.
        # -----------------------------------------------------

        if template_run is None:

            paragraph.runs = [
                RunIR(
                    text=translated_text
                )
            ]

            return

        # -----------------------------------------------------
        # Create one translated run.
        #
        # Important:
        #
        # We intentionally do NOT attempt to align translated
        # words back to the original run boundaries yet.
        #
        # That will be a later formatting-aware translation
        # stage.
        # -----------------------------------------------------

        translated_run = RunIR(
            text=translated_text,
            bold=template_run.bold,
            italic=template_run.italic,
            underline=template_run.underline,
            font_name=template_run.font_name,
            font_size=template_run.font_size,
        )

        paragraph.runs = [
            translated_run
        ]

    # =========================================================
    # Find Formatting Template
    # =========================================================

    def _find_template_run(
        self,
        paragraph: ParagraphBlock,
    ) -> RunIR | None:

        # -----------------------------------------------------
        # Prefer first non-empty run.
        # -----------------------------------------------------

        for run in paragraph.runs:

            if run.text.strip():

                return run

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        if paragraph.runs:

            return paragraph.runs[0]

        return None