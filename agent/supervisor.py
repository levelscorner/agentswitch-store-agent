"""Supervisor — the 'daddy' router.

Holds a fixed roster of workers and routes the planned goals to them, running
independents in parallel on the DAG engine, then verifying. A worker is either:
  - a plain function `fn(client, state)` — trusted, gets the whole blackboard (legacy), OR
  - a `Subgraph` sub-agent — gets ONLY its declared input slice, and only its declared
    outputs are absorbed back.

The supervisor's freedom is bounded: it ROUTES among a designed roster and FILLS the
slices. It does not invent nodes or edges at runtime — that is what keeps it controllable.
"""
from agent.dag import DAG, Node
from agent.subgraph import Subgraph
from agent import verify


class Supervisor:
    def __init__(self, roster):
        self.roster = roster    # {goal: fn(client, state) | Subgraph}

    def _node_for(self, goal):
        worker = self.roster[goal]
        if isinstance(worker, Subgraph):
            def run(ctx, s, w=worker):
                out = w.run(ctx.client, s.scope(*w.inputs))   # scoped INPUT
                s.absorb(out, w.outputs)                       # scoped OUTPUT via reducers
            return Node(goal, run)
        return Node(goal, lambda ctx, s, fn=worker: fn(ctx.client, s))

    def run(self, ctx, state, goals):
        dag = DAG(max_workers=3)
        for g in goals:
            if g in self.roster:
                dag.add(self._node_for(g))
        dag.add(Node("verify", lambda ctx, s: verify.run_verify(ctx.client, s),
                     deps=[g for g in goals if g in self.roster]))
        dag.run(ctx, state)
        return state

    def run_one(self, ctx, state, goal):
        """Re-run a single worker (used by the refine pass)."""
        if goal in self.roster:
            self._node_for(goal).run(ctx, state)
