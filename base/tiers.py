"""Truth tier schema: 0=necessary, 1=empirical, 2=contingent, 3=inference, 4=contested, 5=opinion, 6=speculation."""
from enum import IntEnum
from typing import Optional


class Tier(IntEnum):
    """Epistemic tier for statements. Lower = more certain."""

    NECESSARY = 0   # e.g. 2 + 2 = 4, logic, math
    EMPIRICAL = 1   # e.g. Earth orbits Sun, well-established science
    CONTINGENT = 2  # e.g. Paris is capital of France
    INFERENCE = 3   # well-supported inference
    CONTESTED = 4   # plausible but disputed
    OPINION = 5     # preference, judgment
    SPECULATION = 6  # hypothetical, "what if"


TIER_NAMES: dict[int, str] = {
    0: "necessary",
    1: "empirical",
    2: "contingent",
    3: "inference",
    4: "contested",
    5: "opinion",
    6: "speculation",
}


def tier_from_source(source: str) -> int:
    """Default tier for a corpus source. Used when no explicit tier map is given."""
    _default: dict[str, int] = {
        "text_files": Tier.INFERENCE,
        "email": Tier.INFERENCE,
        "social": Tier.CONTESTED,
        "dictionary": Tier.CONTINGENT,
        "bible_commentary": Tier.CONTINGENT,
        "inferred_bookmarks": Tier.OPINION,
        "inferred_readings": Tier.OPINION,
        "fetched": Tier.CONTESTED,
    }
    return _default.get(source, Tier.INFERENCE)
