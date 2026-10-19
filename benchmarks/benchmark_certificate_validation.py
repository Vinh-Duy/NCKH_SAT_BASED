"""Fixed new-seed certificate study; no SAT/ILP calls and no outcome filtering.

Prepare snapshots the cohort, protocol, environment and implementation before
execution. Run refuses changed inputs and existing observations. Interrupted
outputs are retained but are not presented as completed evidence.
"""
import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import networkx as nx
from scripts.construct_color_order import construct, verify_order
from scripts.matching_bound_certificate import generate as matching_generate, verify as matching_verify
from scripts.verify_clique_certificate import graph_digest, verify as clique_verify
from src.core.graph_utils import greedy_labeling

PROTOCOL = ROOT/'experiments/certificate_validation_v1.json'
SOURCES = ['benchmarks/benchmark_certificate_validation.py',
           'scripts/construct_color_order.py', 'scripts/matching_bound_certificate.py',
           'scripts/verify_clique_certificate.py', 'src/core/graph_utils.py',
           'src/core/parameters.py']
METHODS = ['greedy', 'matching_h', 'random_order', 'insertion_order', 'dsatur_h']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')


def write_csv(path, rows):
    if not rows:
        raise ValueError('cannot export empty study')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cohort(config):
    for n in config['random_sizes']:
        for seed in config['graph_seeds']:
            yield f'tree_{n}_seed{seed}', 'Tree', nx.random_labeled_tree(n, seed=seed)
            yield f'BA_{n}_m2_seed{seed}', 'BA', nx.barabasi_albert_graph(n, config['ba_edges'], seed=seed)
            for p in config['er_probabilities']:
                yield f'ER_{n}_p{p:.2f}_seed{seed}', f'ER p={p:.2f}', nx.gnp_random_graph(n, p, seed=seed)
    for a, b in config['grids']:
        yield f'grid_{a}x{b}', 'Grid stress', nx.convert_node_labels_to_integers(nx.grid_2d_graph(a, b))
    for n in config['cycles']:
        yield f'C_{n}', 'Cycle stress', nx.cycle_graph(n)
    for n in config['bipartite_part_sizes']:
        yield f'K_{n}_{n}', 'Bipartite stress', nx.complete_bipartite_graph(n, n)


def prepare(output, protocol=PROTOCOL):
    config = json.loads(protocol.read_text())
    if config['methods'] != METHODS:
        raise ValueError('method configuration differs from implementation')
    graphs = []
    for name, family, graph in cohort(config):
        data = dict(n=len(graph), edges=sorted([min(u, v), max(u, v)] for u, v in graph.edges()))
        graphs.append(dict(instance=name, family=family, graph=data, sha256=graph_digest(data)))
    if len(graphs) != config['expected_graphs'] or len({g['sha256'] for g in graphs}) != len(graphs):
        raise ValueError('cohort size or graph fingerprint duplication')
    if len(graphs)*len(config['parameter_pairs']) != config['expected_instances']:
        raise ValueError('parameter cohort size mismatch')
    if config['expected_instances']*len(METHODS) != config['expected_observations']:
        raise ValueError('observation count mismatch')
    prior = ROOT/'results/analysis/color_order/2d62af353a1756ae/certificates.jsonl'
    historical = {json.loads(line)['graph_sha256'] for line in prior.read_text().splitlines()}
    if historical & {g['sha256'] for g in graphs}:
        raise ValueError('new cohort overlaps a historical labeled graph')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'protocol.json', config)
    (output/'graphs.jsonl').write_text(''.join(json.dumps(g, sort_keys=True)+'\n' for g in graphs))
    identity = dict(prepared_utc=datetime.now(timezone.utc).isoformat(),
                    protocol_sha256=digest(output/'protocol.json'),
                    graphs_sha256=digest(output/'graphs.jsonl'),
                    historical_graph_source=str(prior.relative_to(ROOT)),
                    historical_graph_source_sha256=digest(prior),
                    sources={p:digest(ROOT/p) for p in SOURCES},
                    python=platform.python_version(), networkx=nx.__version__)
    write_json(output/'prepared.json', identity)
    return identity


