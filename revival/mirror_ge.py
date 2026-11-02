"""Complete Mills 8A's ≥ from its ≤, including both ssty variants.

Uses only fontTools, so the committed OTF can be patched without the scans:
    uv run --with fonttools python revival/mirror_ge.py INPUT.otf OUTPUT.otf
The full math build calls the same function before saving.
"""
import argparse
from copy import deepcopy

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


def complete_ge(font):
    """Replace the Latin Modern ≥ with horizontally mirrored Mills 8A sorts."""
    cmap = font.getBestCmap()
    source, target = cmap[0x2264], cmap[0x2265]
    gsub = font["GSUB"].table
    feature = next(f.Feature for f in gsub.FeatureList.FeatureRecord
                   if f.FeatureTag == "ssty")
    alternates = next(st.alternates for i in feature.LookupListIndex
                      for st in gsub.LookupList.Lookup[i].SubTable
                      if source in st.alternates)
    sources = [source] + alternates[source]
    targets = [target, target + ".st", target + ".sts"]
    assert len(sources) == len(targets), "Expected two Mills 8A script sorts"

    glyphs = font.getGlyphSet()
    order = list(font.getGlyphOrder())
    top = font["CFF "].cff.topDictIndex[0]
    charstrings = top.CharStrings
    for src, dst in zip(sources, targets):
        width = font["hmtx"][src][0]
        pen = T2CharStringPen(width, glyphs)
        # Reflect about the advance's midpoint; reverse contours to retain
        # their original winding after reflection (including any counters).
        glyphs[src].draw(TransformPen(ReverseContourPen(pen),
                                     (-1, 0, 0, 1, width, 0)))
        cs = pen.getCharString(top.Private, top.GlobalSubrs)
        if dst not in order:
            order.append(dst)
            if charstrings.charStringsAreIndexed:
                charstrings.charStrings[dst] = len(charstrings.charStringsIndex)
                charstrings.charStringsIndex.append(cs)
            else:
                charstrings[dst] = cs
        else:
            charstrings[dst] = cs
        bounds = BoundsPen(None)
        cs.draw(bounds)
        font["hmtx"][dst] = (width, round(bounds.bounds[0]))

    top.charset = order
    font.setGlyphOrder(order)
    font["maxp"].numGlyphs = len(order)
    alternates[target] = targets[1:]

    # Mirror the explicit accent anchors too; implicit anchors already use
    # half the advance. These upright relations have no italic corrections
    # or math kerns in Mills 8A.
    accents = font["MATH"].table.MathGlyphInfo.MathTopAccentAttachment
    records = dict(zip(accents.TopAccentCoverage.glyphs,
                       accents.TopAccentAttachment))
    for src, dst in zip(sources, targets):
        if src in records:
            rec = deepcopy(records[src])
            assert rec.DeviceTable is None, "Mills 8A anchors have no device corrections"
            rec.Value = font["hmtx"][src][0] - rec.Value
            records[dst] = rec
    names = sorted(records, key=font.getGlyphID)
    accents.TopAccentCoverage.glyphs = names
    accents.TopAccentAttachment = [records[n] for n in names]
    accents.TopAccentAttachmentCount = len(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    font = TTFont(args.input, recalcTimestamp=False)
    complete_ge(font)
    font.save(args.output)
    print(f"wrote {args.output}: mirrored ≥ and its two script sorts")


if __name__ == "__main__":
    main()
