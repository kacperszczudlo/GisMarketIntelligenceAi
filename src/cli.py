import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("src.cli")


def create_cli_parser() -> argparse.ArgumentParser:
    """Builds argument parser for GisMarketIntelligenceAi CLI."""
    parser = argparse.ArgumentParser(
        prog="gis-intel",
        description="GisMarketIntelligenceAi: Zero-cost Local Advanced RAG for Polish Municipal GIS Procurement",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # Command: ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest tender notices from e-Zamowienia API")
    ingest_parser.add_argument(
        "--cpv",
        type=str,
        default="72220000-3",
        help="CPV code to search for (default: 72220000-3)",
    )
    ingest_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of notices to ingest (default: 5)",
    )
    ingest_parser.add_argument(
        "--download-attachments",
        action="store_true",
        help="Download SWZ/OPZ attachments locally",
    )

    # Command: parse
    parse_parser = subparsers.add_parser("parse", help="Parse PDF attachments to sanitized Markdown via Docling")
    parse_parser.add_argument(
        "--input-dir",
        type=str,
        default="data_raw",
        help="Directory containing downloaded PDF files (default: data_raw)",
    )
    parse_parser.add_argument(
        "--output-dir",
        type=str,
        default="data_processed",
        help="Directory to save parsed Markdown files (default: data_processed)",
    )

    # Command: index
    index_parser = subparsers.add_parser("index", help="Index parsed documents using Parent-Child BGE-M3 embeddings")
    index_parser.add_argument(
        "--procurement-id",
        type=str,
        default=None,
        help="Optional specific procurement ID to index",
    )
    index_parser.add_argument(
        "--markdown-dir",
        type=str,
        default="data_processed",
        help="Directory with Markdown files to index (default: data_processed)",
    )

    # Command: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Execute end-to-end RAG analysis and generate report")
    analyze_parser.add_argument(
        "--ocds-id",
        type=str,
        required=True,
        help="OCDS identifier of the procurement to analyze",
    )
    analyze_parser.add_argument(
        "--query",
        type=str,
        default="Identyfikacja barier rynkowych, formatu .str oraz wymogów licencyjnych EWMAPA",
        help="Analysis query string",
    )
    analyze_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional file path to save the generated Markdown report",
    )
    analyze_parser.add_argument(
        "--min-faithfulness",
        type=float,
        default=0.95,
        help="Strict faithfulness threshold for quality gate (default: 0.95)",
    )

    return parser


# Alias for compatibility with docs/plans
build_parser = create_cli_parser


async def _run_ingest(cpv: str, limit: int, download_attachments: bool) -> int:
    from src.ingestion.client import EZamowieniaClient
    from src.ingestion.downloader import AttachmentDownloader

    client = EZamowieniaClient()
    logger.info("Fetching notices for CPV: %s, limit: %d", cpv, limit)
    notices = await client.fetch_notices(cpv_codes=[cpv], limit=limit)
    print(f"[OK] Pobrano {len(notices)} ogłoszeń przetargowych z e-Zamówienia.")

    if download_attachments and notices:
        downloader = AttachmentDownloader()
        downloaded = 0
        for notice in notices:
            for att in notice.attachments:
                dest = Path("data_raw") / f"{notice.ocds_id}_{att.file_name}"
                meta = await downloader.download_and_save(att.url, dest, att.file_name, notice.ocds_id)
                if meta:
                    downloaded += 1
        print(f"[OK] Pobrano {downloaded} załączników.")
    return 0


def _run_parse(input_dir: str, output_dir: str) -> int:
    from src.parsing.converter import DocumentParsingEngine

    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    pdf_files = list(in_path.glob("*.pdf"))
    if not pdf_files:
        print(f"[INFO] Brak plików PDF w katalogu {input_dir}.")
        return 0

    engine = DocumentParsingEngine()
    converted_count = 0
    for pdf_path in pdf_files:
        try:
            md_content = engine.convert_pdf_to_markdown(pdf_path)
            out_file = out_path / f"{pdf_path.stem}.md"
            out_file.write_text(md_content, encoding="utf-8")
            converted_count += 1
            print(f"[OK] Przekonwertowano: {pdf_path.name} -> {out_file.name}")
        except Exception as e:
            logger.error("Błąd parsowania %s: %s", pdf_path.name, e)

    print(f"[OK] Łącznie przetworzono {converted_count}/{len(pdf_files)} plików.")
    return 0


