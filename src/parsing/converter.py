import gc
import logging
from pathlib import Path
from typing import Optional

from src.config import settings
from src.parsing.config import get_docling_pipeline_options
from src.parsing.table_sanitizer import TableSanitizer

logger = logging.getLogger(__name__)


class DocumentParsingEngine:
    """PDF parsing engine using IBM Docling with TableFormer reconstruction and memory management."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or settings.PROCESSED_DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sanitizer = TableSanitizer()
        self._converter = None

    def _get_converter(self, do_ocr: bool = True):
        if self._converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter, PdfFormatOption

            pipeline_options = get_docling_pipeline_options(do_ocr=do_ocr)
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
        return self._converter

    def _convert_pdf(self, pdf_path: Path, do_ocr: bool = True):
        """Converts PDF using Docling DocumentConverter."""
        converter = self._get_converter(do_ocr=do_ocr)
        return converter.convert(str(pdf_path))

    def convert_to_markdown(
        self,
        pdf_path: Path,
        save_to_disk: bool = True,
        do_ocr: bool = True,
    ) -> str:
        """Converts PDF document to sanitized Markdown with table reconstruction and memory cleanup."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

        logger.info("Starting Docling PDF conversion for %s", pdf_path.name)
        try:
            conversion_res = self._convert_pdf(pdf_path, do_ocr=do_ocr)
            raw_markdown = conversion_res.document.export_to_markdown()

            # Sanitize table structures and layout artifacts
            clean_markdown = self.sanitizer.clean(raw_markdown)

            if save_to_disk:
                target_file = self.output_dir / f"{pdf_path.stem}.md"
                target_file.write_text(clean_markdown, encoding="utf-8")
                logger.info("Saved processed markdown to %s", target_file)

            return clean_markdown
        finally:
            # Memory cleanup to ensure <= 16GB RAM budget is preserved
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