def greedy_clique(square):
    """Deterministic valid clique from every start; never claims maximum size."""
    best = []
    for start in sorted(square):
        chosen, candidates = [start], set(square[start])
        while candidates:
            vertex = min(candidates, key=lambda v: (-len(candidates & set(square[v])), v))
            chosen.append(vertex)
            candidates.intersection_update(square[vertex])
        chosen.sort()
        if len(chosen) > len(best) or len(chosen) == len(best) and chosen < best:
            best = chosen
    return best


def random_order(graph, classes, h, k, seed, attempts):
    edges = sorted([min(u, v), max(u, v)] for u, v in graph.edges())
    order = list(range(len(classes)))
    if h == k:
        checked = verify_order(len(graph), edges, classes, order, h, k)
        return checked['labels'], 0
    rng = random.Random(seed)
    for attempt in range(1, attempts+1):
        rng.shuffle(order)
        if any(any(graph.has_edge(u, v) for u in classes[a] for v in classes[b])
               for a, b in zip(order, order[1:])):
            continue
        checked = verify_order(len(graph), edges, classes, order, h, k)
        return checked['labels'], attempt
    return None, attempts


def spaced_classes(n, classes, spacing):
    labels = [0]*n
    for index, cell in enumerate(classes):
        for v in cell:
            labels[v] = index*spacing
    return labels


def evaluate_graph(record, config):
    data = record['graph']
    graph = nx.Graph()
    graph.add_nodes_from(range(data['n']))
    graph.add_edges_from(data['edges'])
    square = nx.power(graph, 2)
    clique = greedy_clique(square)
    classes = construct(graph, 1, 1)['classes']
    class_hash = hashlib.sha256(json.dumps(classes).encode()).hexdigest()
    colors = nx.coloring.greedy_color(square, strategy='saturation_largest_first')
    matching = matching_generate(graph, 1, 1)
    delta = max(dict(graph.degree()).values(), default=0)
    observations, witnesses, matching_certificates = [], [], []
    for h, k in config['parameter_pairs']:
        _, greedy = greedy_labeling(graph, h, k)
        insertion = construct(graph, h, k, seed=config['algorithm_seed'], max_restarts=config['ordering_attempts'])
        if insertion['classes'] != classes:
            raise ValueError('ordering arms do not share the same partition')
        shuffled, tried = random_order(graph, classes, h, k, config['algorithm_seed'], config['ordering_attempts'])
        labels_by_method = dict(greedy=[greedy[v] for v in graph],
                               matching_h=spaced_classes(len(graph), classes, h),
                               random_order=shuffled,
                               insertion_order=None if insertion['labels'] is None else [insertion['labels'][v] for v in graph],
                               dsatur_h=[h*colors[v] for v in graph])
        degree_lb = h+(delta-1)*k if delta else 0
        clique_lb = k*max(0, len(clique)-1)
        matching_lb = None if matching is None else k*max(0, matching['square_chromatic']-1)
        lower = max(degree_lb, clique_lb, matching_lb or 0)
        greedy_span = max(labels_by_method['greedy'], default=0)
        for method in METHODS:
            labels = labels_by_method[method]
            span = None
            identifier = f'{record["instance"]}:h{h}k{k}:{method}'
            if labels is not None:
                span = max(labels, default=0)-min(labels, default=0)
                cert = dict(schema='lhk-square-clique-v1', id=identifier,
                            instance=record['instance'], graph=data, graph_sha256=record['sha256'],
                            h=h, k=k, clique=clique, lower_bound=clique_lb,
                            labels=labels, upper_bound=span, source_kind='new_seed_validation')
                clique_verify(cert)
                if span < lower:
                    raise ValueError('labeling contradicts mathematical bound')
                witnesses.append(cert)
                if matching is not None:
                    proof = copy.deepcopy(matching)
                    proof.update(id=identifier, instance=record['instance'], h=h, k=k,
                                 lower_bound=matching_lb, labels=labels, upper_bound=span)
                    matching_verify(proof)
                    matching_certificates.append(proof)
            attempts = tried if method == 'random_order' else insertion['attempts'] if method == 'insertion_order' else 0
            observations.append(dict(Instance=record['instance'], Family=record['family'],
                h=h, k=k, V=len(graph), Edges=graph.number_of_edges(), Graph_SHA256=record['sha256'],
                Method=method, Status='UNKNOWN' if labels is None else 'FEASIBLE',
                Span=span, Degree_LB=degree_lb, Clique_LB=clique_lb,
                Matching_LB=matching_lb, Best_LB=lower,
                Certified=span is not None and span == lower,
                Clique_Certified=span is not None and span == clique_lb,
                Matching_Certified=span is not None and span == matching_lb,
                Gap=None if span is None else span-lower,
                Improves_Greedy=span is not None and span < greedy_span,
                Matched_Classes=len(classes), Partition_SHA256=class_hash,
                Attempts=attempts, Witness_ID='' if labels is None else identifier))
    return observations, witnesses, matching_certificates


