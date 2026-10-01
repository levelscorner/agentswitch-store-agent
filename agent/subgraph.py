"""Subgraph sub-agent — the Scale-2 hierarchy primitive.

A `Subgraph` is a named sub-agent that declares the channels it READS (`inputs`)
and WRITES (`outputs`), then runs its OWN internal DAG on a PRIVATE local state
seeded only from the scoped input. It returns only its declared outputs. The parent
never hands it the whole blackboard, and its internal scratch never leaks back —
that isolation is the whole point (correctness + a bounded token/context budget).
"""
from types import SimpleNamespace

from agent.dag import DAG
from agent.state import State


class Subgraph:
    def __init__(self, name, inputs, outputs, build):
        self.name = name
        self.inputs = list(inputs)     # channel names it may read from the parent
        self.outputs = list(outputs)   # channel names it writes back to the parent
        self._build = build            # build() -> DAG of internal steps

    def run(self, client, scoped_input):
        local = State(scoped_input)                 # private local state, seeded from the slice
        ctx = SimpleNamespace(client=client)
        self._build().run(ctx, local)
        return {k: local.get(k) for k in self.outputs}
