#!/usr/bin/env python3
"""Shrink a squib PDF exported from Word on macOS.

Word's "Save as PDF" embeds a separate font subset for nearly every text run,
so a 10-page squib can come out at 20 MB. This slims each embedded font:
  - CFF fonts (the Devanagari): drop unused subroutines. Lossless.
  - TrueType fonts (Times New Roman): drop hinting programs. Invisible in
    anti-aliased viewers; pass --keep-hinting for an exact match (larger file).

Setup (once):
    python3 -m venv .venv && .venv/bin/pip install pikepdf fonttools

Usage:
    .venv/bin/python scripts/slim-pdf.py "From Word.pdf" public/squibs/name.pdf
"""
import argparse
import io
import types

import pikepdf
from fontTools.cffLib import CFFFontSet
from fontTools.ttLib import TTFont


def slim_cff(data):
    cff = CFFFontSet()
    cff.decompile(io.BytesIO(data), None)
    cff.desubroutinize()
    out = io.BytesIO()
    cff.compile(out, types.SimpleNamespace(recalcBBoxes=False))
    return out.getvalue()


def slim_ttf(data):
    f = TTFont(io.BytesIO(data), recalcBBoxes=False, recalcTimestamp=False)
    for t in ("cvt ", "fpgm", "prep"):
        if t in f:
            del f[t]
    f["glyf"].removeHinting()
    out = io.BytesIO()
    f.save(out, reorderTables=False)
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--keep-hinting", action="store_true",
                    help="leave TrueType fonts untouched (lossless, larger)")
    args = ap.parse_args()

    kinds = [("/FontFile3", "cff", slim_cff)]
    if not args.keep_hinting:
        kinds.append(("/FontFile2", "ttf", slim_ttf))

    pdf = pikepdf.open(args.src)
    seen = set()
    for obj in pdf.objects:
        if not isinstance(obj, pikepdf.Dictionary) or obj.get("/Type") != "/FontDescriptor":
            continue
        for key, kind, fn in kinds:
            if key not in obj:
                continue
            st = obj[key]
            if st.objgen in seen:
                continue
            seen.add(st.objgen)
            if kind == "cff" and st.get("/Subtype") not in ("/Type1C", "/CIDFontType0C"):
                continue
            old = st.read_bytes()
            try:
                new = fn(old)
            except Exception as e:
                print(f"skipped {obj.get('/FontName')}: {e!r}")
                continue
            if len(new) < len(old):
                st.write(new)
                if kind == "ttf":
                    st["/Length1"] = len(new)

    pdf.save(args.dst, compress_streams=True, recompress_flate=True,
             object_stream_mode=pikepdf.ObjectStreamMode.generate)


if __name__ == "__main__":
    main()
