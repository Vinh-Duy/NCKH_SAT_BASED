"""Genetic search over vertex orders with a feasible L(h,k) decoder."""

from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Hashable

import networkx as nx

from src.core.graph_utils import graph_constraints, validate_graph
from src.core.parameters import validate_gaps


Vertex = Hashable


@dataclass(frozen=True)
class SearchResult:
    """Best feasible labeling found by one deterministic search run."""

    span: int
    labels: dict[Vertex, int]
    evaluations: int
    runtime_seconds: float
    seed: int
    method: str


def _constraint_neighbors(graph: nx.Graph, h: int, k: int) -> dict[Vertex, tuple[tuple[Vertex, int], ...]]:
    """Build symmetric, exact-distance constraints once for decoder calls."""
    validate_graph(graph)
    validate_gaps(h, k)
    constraints: dict[Vertex, list[tuple[Vertex, int]]] = {v: [] for v in graph.nodes()}
    edges, distance_two = graph_constraints(graph)
    for u, v in edges:
        constraints[u].append((v, h))
        constraints[v].append((u, h))
    for u, v in distance_two:
        constraints[u].append((v, k))
        constraints[v].append((u, k))
    return {v: tuple(pairs) for v, pairs in constraints.items()}


def decode_order(
    order,
    constraints: dict[Vertex, tuple[tuple[Vertex, int], ...]],
) -> tuple[int, dict[Vertex, int]]:
    """Greedily decode an order into a feasible labeling.

    Every constrained pair is checked when its later endpoint is processed.
    The decoder chooses the smallest nonnegative available label, so each
    constructed label is canonical relative to the prefix. The returned span
    is max(label)-min(label), with span zero for the empty graph.
    """
    vertices = tuple(constraints)
    order = tuple(order)
    if len(order) != len(vertices) or len(set(order)) != len(order) or set(order) != set(vertices):
        raise ValueError("order must be a permutation of the complete vertex set")
    labels: dict[Vertex, int] = {}
    for vertex in order:
        forbidden: set[int] = set()
        for other, gap in constraints[vertex]:
            if other in labels:
                forbidden.update(range(labels[other] - gap + 1, labels[other] + gap))
        label = 0
        while label in forbidden:
            label += 1
        labels[vertex] = label
    return (max(labels.values()) - min(labels.values()) if labels else 0), labels


def _ox1(first: tuple[Vertex, ...], second: tuple[Vertex, ...], rng: random.Random) -> tuple[Vertex, ...]:
    """Order crossover 1 for permutations."""
    size = len(first)
    if size < 2:
        return first
    left, right = sorted(rng.sample(range(size), 2))
    child: list[Vertex | None] = [None] * size
    child[left:right + 1] = first[left:right + 1]
    retained = set(child[left:right + 1])
    fill = [gene for gene in second[right + 1:] + second[:right + 1] if gene not in retained]
    positions = list(range(right + 1, size)) + list(range(0, left))
    for position, gene in zip(positions, fill):
        child[position] = gene
    if any(gene is None for gene in child):
        raise RuntimeError("OX1 produced an incomplete permutation")
    return tuple(child)  # type: ignore[arg-type]


def _invert(order: tuple[Vertex, ...], rng: random.Random) -> tuple[Vertex, ...]:
    if len(order) < 2:
        return order
    left, right = sorted(rng.sample(range(len(order)), 2))
    return order[:left] + tuple(reversed(order[left:right + 1])) + order[right + 1:]


