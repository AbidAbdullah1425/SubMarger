import re
import os

def clean_ass_subtitle(sub_path: str) -> str:
    POS_TAG = r"{\pos(193,265)}"
    out_path = os.path.splitext(sub_path)[0] + ".cleaned.ass"

    SCRIPT_INFO = """[Script Info]
; Script generated automatically
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
ScaledBorderAndShadow: yes
"""

    STYLES = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Oath-Bold,20,&HFFFFFF,&HFFFFFF,&H0,&H0,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,0
"""

    EVENTS_HEADER = """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    try:
        with open(sub_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception as e:
        raise RuntimeError("Subtitle cleanup failed: cannot read input file") from e

    dialogues = re.findall(r"^Dialogue:.*$", raw, flags=re.MULTILINE)
    if not dialogues:
        raise RuntimeError("Subtitle cleanup failed: no dialogue lines found")

    dialogues = dialogues[1:]  # remove intro
    cleaned = []

    for line in dialogues:
        low = line.lower()

        if re.search(
            r"(subtitled\s*by|thanks|thank\s*you|www\.|http|free\s*at|fansub|credits?)",
            low
        ):
            continue

        line = re.sub(
            r"^(Dialogue:\d+,[^,]+,[^,]+),[^,]+,",
            r"\1,Default,",
            line
        )

        line = re.sub(r"AnimeXin", "~ [HeavenlySubs]", line, flags=re.I)

        if POS_TAG not in line:
            line = re.sub(r"(,0,,)", r"\1" + POS_TAG, line, count=1)

        cleaned.append(line)

    if not cleaned:
        raise RuntimeError("Subtitle cleanup failed: all lines removed as credits")

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(SCRIPT_INFO + "\n")
            f.write(STYLES + "\n")
            f.write(EVENTS_HEADER + "\n")
            f.write("\n".join(cleaned))
    except Exception as e:
        raise RuntimeError("Subtitle cleanup failed: cannot write output file") from e

    return out_path