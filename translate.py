import sys
from pathlib import Path

from docx_parser import (
    DocxParser,
)

from docx_renderer import (
    DocxRenderer,
)

from translation_builder import (
    TranslationUnitBuilder,
)

from translation_mapper import (
    TranslationMapper,
)

from openai_translator import (
    OpenAITranslator,
)


def main() -> None:

    # =========================================================
    # CLI
    #
    # python3 translate.py input.docx English
    # =========================================================

    if len(sys.argv) < 2:

        print(
            "Usage: "
            "python3 translate.py "
            "<docx_file> "
            "[target_language]"
        )

        sys.exit(1)

    input_path = Path(
        sys.argv[1]
    )

    target_language = (
        sys.argv[2]
        if len(sys.argv) >= 3
        else "English"
    )

    # =========================================================
    # Validate input
    # =========================================================

    if not input_path.exists():

        raise FileNotFoundError(
            f"File not found: {input_path}"
        )

    if (
        input_path.suffix.lower()
        != ".docx"
    ):

        raise ValueError(
            "Only .docx files are supported."
        )

    # =========================================================
    # Start
    # =========================================================

    print()
    print(
        "========================================"
    )

    print(
        "Document Translation"
    )

    print(
        "========================================"
    )

    print()

    print(
        f"Input: {input_path}"
    )

    print(
        f"Target language: "
        f"{target_language}"
    )

    # =========================================================
    # 1. Parse
    # =========================================================

    print()
    print(
        "[1/5] Parsing DOCX..."
    )

    parser = (
        DocxParser()
    )

    document_ir = parser.parse(
        str(input_path)
    )

    # =========================================================
    # 2. Translation Units
    # =========================================================

    print(
        "[2/5] Building "
        "translation units..."
    )

    builder = (
        TranslationUnitBuilder()
    )

    translation_batch = (
        builder.build(
            document_ir
        )
    )

    print(
        "      Translation units: "
        f"{len(translation_batch.units)}"
    )

    if not translation_batch.units:

        print()
        print(
            "No translatable text found."
        )

        return

    # =========================================================
    # 3. OpenAI
    # =========================================================

    print(
        "[3/5] Translating "
        "with OpenAI..."
    )

    translator = (
        OpenAITranslator()
    )

    print(
        f"      Model: "
        f"{translator.model}"
    )

    result_batch = (
        translator.translate(
            batch=translation_batch,
            source_language="auto",
            target_language=(
                target_language
            ),
        )
    )

    # ---------------------------------------------------------
    # Stats
    # ---------------------------------------------------------

    translated_count = sum(
        1
        for result
        in result_batch.results
        if (
            result.action
            == "translate"
        )
    )

    preserved_count = sum(
        1
        for result
        in result_batch.results
        if (
            result.action
            == "preserve"
        )
    )

    print(
        "      Results: "
        f"{len(result_batch.results)}"
    )

    print(
        "      Translated: "
        f"{translated_count}"
    )

    print(
        "      Preserved: "
        f"{preserved_count}"
    )

    # =========================================================
    # 4. Map translations back to DocumentIR
    # =========================================================

    print(
        "[4/5] Mapping translations "
        "back to document..."
    )

    mapper = (
        TranslationMapper()
    )

    translated_document = (
        mapper.apply(
            document_ir=document_ir,
            translation_batch=(
                translation_batch
            ),
            result_batch=(
                result_batch
            ),
        )
    )

    # =========================================================
    # 5. Template-based rendering
    # =========================================================

    print(
        "[5/5] Rendering translated "
        "DOCX from original template..."
    )

    output_dir = Path(
        "output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_language = (
        target_language
        .strip()
        .replace(
            " ",
            "_",
        )
        .replace(
            "/",
            "_",
        )
    )

    output_path = (
        output_dir
        / (
            f"{input_path.stem}"
            f"_{safe_language}"
            ".docx"
        )
    )

    renderer = (
        DocxRenderer()
    )

    renderer.render(
        source_path=str(
            input_path
        ),
        document_ir=(
            translated_document
        ),
        output_path=str(
            output_path
        ),
    )

    # =========================================================
    # Done
    # =========================================================

    print()
    print(
        "========================================"
    )

    print(
        "Translation completed"
    )

    print(
        "========================================"
    )

    print()

    print(
        f"Output: {output_path}"
    )


if __name__ == "__main__":
    main()