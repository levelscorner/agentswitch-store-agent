"""Tiny DAG engine (S08 — graphs, not loops).

Pure plumbing: it runs nodes in dependency order, runs independent nodes in
parallel on a small thread pool, and threads one shared blackboard `state`
(plus a shared read-only `ctx` of services) through every node.

The engine knows nothing about publishing or analysis — the intelligence lives
in each node's run(ctx, state) function. Nodes write DISTINCT keys into state,
so parallel writes don't collide.
"""
import concurrent.futures as cf


class Node:
    def __init__(self, name, run, deps=None):
        self.name = name
        self.run = run              # run(ctx, state) -> None; writes into state
        self.deps = list(deps or [])


class DAG:
    def __init__(self, max_workers=3):
        self.nodes = {}
        self.max_workers = max_workers

    def add(self, node):
        self.nodes[node.name] = node
        return self

    def run(self, ctx, state):
        done, pending, order = set(), dict(self.nodes), []
        with cf.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while pending:
                ready = [n for n in pending.values() if all(d in done for d in n.deps)]
                if not ready:
                    raise RuntimeError("DAG stuck (cycle or unmet dep): " + ", ".join(pending))
                futs = {ex.submit(n.run, ctx, state): n for n in ready}
                for fut in cf.as_completed(futs):
                    n = futs[fut]
                    fut.result()            # re-raise any node error
                    done.add(n.name)
                    pending.pop(n.name)
                    order.append(n.name)
        state.setdefault("_trace", {})["dag_order"] = order
        return state
