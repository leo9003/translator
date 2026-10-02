import json
import os
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from translation_models import (
    TranslationBatch,
    TranslationResult,
    TranslationResultBatch,
)


# =========================================================
# Structured Output Schema
#
# These Pydantic models define exactly what OpenAI
# is allowed to return.
# =========================================================


class ModelTranslationItem(BaseModel):
    id: str

    action: Literal[
        "translate",
        "preserve",
    ]

    translated_text: str


class ModelTranslationResponse(BaseModel):
    translations: list[
        ModelTranslationItem
    ]


# =========================================================
# OpenAI Translation Provider
# =========================================================


class OpenAITranslator:

    def __init__(
        self,
        model: str | None = None,
    ) -> None:

        # -----------------------------------------------------
        # Load .env
        # -----------------------------------------------------

        load_dotenv()

        # -----------------------------------------------------
        # API Key
        # -----------------------------------------------------

        api_key = os.getenv(
            "OPENAI_API_KEY"
        )

        if not api_key:

            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file."
            )

        # -----------------------------------------------------
        # Model
        #
        # Can be overridden by:
        #
        # OPENAI_MODEL=gpt-5.6-terra
        # -----------------------------------------------------

        self.model = (
            model
            or os.getenv(
                "OPENAI_MODEL"
            )
            or "gpt-5.6-terra"
        )

        # -----------------------------------------------------
        # Client
        # -----------------------------------------------------

        self.client = OpenAI(
            api_key=api_key
        )

    # =========================================================
    # Public API
    # =========================================================

    def translate(
        self,
        batch: TranslationBatch,
        target_language: str,
        source_language: str = "auto",
    ) -> TranslationResultBatch:

        if not batch.units:

            return TranslationResultBatch()

        # -----------------------------------------------------
        # Convert TranslationUnits into the thin semantic view
        # sent to the model.
        #
        # Notice:
        #
        # NO font
        # NO bold
        # NO table width
        # NO Word formatting
        # -----------------------------------------------------

        units_payload = []

        for unit in batch.units:

            units_payload.append(
                {
                    "id": unit.id,
                    "text": unit.source_text,
                    "context": {
                        "block_type": (
                            unit.context.block_type
                        ),
                        "table_id": (
                            unit.context.table_id
                        ),
                        "row_index": (
                            unit.context.row_index
                        ),
                        "cell_index": (
                            unit.context.cell_index
                        ),
                    },
                }
            )

        # -----------------------------------------------------
        # User payload
        # -----------------------------------------------------

        payload = {
            "source_language": source_language,
            "target_language": target_language,
            "units": units_payload,
        }

        # -----------------------------------------------------
        # Responses API + Structured Outputs
        # -----------------------------------------------------

        response = (
            self.client.responses.parse(
                model=self.model,

                instructions=(
                    "You are the translation engine for a "
                    "document translation system.\n\n"

                    "Translate document text accurately while "
                    "preserving its meaning, technical terminology, "
                    "numbers, symbols, formulas, identifiers, "
                    "dataset field names, abbreviations, and units "
                    "when they should remain unchanged.\n\n"

                    "You receive multiple translation units from "
                    "the same document. Use their structural "
                    "context to understand relationships between "
                    "units.\n\n"

                    "For table content, units with the same "
                    "table_id and row_index belong to the same "
                    "table row. Use the other cells in that row "
                    "as semantic context.\n\n"

                    "Decide independently for each unit whether "
                    "its text should be translated or preserved.\n\n"

                    "Use action='translate' when translation is "
                    "appropriate.\n"

                    "Use action='preserve' when the original text "
                    "should remain unchanged, such as a technical "
                    "identifier, schema field name, abbreviation, "
                    "number-only value, formula, or code-like "
                    "token.\n\n"

                    "When action='preserve', translated_text must "
                    "exactly equal the original text.\n\n"

                    "When action='translate', translated_text must "
                    "contain only the translated content. Do not "
                    "add explanations, notes, quotation marks, or "
                    "commentary.\n\n"

                    "Preserve important technical tokens embedded "
                    "inside otherwise translated text when their "
                    "translation would change their technical "
                    "meaning. Examples include variable names such "
                    "as Tmax, TX90p, CDD, crop, heat_days, and "
                    "units such as kg/ha.\n\n"

                    "Return exactly one result for every input "
                    "unit. Keep every input id unchanged."
                ),

                input=json.dumps(
                    payload,
                    ensure_ascii=False,
                ),

                text_format=(
                    ModelTranslationResponse
                ),
            )
        )

        # -----------------------------------------------------
        # Parsed Structured Output
        # -----------------------------------------------------

        parsed = response.output_parsed

        if parsed is None:

            raise RuntimeError(
                "OpenAI returned no parsed "
                "translation result."
            )

        # -----------------------------------------------------
        # Validate IDs
        # -----------------------------------------------------

        self._validate_response(
            batch=batch,
            response=parsed,
        )

        # -----------------------------------------------------
        # Convert API schema → application schema
        # -----------------------------------------------------

        results: list[
            TranslationResult
        ] = []

        for item in parsed.translations:

            results.append(
                TranslationResult(
                    id=item.id,
                    action=item.action,
                    translated_text=(
                        item.translated_text
                    ),
                )
            )

        return TranslationResultBatch(
            results=results
        )

    # =========================================================
    # Response Validation
    # =========================================================

    def _validate_response(
        self,
        batch: TranslationBatch,
        response: ModelTranslationResponse,
    ) -> None:

        input_ids = [
            unit.id
            for unit in batch.units
        ]

        output_ids = [
            item.id
            for item in response.translations
        ]

        # -----------------------------------------------------
        # Duplicate output IDs
        # -----------------------------------------------------

        if (
            len(output_ids)
            != len(set(output_ids))
        ):

            raise ValueError(
                "OpenAI response contains "
                "duplicate translation IDs."
            )

        # -----------------------------------------------------
        # Missing / extra IDs
        # -----------------------------------------------------

        if set(input_ids) != set(output_ids):

            missing_ids = (
                set(input_ids)
                - set(output_ids)
            )

            extra_ids = (
                set(output_ids)
                - set(input_ids)
            )

            raise ValueError(
                "OpenAI translation ID mismatch.\n"
                f"Missing IDs: {sorted(missing_ids)}\n"
                f"Extra IDs: {sorted(extra_ids)}"
            )

        # -----------------------------------------------------
        # Preserve must be exact
        # -----------------------------------------------------

        source_by_id = {
            unit.id: unit.source_text
            for unit in batch.units
        }

        for item in response.translations:

            if item.action != "preserve":
                continue

            original = source_by_id[
                item.id
            ]

            if (
                item.translated_text
                != original
            ):

                raise ValueError(
                    "Invalid preserve result for "
                    f"{item.id}. "
                    "translated_text must exactly "
                    "match source_text."
                )