def _run_index(procurement_id: Optional[str], markdown_dir: str) -> int:
    from src.indexing.embedder import BgeM3Embedder
    from src.indexing.indexer import DatabaseIndexer
    from src.indexing.splitter import ParentChildSplitter

    md_path = Path(markdown_dir)
    files = list(md_path.glob("*.md"))
    if not files:
        print(f"[INFO] Brak plików Markdown w katalogu {markdown_dir}.")
        return 0

    splitter = ParentChildSplitter()
    embedder = BgeM3Embedder()
    indexer = DatabaseIndexer(embedder=embedder)

    total_chunks = 0
    for file in files:
        text = file.read_text(encoding="utf-8")
        target_id = procurement_id or file.stem
        parent_nodes, child_chunks = splitter.split_document(text, document_id=file.name)
        inserted = indexer.index_document(target_id, parent_nodes, child_chunks)
        total_chunks += inserted
        print(f"[OK] Zaindeksowano {file.name}: {inserted} wektorów.")

    print(f"[OK] Zakończono indeksację. Zapisano łącznie {total_chunks} fragmentów wektorowych.")
    return 0


async def _run_analyze(
    ocds_id: str,
    query: str,
    output: Optional[str],
    min_faithfulness: float,
) -> int:
    from src.evaluation.ragas_guard import RagasGuard
    from src.inference.report_generator import TenderReportGenerator
    from src.retrieval.pipeline import RetrievalPipeline

    print(f"[*] Rozpoczynam zaawansowaną analizę RAG dla postępowania: {ocds_id}")
    pipeline = RetrievalPipeline()
    retrieved_items = pipeline.retrieve(query=query, procurement_id=ocds_id, top_k=5)

    contexts = [item.content for item in retrieved_items]
    merged_context = "\n\n---\n\n".join(contexts) if contexts else "Brak dokumentacji w bazie."

    generator = TenderReportGenerator()
    report = await generator.generate(
        procurement_id=ocds_id,
        title=f"Analiza postępowania {ocds_id}",
        municipality="Zamawiający publiczny",
        context=merged_context,
    )

    # RAGAS Quality Gate
    guard = RagasGuard(min_faithfulness=min_faithfulness)
    eval_result = guard.evaluate_claims_grounding(report.markdown_report, contexts)

    print("\n" + "=" * 60)
    print(f"WYNIK JAKOŚCI RAGAS (Quality Gate):")
    print(f"Faithfulness:      {eval_result.faithfulness:.4f} (Wymóg: >= {min_faithfulness})")
    print(f"Status weryfikacji: {'PASSED [Raport zatwierdzony]' if eval_result.passed else 'REJECTED [Wykryto halucynacje!]'}")
    if not eval_result.passed:
        print(f"Powód odrzucenia:   {eval_result.reason}")
    print("=" * 60 + "\n")

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report.markdown_report, encoding="utf-8")
        print(f"[OK] Zapisano raport w pliku: {out_path.resolve()}")
    else:
        print(report.markdown_report)

    return 0 if eval_result.passed else 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI execution router."""
    parser = create_cli_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    try:
        if args.command == "ingest":
            return asyncio.run(
                _run_ingest(
                    cpv=args.cpv,
                    limit=args.limit,
                    download_attachments=args.download_attachments,
                )
            )
        elif args.command == "parse":
            return _run_parse(input_dir=args.input_dir, output_dir=args.output_dir)
        elif args.command == "index":
            return _run_index(
                procurement_id=args.procurement_id,
                markdown_dir=args.markdown_dir,
            )
        elif args.command == "analyze":
            return asyncio.run(
                _run_analyze(
                    ocds_id=args.ocds_id,
                    query=args.query,
                    output=args.output,
                    min_faithfulness=args.min_faithfulness,
                )
            )
        else:
            parser.print_help()
            return 1
    except Exception as e:
        logger.error("Błąd wykonania CLI: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
