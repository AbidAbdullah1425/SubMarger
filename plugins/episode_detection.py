import re

def extract_episode(filename: str) -> int | None:
    """
    Extract episode number from filename.
    Avoids matching resolutions and years.
    """

    patterns = [
        r"\bE(?:P)?\s*0*(\d+)\b",          # E180, EP180
        r"\bEpisode\s*0*(\d+)\b",          # Episode 180
        r"\bS\d+\s*[-._ ]\s*0*(\d+)\b",    # S5-180, S05 180
    ]

    blacklist = {
        240, 360, 480, 540, 720, 1080, 1440, 2160,
        2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025
    }

    for p in patterns:
        m = re.search(p, filename, re.I)
        if m:
            ep = int(m.group(1))
            if ep not in blacklist:
                return ep

    return None