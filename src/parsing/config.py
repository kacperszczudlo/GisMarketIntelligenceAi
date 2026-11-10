"""Docling pipeline configuration with TableFormer and OCR options."""

from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
)

MAX_PDF_SIZE_MB = 50
PARSING_TIMEOUT_SECONDS = 300


def get_docling_pipeline_options(
    do_ocr: bool = True,
    accurate_tables: bool = True,
) -> PdfPipelineOptions:
    """Builds and returns optimized Docling PdfPipelineOptions for Polish SWZ documents."""
    options = PdfPipelineOptions()
    options.do_table_structure = True

    if accurate_tables:
        options.table_structure_options.mode = TableFormerMode.ACCURATE

    options.do_ocr = do_ocr
    return options
