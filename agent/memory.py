"""3-tier memory (S07), backed by the platform's AgentMemory with a local fallback.

Three tiers, three ideas:
  - Factual    : stable facts (ids, definitions)        -> AgentMemory category "fact"
  - Episodic   : a diary of past runs (recipes)         -> AgentMemory category "context"
  - Preference : standing rules (house style, meanings) -> local JSON (per agent)

Local JSON is the always-available cache; the platform is mirrored best-effort, so a
run never fails on a memory hiccup and facts survive across machines.
"""
import json
import time
from pathlib import Path

MEM_DIR = Path(__file__).parent / "mem_store"
_CATEGORY = {"factual": "fact", "episodic": "context", "preference": "preference"}


class _JsonStore:
    def __init__(self, name):
        self.path = MEM_DIR / f"{name}.json"

    def _load(self):
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return {}

    def _save(self, data):
        MEM_DIR.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))


class KeyValueTier(_JsonStore):
    """Factual and Preference are both simple key -> value stores."""

    def get(self, key, default=None):
        return self._load().get(key, default)

    def set(self, key, value):
        data = self._load()
        data[key] = value
        self._save(data)

    def all(self):
        return self._load()


class EpisodicTier(_JsonStore):
    """A growing list of past runs (a diary)."""

    def add(self, episode):
        data = self._load()
        data.setdefault("episodes", []).append({**episode, "at": time.time()})
        self._save(data)

    def recent(self, n=5):
        return self._load().get("episodes", [])[-n:]


class Memory:
    """One object the agent carries: read at the start of a task, write at the end.
    Pass a client to mirror factual/episodic memory onto the platform's AgentMemory."""

    def __init__(self, client=None):
        self.client = client
        self.facts = KeyValueTier("facts")        # -> AgentMemory "fact"
        self.episodes = EpisodicTier("episodes")  # -> AgentMemory "context"
        self.prefs = KeyValueTier("prefs")        # standing rules (local)

    def set_fact(self, key, value, importance=3):
        if self.facts.get(key) == value:
            return
        self.facts.set(key, value)
        self._platform_write("factual", key, value, importance)

    def get_fact(self, key, default=None):
        v = self.facts.get(key)
        if v is not None:
            return v
        v = self._platform_read("factual", key)
        return v if v is not None else default

    def add_episode(self, episode, importance=2):
        self.episodes.add(episode)
        self._platform_write("episodic", f"ep-{int(time.time())}", episode, importance)

    def seed_defaults(self):
        """Give the agent its starting preferences so it is useful on day one."""
        if not self.prefs.get("house_style"):
            self.prefs.set("house_style", "Clear, terse, benefit-led. Short sentences. No hype.")
        if not self.prefs.get("no_traffic_definition"):
            self.prefs.set("no_traffic_definition",
                           "orphan pages: published, not in any WebsiteMenu, not linked from another page")
        return self

    # --- platform mirror (best effort; never raises) ---
    def _platform_write(self, tier, key, value, importance):
        if not self.client or self._platform_read(tier, key) is not None:
            return
        try:
            self.client.call("AgentMemory.create", {
                "category": _CATEGORY[tier],
                "content": f"{key} = {json.dumps(value)}",
                "importance": importance, "source": "system", "is_active": True})
        except Exception:
            pass

    def _platform_read(self, tier, key):
        if not self.client:
            return None
        try:
            r = self.client.call("AgentMemory.list", {"category": _CATEGORY[tier], "limit": 50})
            rows = r if isinstance(r, list) else r.get("items", r.get("data", r.get("results", [])))
            for row in rows:
                c = row.get("content", "")
                if c.startswith(key + " = "):
                    return json.loads(c[len(key) + 3:])
        except Exception:
            pass
        return None


if __name__ == "__main__":
    m = Memory().seed_defaults()
    print("prefs:", m.prefs.all())
    print("recent episodes:", m.episodes.recent())
