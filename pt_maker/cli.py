"""Command-line entry for PT_maker.

Subcommands:
  extract-theme   Build theme.json from a reference PPTX/PDF/image
  ingest          Dump PDF ingest summary to JSON (debug)
  outline         Produce outline.json from a PDF
  draft           Produce slides.json from outline + theme
  review          Run reviewer loop + QA on an existing slides.json
  render          Render slides.json + theme.json → .pptx
  make-deck       All of the above in one shot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ingest.figures import extract_figures
from .ingest.pdf_reader import ingest_pdf
from .ingest.tables import extract_tables
from .outline.generator import generate_outline
from .outline.schema import load_outline, save_outline
from .qa.checks import run_qa
from .render.engine import render_deck
from .slides.drafter import draft_slides
from .slides.reviewer import review_loop
from .slides.schema import load_slides, save_slides
from .theme.from_image import extract_theme_from_image
from .theme.from_pdf import extract_theme_from_pdf
from .theme.from_pptx import extract_theme_from_pptx
from .theme.schema import load_theme, save_theme

DEFAULT_WORKDIR = Path(".ptmaker")


def _theme_path(name: str) -> Path:
    return DEFAULT_WORKDIR / "themes" / f"{name}.json"


def cmd_extract_theme(args: argparse.Namespace) -> int:
    src = Path(args.source)
    if not src.exists():
        print(f"source not found: {src}", file=sys.stderr)
        return 2

    ext = src.suffix.lower()
    name = args.name or src.stem
    if ext == ".pptx":
        theme = extract_theme_from_pptx(src, name=name)
    elif ext == ".pdf":
        theme = extract_theme_from_pdf(src, name=name, use_vision=not args.no_vision)
    elif ext in (".png", ".jpg", ".jpeg", ".webp"):
        theme = extract_theme_from_image(src, name=name, use_vision=not args.no_vision)
    else:
        print(f"unsupported theme source: {ext}", file=sys.stderr)
        return 2

    out = Path(args.out) if args.out else _theme_path(name)
    save_theme(theme, out)
    print(json.dumps({"theme_path": str(out), "name": name}, ensure_ascii=False))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    ing = ingest_pdf(args.pdf, max_pages=args.max_pages)
    tables = extract_tables(args.pdf, max_pages=args.max_pages) if args.tables else []
    figures = []
    if args.figures:
        fig_dir = DEFAULT_WORKDIR / "figures" / Path(args.pdf).stem
        figures = extract_figures(args.pdf, fig_dir, max_pages=args.max_pages)
    print(json.dumps({
        "title": ing.title, "pages": ing.pages, "n_blocks": len(ing.blocks),
        "n_tables": len(tables), "n_figures": len(figures),
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_outline(args: argparse.Namespace) -> int:
    ing = ingest_pdf(args.pdf)
    tables = extract_tables(args.pdf)
    fig_dir = DEFAULT_WORKDIR / "figures" / Path(args.pdf).stem
    figures = extract_figures(args.pdf, fig_dir) if args.figures else []
    outline = generate_outline(
        ing, tables, figures,
        purpose=args.purpose, language=args.language,
        audience=args.audience or "",
        duration_min=args.duration, target_slides=args.slides,
    )
    out = Path(args.out) if args.out else (DEFAULT_WORKDIR / "outlines" / f"{Path(args.pdf).stem}.json")
    save_outline(outline, out)
    print(json.dumps({"outline_path": str(out), "n_slides": len(outline["slides"])}, ensure_ascii=False))
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    outline = load_outline(args.outline)
    theme = load_theme(args.theme if "/" in args.theme or args.theme.endswith(".json")
                       else str(_theme_path(args.theme)))
    spec = draft_slides(outline, theme, use_llm=not args.no_llm)
    spec["theme_ref"] = {"name": theme["name"]}
    out = Path(args.out) if args.out else (DEFAULT_WORKDIR / "slides" / f"{Path(args.outline).stem}.json")
    save_slides(spec, out)
    print(json.dumps({"slides_path": str(out), "n_slides": len(spec["slides"])}, ensure_ascii=False))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    spec = load_slides(args.slides)
    theme_name = spec.get("theme_ref", {}).get("name", "default")
    theme = load_theme(args.theme) if args.theme else load_theme(str(_theme_path(theme_name)))
    if not args.qa_only:
        spec = review_loop(spec, max_iterations=args.iterations)
        save_slides(spec, args.slides)
    source_text = Path(args.source_text).read_text(encoding="utf-8") if args.source_text else None
    report = run_qa(spec, theme, source_text=source_text)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


def cmd_render(args: argparse.Namespace) -> int:
    spec = load_slides(args.slides)
    theme_name = spec.get("theme_ref", {}).get("name", "default")
    theme = load_theme(args.theme) if args.theme else load_theme(str(_theme_path(theme_name)))
    out = Path(args.out) if args.out else Path(f"{Path(args.slides).stem}.pptx")
    render_deck(spec, theme, out)
    print(json.dumps({"pptx": str(out)}, ensure_ascii=False))
    return 0


def cmd_make_deck(args: argparse.Namespace) -> int:
    # 1. Theme (from --theme or fresh extraction of --ref)
    if args.theme:
        theme_path = args.theme if args.theme.endswith(".json") else str(_theme_path(args.theme))
        theme = load_theme(theme_path)
    elif args.ref:
        ref = Path(args.ref)
        ext = ref.suffix.lower()
        name = ref.stem
        if ext == ".pptx":
            theme = extract_theme_from_pptx(ref, name=name)
        elif ext == ".pdf":
            theme = extract_theme_from_pdf(ref, name=name, use_vision=not args.no_vision)
        else:
            theme = extract_theme_from_image(ref, name=name, use_vision=not args.no_vision)
        save_theme(theme, _theme_path(name))
    else:
        from .theme.schema import default_theme
        theme = default_theme("default")
        save_theme(theme, _theme_path("default"))

    # 2. Ingest
    ing = ingest_pdf(args.pdf)
    tables = extract_tables(args.pdf)
    fig_dir = DEFAULT_WORKDIR / "figures" / Path(args.pdf).stem
    figures = extract_figures(args.pdf, fig_dir)

    # 3. Outline
    outline = generate_outline(
        ing, tables, figures,
        purpose=args.purpose, language=args.language,
        audience=args.audience or "", duration_min=args.duration,
        target_slides=args.slides,
    )
    save_outline(outline, DEFAULT_WORKDIR / "outlines" / f"{Path(args.pdf).stem}.json")

    # 4. Draft
    spec = draft_slides(outline, theme, use_llm=not args.no_llm)
    spec["theme_ref"] = {"name": theme["name"]}

    # 5. Review
    if not args.no_review:
        spec = review_loop(spec, max_iterations=args.iterations)
    slides_path = DEFAULT_WORKDIR / "slides" / f"{Path(args.pdf).stem}.json"
    save_slides(spec, slides_path)

    # 6. QA
    report = run_qa(spec, theme, source_text=ing.full_text)

    # 7. Render
    out = Path(args.out) if args.out else Path(f"{Path(args.pdf).stem}.pptx")
    render_deck(spec, theme, out)

    print(json.dumps({
        "pptx": str(out),
        "slides_path": str(slides_path),
        "theme_name": theme["name"],
        "qa": report.to_dict(),
    }, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pt-maker")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("extract-theme", help="Build theme.json from a reference design")
    t.add_argument("source")
    t.add_argument("--name")
    t.add_argument("--out")
    t.add_argument("--no-vision", action="store_true")
    t.set_defaults(func=cmd_extract_theme)

    i = sub.add_parser("ingest", help="Inspect a PDF (debug)")
    i.add_argument("pdf")
    i.add_argument("--tables", action="store_true")
    i.add_argument("--figures", action="store_true")
    i.add_argument("--max-pages", type=int)
    i.set_defaults(func=cmd_ingest)

    o = sub.add_parser("outline", help="PDF → outline.json")
    o.add_argument("pdf")
    o.add_argument("--purpose", choices=["academic", "ir", "business"], default="business")
    o.add_argument("--language", choices=["ko", "en"], default="ko")
    o.add_argument("--audience")
    o.add_argument("--duration", type=int, default=15)
    o.add_argument("--slides", type=int, default=12)
    o.add_argument("--figures", action="store_true", default=True)
    o.add_argument("--out")
    o.set_defaults(func=cmd_outline)

    d = sub.add_parser("draft", help="outline + theme → slides.json")
    d.add_argument("--outline", required=True)
    d.add_argument("--theme", required=True,
                    help="Theme name (lookup in .ptmaker/themes/) or explicit .json path")
    d.add_argument("--no-llm", action="store_true")
    d.add_argument("--out")
    d.set_defaults(func=cmd_draft)

    r = sub.add_parser("review", help="Review + QA an existing slides.json")
    r.add_argument("slides")
    r.add_argument("--theme")
    r.add_argument("--iterations", type=int, default=2)
    r.add_argument("--qa-only", action="store_true")
    r.add_argument("--source-text", help="Path to source text for numeric checks")
    r.set_defaults(func=cmd_review)

    rn = sub.add_parser("render", help="slides.json + theme → .pptx")
    rn.add_argument("slides")
    rn.add_argument("--theme")
    rn.add_argument("--out")
    rn.set_defaults(func=cmd_render)

    m = sub.add_parser("make-deck", help="Full pipeline PDF → .pptx")
    m.add_argument("pdf")
    m.add_argument("--ref", help="Reference design (PPTX/PDF/image)")
    m.add_argument("--theme", help="Pre-extracted theme name or .json path")
    m.add_argument("--purpose", choices=["academic", "ir", "business"], default="business")
    m.add_argument("--language", choices=["ko", "en"], default="ko")
    m.add_argument("--audience")
    m.add_argument("--duration", type=int, default=15)
    m.add_argument("--slides", type=int, default=12)
    m.add_argument("--iterations", type=int, default=2)
    m.add_argument("--no-llm", action="store_true")
    m.add_argument("--no-review", action="store_true")
    m.add_argument("--no-vision", action="store_true")
    m.add_argument("--out")
    m.set_defaults(func=cmd_make_deck)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