def genetic_search(
    graph: nx.Graph,
    h: int = 2,
    k: int = 1,
    *,
    seed: int = 0,
    population_size: int = 40,
    evaluation_budget: int = 1000,
    crossover_probability: float = 0.9,
    mutation_probability: float = 0.05,
    tournament_size: int = 3,
) -> SearchResult:
    """Run a fixed-evaluation-budget GA with OX1, inversion, and elitism."""
    _validate_search_settings(population_size, evaluation_budget, crossover_probability,
                              mutation_probability, tournament_size)
    constraints = _constraint_neighbors(graph, h, k)
    vertices = tuple(graph.nodes())
    rng = random.Random(seed)
    started = time.perf_counter()
    population: list[tuple[Vertex, ...]] = []
    scores: list[tuple[int, dict[Vertex, int]]] = []
    evaluations = 0
    best_order: tuple[Vertex, ...] | None = None
    best_span: int | None = None
    best_labels: dict[Vertex, int] = {}

    def evaluate(order: tuple[Vertex, ...]) -> tuple[int, dict[Vertex, int]]:
        nonlocal evaluations, best_order, best_span, best_labels
        span, labels = decode_order(order, constraints)
        evaluations += 1
        if best_span is None or span < best_span:
            best_order, best_span, best_labels = order, span, labels
        return span, labels

    for _ in range(min(population_size, evaluation_budget)):
        order = list(vertices)
        rng.shuffle(order)
        population.append(tuple(order))
        scores.append(evaluate(tuple(order)))

    while evaluations < evaluation_budget:
        elite_index = min(range(len(population)), key=lambda i: scores[i][0])
        next_population = [population[elite_index]]
        next_scores = [scores[elite_index]]
        while len(next_population) < population_size and evaluations < evaluation_budget:
            parent_a = _tournament(population, scores, rng, tournament_size)
            parent_b = _tournament(population, scores, rng, tournament_size)
            child = _ox1(parent_a, parent_b, rng) if rng.random() < crossover_probability else parent_a
            if rng.random() < mutation_probability:
                child = _invert(child, rng)
            next_population.append(child)
            next_scores.append(evaluate(child))
        population, scores = next_population, next_scores

    return SearchResult(best_span or 0, best_labels, evaluations,
                        time.perf_counter() - started, seed, "ga_ox1_inversion")


def random_order_search(
    graph: nx.Graph,
    h: int = 2,
    k: int = 1,
    *,
    seed: int = 0,
    evaluation_budget: int = 1000,
) -> SearchResult:
    """Equal-evaluation random-permutation multi-start baseline."""
    if not isinstance(evaluation_budget, int) or isinstance(evaluation_budget, bool) or evaluation_budget < 1:
        raise ValueError("evaluation_budget must be a positive integer")
    constraints = _constraint_neighbors(graph, h, k)
    vertices = tuple(graph.nodes())
    rng = random.Random(seed)
    started = time.perf_counter()
    best_span: int | None = None
    best_labels: dict[Vertex, int] = {}
    for _ in range(evaluation_budget):
        order = list(vertices)
        rng.shuffle(order)
        span, labels = decode_order(order, constraints)
        if best_span is None or span < best_span:
            best_span, best_labels = span, labels
    return SearchResult(best_span or 0, best_labels, evaluation_budget,
                        time.perf_counter() - started, seed, "random_order")


def greedy_order_search(graph: nx.Graph, h: int = 2, k: int = 1) -> SearchResult:
    """Single deterministic graph-insertion-order decoding baseline."""
    constraints = _constraint_neighbors(graph, h, k)
    started = time.perf_counter()
    span, labels = decode_order(tuple(graph.nodes()), constraints)
    return SearchResult(span, labels, 1, time.perf_counter() - started, 0, "greedy_order")


def _tournament(population, scores, rng, size):
    candidates = [rng.randrange(len(population)) for _ in range(min(size, len(population)))]
    winner = min(candidates, key=lambda i: scores[i][0])
    return population[winner]


def _validate_search_settings(population_size, evaluation_budget, crossover_probability,
                              mutation_probability, tournament_size):
    if not isinstance(population_size, int) or isinstance(population_size, bool) or population_size < 2:
        raise ValueError("population_size must be an integer >= 2")
    if not isinstance(evaluation_budget, int) or isinstance(evaluation_budget, bool) or evaluation_budget < 1:
        raise ValueError("evaluation_budget must be a positive integer")
    for name, value in (("crossover_probability", crossover_probability),
                        ("mutation_probability", mutation_probability)):
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{name} must lie in [0, 1]")
    if not isinstance(tournament_size, int) or isinstance(tournament_size, bool) or tournament_size < 1:
        raise ValueError("tournament_size must be a positive integer")
