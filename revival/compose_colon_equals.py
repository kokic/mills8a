"""Complete Mills 8A's ≔ and ≕ from its colon and equals sorts.

Includes both ssty variants; uses only fontTools, without the source scans:
    uv run --with fonttools python revival/compose_colon_equals.py INPUT.otf OUTPUT.otf
The full math build calls the same function before saving.
"""
import argparse

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


def complete_colon_equals(font):
    """Compose ≔ and ≕ without changing or reflecting either component."""
    cmap = font.getBestCmap()
    colon, equal = cmap[ord(":")], cmap[ord("=")]
    gsub = font["GSUB"].table
    feature = next(f.Feature for f in gsub.FeatureList.FeatureRecord
                   if f.FeatureTag == "ssty")
    tables = [st.alternates for i in feature.LookupListIndex
              for st in gsub.LookupList.Lookup[i].SubTable]
    colon_alts = next(t[colon] for t in tables if colon in t)
    equal_alts = next(t[equal] for t in tables if equal in t)
    assert len(colon_alts) == len(equal_alts) == 2, "Expected two Mills 8A script sorts"

    glyphs = font.getGlyphSet()
    order = list(font.getGlyphOrder())
    top = font["CFF "].cff.topDictIndex[0]
    charstrings = top.CharStrings
    for c, e, suffix in zip([colon] + colon_alts, [equal] + equal_alts,
                            ("", ".st", ".sts")):
        cb, eb = BoundsPen(glyphs), BoundsPen(glyphs)
        glyphs[c].draw(cb)
        glyphs[e].draw(eb)
        dy = round((eb.bounds[1] + eb.bounds[3]
                    - cb.bounds[1] - cb.bounds[3]) / 2)
        cw, ew = font["hmtx"][c][0], font["hmtx"][e][0]
        width = cw + ew
        # The components' existing side bearings supply the internal gap:
        # about 60 units in text, 50 in scripts. Keep the outside bearings
        # too, and move only the colon vertically to match the equals sort.
        for cp, parts in ((0x2254, ((c, 0, dy), (e, cw, 0))),
                          (0x2255, ((e, 0, 0), (c, ew, dy)))):
            name = cmap[cp] + suffix
            pen = T2CharStringPen(width, glyphs)
            for src, dx, y in parts:
                glyphs[src].draw(TransformPen(pen, (1, 0, 0, 1, dx, y)))
            cs = pen.getCharString(top.Private, top.GlobalSubrs)
            if name not in order:
                order.append(name)
                if charstrings.charStringsAreIndexed:
                    charstrings.charStrings[name] = len(charstrings.charStringsIndex)
                    charstrings.charStringsIndex.append(cs)
                else:
                    charstrings[name] = cs
            else:
                charstrings[name] = cs
            bounds = BoundsPen(None)
            cs.draw(bounds)
            font["hmtx"][name] = (width, round(bounds.bounds[0]))

    top.charset = order
    font.setGlyphOrder(order)
    font["maxp"].numGlyphs = len(order)
    for cp in (0x2254, 0x2255):
        name = cmap[cp]
        tables[0][name] = [name + ".st", name + ".sts"]
    # These upright relations have no explicit MATH corrections or anchors;
    # the implicit top-accent position remains half the new advance.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    font = TTFont(args.input, recalcTimestamp=False)
    complete_colon_equals(font)
    font.save(args.output)
    print(f"wrote {args.output}: composed ≔, ≕ and their two script sorts")


if __name__ == "__main__":
    main()
