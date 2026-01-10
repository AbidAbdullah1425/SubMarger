import re
import os

def clean_ass_subtitle(sub_path: str) -> str:
    """
    Cleans an ASS subtitle file and returns path to cleaned file.
    - Removes intro line
    - Removes credit lines
    - Replaces AnimeXin -> ~ [HeavenlySubs]
    - Forces Default style
    - Injects {\pos()} safely
    """

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
    except Exception:
        return sub_path  # fail-safe: return original

    dialogues = re.findall(r"^Dialogue:.*$", raw, flags=re.MULTILINE)

    if not dialogues:
        return sub_path

    # drop first line (intro)
    dialogues = dialogues[1:]

    cleaned = []

    for line in dialogues:
        low = line.lower()

        # aggressive credit removal
        if re.search(
            r"(subtitled\s*by|thanks|thank\s*you|www\.|http|free\s*at|fansub|credits?)",
            low
        ):
            continue

        # normalize style
        line = re.sub(
            r"^(Dialogue:\d+,[^,]+,[^,]+),[^,]+,",
            r"\1,Default,",
            line
        )

        # replace group name
        line = re.sub(r"AnimeXin", "~ [HeavenlySubs]", line, flags=re.I)

        # inject pos tag once
        if POS_TAG not in line:
            line = re.sub(r"(,0,,)", r"\1" + POS_TAG, line, count=1)

        cleaned.append(line)

    if not cleaned:
        return sub_path

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(SCRIPT_INFO + "\n")
            f.write(STYLES + "\n")
            f.write(EVENTS_HEADER + "\n")
            f.write("\n".join(cleaned))
    except Exception:
        return sub_path

    return out_path