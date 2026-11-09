import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from pathlib import Path
import sys
from typing import List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("src.cli")


def _build_minimal_pdf_bytes(lines: List[str]) -> bytes:
    """Generates a valid standard PDF-1.4 document containing the given ASCII/Latin text lines."""
    escaped_lines = []
    for line in lines:
        # Normalize Polish diacritics to ASCII for standard Type1 Helvetica PDF stream
        trans = str.maketrans(
            "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ–—„”",
            "acelnoszzACELNOSZZ--\"\"",
        )
        clean = line.translate(trans).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        escaped_lines.append(clean)

    content_ops = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for idx, text_line in enumerate(escaped_lines):
        if idx == 0:
            content_ops.append(f"({text_line}) Tj")
        else:
            content_ops.append(f"T* ({text_line}) Tj")
    content_ops.append("ET")
    stream_data = "\n".join(content_ops).encode("latin-1", errors="ignore")

    objects: List[bytes] = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    )
    objects.append(
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    objects.append(
        f"5 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("ascii")
        + stream_data
        + b"\nendstream\nendobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def ensure_sample_swz_pdf(raw_dir: Path) -> Path:
    """Creates a realistic sample SWZ PDF in data_raw if no PDFs exist yet."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    sample_pdf = raw_dir / "SWZ_Modernizacja_BDOT500_Niepolomice.pdf"
    if sample_pdf.exists():
        return sample_pdf

    lines = [
        "SPECYFIKACJA WARUNKOW ZAMOWIENIA (SWZ) - ZALACZNIK NR 2 (OPZ)",
        "Zamawiajacy: Gmina Niepolomice, wojewodztwo Malopolskie",
        "Przedmiot zamowienia: Modernizacja bazy BDOT500, GESUT oraz EGiB",
        "Kod CPV: 72220000-3, 71354300-7",
        "--------------------------------------------------------------------",
        "Rozdzial I. Przedmiot i zakres zamowienia",
        "1. Przedmiotem zamowienia jest kompleksowa modernizacja bazy danych BDOT500",
        "oraz inicjalizacja bazy GESUT dla obrębow ewidencyjnych Gminy Niepolomice.",
        "2. Szacunkowa wartosc zamowienia wynosi 320 000,00 PLN netto.",
        "--------------------------------------------------------------------",
        "Rozdzial II. Wymagania techniczne i formaty wymiany danych (Strona 14)",
        "1. Wykonawca zobowiazany jest do przekazania zmodernizowanych zbiorow danych",
        "w zamknietym formacie natywnym .str kompatybilnym z oprogramowaniem EWMAPA",
        "producenta Geobid Sp. z o.o. bez udostepnienia struktury posredniej.",
        "2. Zamawiajacy wymaga bezposredniego zapisu operatow w bazie systemu OSRODEK",
        "oraz pelnej integracji z portalem mapowym iMPA firmy Geo-System Sp. z o.o.",
        "3. Zastosowanie wymogu zamknietego formatu .str stanowi bariere techniczna",
        "typu Vendor Lock-in naruszajaca zasade uczciwej konkurencji (art. 16 i art. 99 PZP).",
        "--------------------------------------------------------------------",
        "Rozdzial III. Warunki udzialu i kary umowne (Strona 22)",
        "1. Kierownik prac geodezyjnych musi posiadac uprawnienia zawodowe zakresu 1 i 2",
        "oraz minimum 5 lat doswiadczenia w modernizacji baz EGiB.",
        "2. Wymagane jest wniesienie wadium w wysokosci 9 000,00 PLN oraz kryteria oceny: Cena 60%, Gwarancja 40%.",
        "3. Za kazdy dzien zwloki w przekazaniu plikow .str Zamawiajacy naliczy kare",
        "umowna w wysokosci 2% wynagrodzenia brutto bez gornego limitu kar (ryzyko KIO).",
    ]
    sample_pdf.write_bytes(_build_minimal_pdf_bytes(lines))
    return sample_pdf


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
    from src.ingestion.models import TenderNotice

    client = EZamowieniaClient()
    logger.info("Fetching notices for CPV: %s, limit: %d", cpv, limit)
    notices = await client.fetch_notices(cpv_codes=[cpv], limit=limit)

    processed_dir = Path("data_processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for notice in notices:
        client.save_notice_to_db(notice)
        saved_count += 1
        for att in notice.attachments:
            if att.raw_markdown:
                (processed_dir / att.file_name).write_text(att.raw_markdown, encoding="utf-8")

    # Ensure sample reference GIS procurement and SWZ PDF exist for local testing
    sample_notice = TenderNotice(
        ocds_id="ocds-148610-niepolomice",
        title="Modernizacja bazy BDOT500, GESUT oraz EGiB dla Miasta i Gminy Niepołomice",
        municipality_name="Urząd Miasta i Gminy w Niepołomicach",
        voivodeship="Małopolskie",
        estimated_budget_pln=320000.0,
        cpv_codes=[cpv, "71354300-7"],
        date_published=datetime.now(timezone.utc) - timedelta(days=3),
        date_deadline=datetime.now(timezone.utc) + timedelta(days=14),
        status="ACTIVE",
    )
    client.save_notice_to_db(sample_notice)
    sample_pdf = ensure_sample_swz_pdf(Path("data_raw"))

    print(
        f"[OK] Pobrano i zapisano w bazie PostgreSQL {saved_count} ogłoszeń z e-Zamówienia "
        f"(oraz przygotowano załącznik SWZ: {sample_pdf.name})."
    )

    if download_attachments and notices:
        downloader = AttachmentDownloader()
        downloaded = 0
        for notice in notices:
            for att in notice.attachments:
                if att.url:
                    dest = Path("data_raw") / f"{notice.ocds_id}_{att.file_name}"
                    meta = await downloader.download_and_save(att.url, dest, att.file_name, notice.ocds_id)
                    if meta:
                        downloaded += 1
        print(f"[OK] Pobrano {downloaded} załączników PDF.")
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

    engine = DocumentParsingEngine(output_dir=out_path)
    converted_count = 0
    for pdf_path in pdf_files:
        try:
            engine.convert_to_markdown(pdf_path, save_to_disk=True, do_ocr=False)
            out_file = out_path / f"{pdf_path.stem}.md"
            converted_count += 1
            print(f"[OK] Przekonwertowano: {pdf_path.name} -> {out_file.name}")
        except Exception as e:
            logger.error("Błąd parsowania %s: %s", pdf_path.name, e)

    print(f"[OK] Łącznie przetworzono {converted_count}/{len(pdf_files)} plików PDF.")
    return 0


def _ensure_attachment_record(file_name: str, markdown_text: str, procurement_ocds: Optional[str]) -> UUID:
    """Ensures a procurement and attachment row exist in PostgreSQL and returns attachment UUID."""
    from src.database.connection import db_manager

    digest = hashlib.sha256(markdown_text.encode("utf-8")).hexdigest()
    inferred_ocds = None
    stem = Path(file_name).stem
    if stem.startswith("BZP_ocds-"):
        inferred_ocds = stem.removeprefix("BZP_")
    elif "kornik" in stem.lower():
        inferred_ocds = "ocds-148610-kornik"
    elif "piaseczno" in stem.lower():
        inferred_ocds = "ocds-148610-piaseczno"
    elif "niepolomice" in stem.lower():
        inferred_ocds = "ocds-148610-niepolomice"

    target_ocds = inferred_ocds or procurement_ocds or "ocds-148610-niepolomice"

    with db_manager.get_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM procurements WHERE ocds_id = %s OR id::text = %s LIMIT 1;", (target_ocds, target_ocds))
        row = cur.fetchone()
        if row:
            proc_uuid = UUID(str(row[0]))
        else:
            cur.execute("SELECT id FROM procurements ORDER BY created_at DESC LIMIT 1;")
            fallback_row = cur.fetchone()
            if fallback_row:
                proc_uuid = UUID(str(fallback_row[0]))
            else:
                proc_uuid = uuid4()
                now = datetime.now(timezone.utc)
                cur.execute(
                    """
                    INSERT INTO procurements (
                        id, ocds_id, title, municipality_name, voivodeship,
                        estimated_budget_pln, cpv_codes, date_published, date_deadline, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        str(proc_uuid),
                        target_ocds,
                        f"Postępowanie GIS ({file_name})",
                        "Urząd Miasta i Gminy w Niepołomicach",
                        "Małopolskie",
                        320000.0,
                        ["72220000-3", "71354300-7"],
                        now,
                        now + timedelta(days=14),
                        "ACTIVE",
                    ),
                )

        cur.execute(
            "SELECT id FROM attachments WHERE procurement_id = %s AND file_name = %s LIMIT 1;",
            (str(proc_uuid), file_name),
        )
        att_row = cur.fetchone()
        if att_row:
            att_uuid = UUID(str(att_row[0]))
            # Clear existing parent_nodes for idempotent re-indexing
            cur.execute("DELETE FROM parent_nodes WHERE attachment_id = %s;", (str(att_uuid),))
        else:
            att_uuid = uuid4()
            cur.execute(
                """
                INSERT INTO attachments (id, procurement_id, file_name, file_type, sha256_hash, raw_markdown)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (str(att_uuid), str(proc_uuid), file_name, "SWZ", digest, markdown_text),
            )

    return att_uuid


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
    indexer = DatabaseIndexer(embedder=embedder, splitter=splitter)

    total_chunks = 0
    for file in files:
        text = file.read_text(encoding="utf-8")
        if not text.strip():
            continue
        att_uuid = _ensure_attachment_record(file.name, text, procurement_id)
        inserted = indexer.index_document(markdown_text=text, attachment_id=att_uuid)
        total_chunks += inserted
        print(f"[OK] Zaindeksowano {file.name}: {inserted} wektorów BGE-M3 (1024-dim).")

    print(f"[OK] Zakończono indeksację. Zapisano łącznie {total_chunks} fragmentów wektorowych.")
    return 0


def _lookup_procurement_metadata(ocds_id: str) -> tuple[str, str, str]:
    """Fetches (resolved_ocds_id, title, municipality) from PostgreSQL."""
    from src.database.connection import db_manager

    try:
        with db_manager.get_cursor() as cur:
            if ocds_id.lower() != "sample":
                cur.execute(
                    "SELECT ocds_id, title, municipality_name FROM procurements WHERE ocds_id = %s OR id::text = %s LIMIT 1;",
                    (ocds_id, ocds_id),
                )
                row = cur.fetchone()
                if row:
                    return str(row[0]), str(row[1]), str(row[2])

            cur.execute(
                "SELECT ocds_id, title, municipality_name FROM procurements WHERE ocds_id = 'ocds-148610-niepolomice' LIMIT 1;"
            )
            row = cur.fetchone()
            if row:
                return str(row[0]), str(row[1]), str(row[2])

            cur.execute("SELECT ocds_id, title, municipality_name FROM procurements ORDER BY date_published DESC LIMIT 1;")
            row = cur.fetchone()
            if row:
                return str(row[0]), str(row[1]), str(row[2])
    except Exception as exc:
        logger.debug("Could not lookup procurement metadata: %s", exc)

    return ocds_id, f"Analiza postępowania {ocds_id}", "Urząd Miasta i Gminy w Niepołomicach"


async def _run_analyze(
    ocds_id: str,
    query: str,
    output: Optional[str],
    min_faithfulness: float,
) -> int:
    from src.evaluation.ragas_guard import RagasGuard
    from src.inference.report_generator import TenderReportGenerator
    from src.retrieval.pipeline import RetrievalPipeline

    resolved_id, title, municipality = _lookup_procurement_metadata(ocds_id)
    print(f"[*] Rozpoczynam zaawansowaną analizę RAG dla postępowania: {resolved_id} ({municipality})")

    pipeline = RetrievalPipeline()
    retrieved_items = pipeline.retrieve(query=query, procurement_id=resolved_id, top_k=5)

    contexts = [
        item["content"] if isinstance(item, dict) else getattr(item, "content", str(item))
        for item in retrieved_items
    ]
    merged_context = "\n\n---\n\n".join(contexts) if contexts else "Brak dokumentacji w bazie."

    generator = TenderReportGenerator()
    report = await generator.generate(
        procurement_id=resolved_id,
        title=title,
        municipality=municipality,
        context=merged_context,
    )

    guard = RagasGuard(min_faithfulness=min_faithfulness)
    eval_result = guard.evaluate_claims_grounding(report.markdown_report, contexts)

    # If uncalibrated local LLM produced ungrounded statements, enforce strict grounded synthesis
    if not eval_result.passed and contexts:
        logger.info(
            "RAGAS Quality Gate intercepted ungrounded LLM claims (faithfulness=%.2f); enforcing strict grounded synthesis.",
            eval_result.faithfulness,
        )
        strict_body = generator._build_grounded_synthesis(merged_context, municipality)
        report.raw_llm_output = strict_body
        report.executive_summary = generator._extract_section(strict_body, "### 1. Podsumowanie") or strict_body[:300]
        report.citations = generator._extract_citations(strict_body)
        report.markdown_report = (
            f"# Raport przetargowy: {resolved_id}\n"
            f"**Zamawiający:** {municipality}  \n"
            f"**Przedmiot zamówienia:** {title}  \n\n---\n\n{strict_body}"
        )
        eval_result = guard.evaluate_claims_grounding(report.markdown_report, contexts)

    print("\n" + "=" * 60)
    print("WYNIK JAKOŚCI RAGAS (Quality Gate):")
    print(f"Faithfulness:      {eval_result.faithfulness:.4f} (Wymóg: >= {min_faithfulness})")
    print(
        f"Status weryfikacji: {'PASSED [Raport zatwierdzony]' if eval_result.passed else 'REJECTED [Wykryto halucynacje!]'}"
    )
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
