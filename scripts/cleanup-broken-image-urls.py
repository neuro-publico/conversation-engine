#!/usr/bin/env python3
"""Regenerate images for sections whose HTML has unresolved placeholders
or external (untrusted) image URLs left over from edits made BEFORE the
image pipeline existed.

For each eligible section:
  1. Load current HTML from Postgres (website DB via SSM tunnel on :5433).
  2. Treat EVERY <img src> that is not a trusted domain and not a
     placeholder as a "new placeholder" (normalize → placehold.co).
  3. Run the orchestrator + sub-image generator over the normalized HTML.
  4. Write the resulting HTML back to the JSONB `content` column.

Does NOT call the HTTP /edit-section-html endpoint — we go direct to the
service layer so we don't need auth or Pydantic wiring. Safe to run
idempotently: sections already clean are skipped.

Usage:
    cd conversation-engine
    source venv/bin/activate
    python scripts/cleanup-broken-image-urls.py --funnel 82e91b9ee77e4b09b3d719d98692e2a
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.requests.edit_section_html_request import EditSectionHtmlRequest  # noqa: E402
from app.services.section_html_service import SectionHtmlService  # noqa: E402


PG = dict(
    host=os.environ.get("CLEANUP_DB_HOST", "localhost"),
    port=int(os.environ.get("CLEANUP_DB_PORT", "5433")),
    user=os.environ.get("CLEANUP_DB_USER", "fluxi"),
    password=os.environ.get(
        "CLEANUP_DB_PASSWORD", "If4EdNQJLKDWSFpty5coT7YxbpkIy5Cj"
    ),
    dbname=os.environ.get("CLEANUP_DB_NAME", "website"),
)


def has_broken_urls(html: str) -> bool:
    """Sections with unsplash / pexels / unresolved placehold.co need cleanup."""
    if "unsplash.com" in html or "pexels.com" in html or "picsum.photos" in html:
        return True
    if "placehold.co" in html:
        return True
    return False


async def cleanup_section(service: SectionHtmlService, section: dict, owner_id: str):
    sid = section["id"]
    name = section["name"]
    content = section["content"]
    html = content.get("html_content") or ""
    if not html or not has_broken_urls(html):
        return {"id": sid, "name": name, "status": "skipped_clean"}

    # Build a fake "edit request" so we can reuse _process_new_images_in_edit
    # with `previous_html=""` — that makes every current URL look "new",
    # which is exactly what we want (regenerate them all).
    request = EditSectionHtmlRequest(
        current_html="",  # pretend nothing was there → every image is "new"
        instruction="(cleanup)",
        product_name="",
        product_description="",
        owner_id=owner_id,
        language="es",
    )
    try:
        fixed_html = await service._process_new_images_in_edit(
            previous_html="",
            new_html=html,
            request=request,
        )
    except Exception as e:
        return {"id": sid, "name": name, "status": "error", "error": str(e)[:200]}

    # Persist only if something actually changed.
    if fixed_html == html:
        return {"id": sid, "name": name, "status": "no_change"}

    new_content = dict(content)
    new_content["html_content"] = fixed_html
    # Invalidate compiled_css so the frontend either recompiles on next
    # load or falls back to the CDN. Safer than writing a stale CSS.
    if "compiled_css" in new_content:
        new_content["compiled_css"] = None

    with psycopg2.connect(**PG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE website_sections SET content = %s, updated_at = NOW() WHERE id = %s",
                (json.dumps(new_content), sid),
            )
        conn.commit()

    return {
        "id": sid,
        "name": name,
        "status": "cleaned",
        "before_len": len(html),
        "after_len": len(fixed_html),
        "before_unsplash": html.count("unsplash.com"),
        "before_placehold": html.count("placehold.co"),
        "after_unsplash": fixed_html.count("unsplash.com"),
        "after_placehold": fixed_html.count("placehold.co"),
        "after_fluxi": fixed_html.count("fluxi.co"),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--funnel", required=True, help="website_id")
    ap.add_argument("--owner", default="d3414d018d8e437bad0d195c68938b1")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", help="Comma-separated list of section ids to process (overrides --funnel filter)")
    args = ap.parse_args()

    # Load candidates
    with psycopg2.connect(**PG) as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if args.ids:
                ids = [int(x) for x in args.ids.split(",") if x.strip()]
                cur.execute(
                    "SELECT id, name, content FROM website_sections WHERE id = ANY(%s) AND type = 'customCodeSection'",
                    (ids,),
                )
            else:
                cur.execute(
                    "SELECT id, name, content FROM website_sections "
                    "WHERE type = 'customCodeSection' AND website_id = %s "
                    "ORDER BY id",
                    (args.funnel,),
                )
            sections = [dict(r) for r in cur.fetchall()]

    # content may come back as str (old) or dict (JSONB) depending on driver
    for s in sections:
        if isinstance(s["content"], str):
            s["content"] = json.loads(s["content"])

    print(f"Found {len(sections)} sections in funnel {args.funnel}")
    service = SectionHtmlService()

    ok = cleaned = skipped = errors = 0
    results = []
    for s in sections:
        if args.limit and cleaned >= args.limit:
            break
        html = (s["content"] or {}).get("html_content") or ""
        if not has_broken_urls(html):
            results.append({"id": s["id"], "name": s["name"], "status": "skipped_clean"})
            skipped += 1
            continue
        print(f"  · id={s['id']} {s['name'][:50]}  unsplash={html.count('unsplash.com')}  placeholders={html.count('placehold.co')}  → processing...")
        res = await cleanup_section(service, s, args.owner)
        results.append(res)
        st = res.get("status")
        if st == "cleaned":
            cleaned += 1
            print(f"    ✓ {res}")
        elif st == "error":
            errors += 1
            print(f"    ✗ {res['error']}")
        else:
            skipped += 1
            print(f"    · {st}")

    print("\n---- SUMMARY ----")
    print(f"cleaned={cleaned} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    asyncio.run(main())
