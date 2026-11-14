"""
src/aggregator/topic_rotator.py - Autonomous Topic Rotation Engine for Arachudar.
Orchestrates systematic, cyclical publishing across all news desks every 20 minutes:
1. history (தமிழ் வரலாறு & தொல்லியல்)
2. tamilnadu (தமிழகம்)
3. national (இந்தியா)
4. world (உலகம்)
5. politics (அரசியல்)
6. business (வணிகம்)
7. tech (தொழில்நுட்பம்)
8. sports (விளையாட்டு)
9. cinema (சினிமா)
10. spiritual (ஆன்மிகம்)
11. astrology (இன்றைய ராசி பலன் - Daily once)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("arachudar.topic_rotator")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATE_FILE = ROOT_DIR / "data" / "topic_rotation_state.json"

TOPIC_CYCLE: List[str] = [
    "history",
    "tamilnadu",
    "national",
    "world",
    "politics",
    "business",
    "tech",
    "sports",
    "cinema",
    "spiritual",
    "astrology",
]

TOPIC_TITLES_TAMIL: Dict[str, str] = {
    "history": "தமிழ் வரலாறு & தொல்லியல்",
    "tamilnadu": "தமிழக செய்திகள் & மாவட்டங்கள்",
    "national": "தேசிய செய்திகள்",
    "world": "உலக செய்திகள் & சர்வதேச நிகழ்வுகள்",
    "politics": "அரசியல் களம்",
    "business": "வணிகம் & பங்குச்சந்தை",
    "tech": "அறிவியல் & தொழில்நுட்பம்",
    "sports": "விளையாட்டு அரங்கம்",
    "cinema": "திரைப்படம் & கலை",
    "spiritual": "ஆன்மிக தரிசனம் & ஆலயங்கள்",
    "astrology": "இன்றைய ராசி பலன் & பஞ்சாங்கம்",
}


class TopicRotator:
    """Manages sequential topic rotation across newsroom desks with daily cadence controls."""

    def __init__(self, state_path: Path = STATE_FILE):
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not read topic rotation state: {e}")
        return {
            "current_index": 0,
            "last_topic": None,
            "last_run_timestamp": None,
            "astrology_last_posted_date": None,
        }

    def _save_state(self):
        try:
            self.state_path.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Could not save topic rotation state: {e}")

    def peek_next_topic(self) -> str:
        """Returns the topic scheduled for the current/next execution without advancing index."""
        idx = self.state.get("current_index", 0) % len(TOPIC_CYCLE)
        return TOPIC_CYCLE[idx]

    def advance_to_next_topic(self) -> str:
        """
        Advances to the next topic in the cycle.
        If next topic is astrology and has already run today, advances to history.
        """
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        idx = self.state.get("current_index", 0) % len(TOPIC_CYCLE)
        topic = TOPIC_CYCLE[idx]

        # Check daily constraint for astrology (Rasi Palan)
        if topic == "astrology" and self.state.get("astrology_last_posted_date") == today_str:
            logger.info("Astrology (Rasi Palan) already published for today. Advancing to history.")
            idx = (idx + 1) % len(TOPIC_CYCLE)
            topic = TOPIC_CYCLE[idx]

        # Record publication state
        self.state["last_topic"] = topic
        self.state["last_run_timestamp"] = now.isoformat()
        if topic == "astrology":
            self.state["astrology_last_posted_date"] = today_str

        # Advance pointer for subsequent run
        self.state["current_index"] = (idx + 1) % len(TOPIC_CYCLE)
        self._save_state()

        logger.info(f"Topic Rotator dispatched active desk: [{topic}] ({TOPIC_TITLES_TAMIL.get(topic, topic)})")
        return topic

    def set_active_topic(self, topic: str):
        """Forces the rotator to anchor on a specific topic (e.g. for initial history post)."""
        if topic in TOPIC_CYCLE:
            idx = TOPIC_CYCLE.index(topic)
            self.state["current_index"] = (idx + 1) % len(TOPIC_CYCLE)
            self.state["last_topic"] = topic
            self.state["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
