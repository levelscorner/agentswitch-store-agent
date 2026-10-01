"""Typed blackboard with named channels + reducers (the state-schema layer).

A `State` is a `dict` (so legacy nodes that do `state["k"] = v` still work — that is
a last-write), PLUS:
  - `merge(key, value)` — reducer-aware write, for channels more than one node writes.
  - `scope(*keys)`      — a read-only slice handed to a sub-agent (scoped INPUT).
  - `absorb(out, keys)` — merge a sub-agent's scoped OUTPUT back, channel by channel.

Reducers are the rule for combining concurrent writes to one channel. Without them,
two parallel writers silently clobber each other; with them you choose append / union /
sum / last. This contract is what makes safe parallelism and subgraphs possible.
"""


def _append(old, new):
    return (old or []) + (new if isinstance(new, list) else [new])


def _union(old, new):
    return sorted(set(old or []) | set(new if isinstance(new, (list, set, tuple)) else [new]))


def _sum(old, new):
    return (old or 0) + (new or 0)


def _last(old, new):
    return new


REDUCERS = {
    "disagreement_candidates": _append,   # payment/stock detectors append here
    "_pending": _append,
    "cost": _sum,
}


class State(dict):
    """dict + reducer-aware merges + scoped I/O for sub-agents."""

    def merge(self, key, value):
        reducer = REDUCERS.get(key, _last)
        self[key] = reducer(self.get(key), value)
        return self

    def scope(self, *keys):
        """Only the channels a sub-agent declared it reads — nothing else leaks in."""
        return {k: self.get(k) for k in keys}

    def absorb(self, out, keys):
        """Merge a sub-agent's declared outputs back; everything else it did stays private."""
        for k in keys:
            if k in out:
                self.merge(k, out[k])
        return self