def summarize(rows):
    results = []
    for family, h, k, method in sorted({(r['Family'], r['h'], r['k'], r['Method']) for r in rows}):
        subset = [r for r in rows if (r['Family'], r['h'], r['k'], r['Method']) == (family,h,k,method)]
        feasible = [r for r in subset if r['Span'] is not None]
        results.append(dict(Family=family,h=h,k=k,Method=method,Cases=len(subset),
            Feasible=len(feasible),Unknown=len(subset)-len(feasible),
            Certified=sum(r['Certified'] for r in subset),
            Improves_Greedy=sum(r['Improves_Greedy'] for r in subset),
            Median_Gap=statistics.median(r['Gap'] for r in feasible) if feasible else None))
    return results


def run(output):
    identity = json.loads((output/'prepared.json').read_text())
    for name in ('protocol', 'graphs'):
        path = output/('protocol.json' if name == 'protocol' else 'graphs.jsonl')
        if digest(path) != identity[f'{name}_sha256']:
            raise ValueError('prepared cohort or protocol changed')
    for path, expected in identity['sources'].items():
        if digest(ROOT/path) != expected:
            raise ValueError(f'implementation changed after preparation: {path}')
    if platform.python_version() != identity['python'] or nx.__version__ != identity['networkx']:
        raise ValueError('prepared environment changed')
    if (output/'observations.csv').exists() or (output/'progress.jsonl').exists():
        raise FileExistsError('output already started; preserve it and prepare a fresh directory')
    config = json.loads((output/'protocol.json').read_text())
    graphs = [json.loads(line) for line in (output/'graphs.jsonl').read_text().splitlines()]
    rows, witnesses, proofs = [], [], []
    started = time.perf_counter()
    with (output/'progress.jsonl').open('x') as progress:
        for index, record in enumerate(graphs, 1):
            observed, valid, matching = evaluate_graph(record, config)
            rows.extend(observed)
            witnesses.extend(valid)
            proofs.extend(matching)
            progress.write(json.dumps(dict(instance=record['instance'], completed=index,
                               elapsed_seconds=time.perf_counter()-started))+'\n')
            progress.flush()
            print(f'{index}/{len(graphs)} {record["instance"]}', flush=True)
    if len(rows) != config['expected_observations'] or len({r['Witness_ID'] for r in rows if r['Witness_ID']}) != len(witnesses):
        raise ValueError('incomplete or duplicate observation cohort')
    write_csv(output/'observations.csv', rows)
    write_csv(output/'summary.csv', summarize(rows))
    for name, records in [('witnesses', witnesses), ('matching_certificates', proofs)]:
        (output/f'{name}.jsonl').write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in records))
    totals = {m:dict(observations=sum(r['Method']==m for r in rows),
                    feasible=sum(r['Method']==m and r['Span'] is not None for r in rows),
                    certified=sum(r['Method']==m and r['Certified'] for r in rows),
                    improves_greedy=sum(r['Method']==m and r['Improves_Greedy'] for r in rows)) for m in METHODS}
    write_json(output/'sources.json', dict(identity=identity, completed_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.perf_counter()-started, totals=totals,
        outputs_sha256={p.name:digest(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'run'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'prepare':
        prepare(args.output)
        print(f'Prepared fixed study: {args.output}')
    else:
        run(args.output)
