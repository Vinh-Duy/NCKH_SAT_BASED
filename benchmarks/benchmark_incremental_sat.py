"""Compare baseline SAT, incremental SAT, validated GA bounds, ILP and heuristics.

The frozen input cohort is the 69-graph certificate-validation manifest
(207 graph/(h,k) instances). Each method receives the same external wall cap.
This is a new cohort and is not the historical 117-instance experiment.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import greedy_labeling, lower_bound
from src.core.io import BenchmarkWriter, default_output
from src.core.validator import validate_labeling
from src.heuristics.genetic_labeling import genetic_search, random_order_search
from src.solvers.ilp_solver import solve_graph as solve_ilp
from src.solvers.sat_solver import solve_graph as solve_sat


MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"
PAIRS = ((1, 1), (2, 1), (3, 2))
METHODS = ("sat_original", "sat_incremental", "sat_ga_bound", "ilp", "ga", "random_order")
FIELDS = [
    "Graph", "Instance", "Manifest_SHA256", "Family", "h", "k", "Method",
    "Status", "Solver_Outcome", "Termination", "Timeout_Or_Interruption",
    "Span", "Best_Span", "Lower_Bound", "Optimality_Proven", "Optimality_Source",
    "Feasible_Witness", "Valid_Witness", "Error_Info", "Log_Reference",
    "Runtime_Seconds", "SAT_Runtime_Seconds", "GA_Runtime_Seconds",
    "Validation_Runtime_Seconds", "Evaluations", "Seeds_Completed", "Variables",
    "Clauses_or_Constraints", "SAT_Calls", "SAT_Conflicts", "SAT_Decisions",
    "SAT_Propagations", "Timeout_Seconds", "Witness_JSON",
]
GA_CONFIG = dict(population_size=40, evaluation_budget=1000,
                 crossover_probability=0.9, mutation_probability=0.05,
                 tournament_size=3, seed_base=0, repeats=10)


def _last_sat_outcome(result):
    if result.attempt_statistics:
        return result.attempt_statistics[-1].get("outcome", "NOT_RUN")
    if result.history:
        return result.history[-1].rsplit(":", 1)[-1]
    return "NOT_RUN"


def _safe_error(error):
    """Keep useful exception context while removing credential-shaped values."""
    message = str(error).replace("\r", " ").replace("\n", " ")
    message = re.sub(
        r"(?i)\b(WLSACCESSID|WLSSECRET|LICENSEID)\b"
        r"(?:\s+to\s+value\s+[^,;\s]+|\s*[=:]\s*[^,;\s]+)",
        r"\1=<redacted>", message,
    )
    message = re.sub(
        r"(?i)\b(GRB_LICENSE_FILE|AUTHORIZATION)\b\s*[=:]\s*[^,;\s]+",
        r"\1=<redacted>", message,
    )
    return f"{type(error).__name__}: {message[:500]}"


def _parse_bool(value):
    return value is True or str(value).lower() in {"true", "1"}


def _incremental_record_valid(row, witness, graphs_by_name):
    """Validate row semantics and any required witness artifact before resume."""
    required = ("Graph", "Instance", "Manifest_SHA256", "Family", "h", "k", "Method",
                "Status", "Solver_Outcome", "Termination", "Timeout_Or_Interruption",
                "Optimality_Proven", "Feasible_Witness", "Best_Span", "Error_Info")
    if any(row.get(key) in (None, "") for key in required if key not in {
            "Best_Span", "Error_Info"}):
        return False
    status = row.get("Status")
    outcome = row.get("Solver_Outcome")
    termination = row.get("Termination")
    if status not in {"OPT", "FEASIBLE", "UNKNOWN", "TIMEOUT", "ERROR", "UNAVAILABLE", "INFEASIBLE"}:
        return False
    if outcome not in {"SAT", "UNSAT", "UNKNOWN", "NOT_RUN", "NOT_APPLICABLE",
                       "OPTIMAL", "FEASIBLE", "INFEASIBLE", "TIME_LIMIT", "INTERRUPTED",
                       "ERROR", "UNAVAILABLE", "INVALID"}:
        return False
    if termination not in {"COMPLETED", "SOLVER_UNKNOWN", "SOLVER_TIME_LIMIT",
                           "SOLVER_UNAVAILABLE", "WALL_TIMEOUT", "WORKER_ERROR",
                           "WORKER_EXIT", "INVALID_WITNESS", "SOLVER_ERROR"}:
        return False
    if status == "UNKNOWN" and (outcome != "UNKNOWN" or termination != "SOLVER_UNKNOWN"):
        return False
    if outcome == "UNKNOWN" and status != "UNKNOWN":
        return False
    if status == "TIMEOUT" and termination not in {"WALL_TIMEOUT", "SOLVER_TIME_LIMIT"}:
        return False
    if status == "ERROR" and termination not in {
            "WORKER_ERROR", "WORKER_EXIT", "INVALID_WITNESS", "SOLVER_ERROR"}:
        return False
    if status == "UNAVAILABLE" and termination != "SOLVER_UNAVAILABLE":
        return False
    if status == "INFEASIBLE" and outcome != "INFEASIBLE":
        return False
    if status == "UNAVAILABLE" and outcome != "UNAVAILABLE":
        return False
    if status == "TIMEOUT" and outcome not in {"TIME_LIMIT", "INTERRUPTED"}:
        return False
    if status == "ERROR" and outcome not in {"ERROR", "INVALID", "INFEASIBLE"}:
        return False
    if outcome == "OPTIMAL" and (status != "OPT" or not _parse_bool(row.get("Optimality_Proven"))):
        return False
    if outcome in {"TIME_LIMIT", "INTERRUPTED"} and status != "TIMEOUT":
        return False
    if outcome in {"ERROR", "INVALID"} and status != "ERROR":
        return False
    if outcome == "UNAVAILABLE" and status != "UNAVAILABLE":
        return False
    if termination == "SOLVER_ERROR" and status != "ERROR":
        return False
    if status == "OPT" and not _parse_bool(row.get("Optimality_Proven")):
        return False
    if status != "OPT" and _parse_bool(row.get("Optimality_Proven")):
        return False
    if (termination in {"WALL_TIMEOUT", "SOLVER_TIME_LIMIT", "WORKER_EXIT"}) != _parse_bool(
            row.get("Timeout_Or_Interruption")):
        return False
    if status in {"ERROR", "UNAVAILABLE"} and not row.get("Error_Info"):
        return False
    if status == "OPT":
        try:
            if not row.get("Best_Span") or int(row["Lower_Bound"]) < int(row["Best_Span"]):
                return False
        except (TypeError, ValueError):
            return False

    has_witness = _parse_bool(row.get("Feasible_Witness"))
    if _parse_bool(row.get("Valid_Witness")) != has_witness:
        return False
    if outcome in {"SAT", "FEASIBLE", "OPTIMAL"} and not has_witness:
        return False
    if (outcome == "INFEASIBLE" and has_witness and
            (status != "ERROR" or termination != "SOLVER_ERROR")):
        return False
    if not has_witness:
        return row.get("Best_Span", "") in (None, "")
    if witness is None or not row.get("Witness_JSON") or row.get("Best_Span", "") == "":
        return False
    if witness.get("Graph") != row.get("Graph"):
        return False
    result = witness.get("result")
    if not isinstance(result, dict):
        return False
    for field in ("Instance", "Family", "h", "k", "Method", "Solver_Outcome",
                  "Termination", "Best_Span", "Optimality_Proven", "Feasible_Witness"):
        if str(result.get(field)) != str(row.get(field)):
            return False
    try:
        csv_pairs = json.loads(row["Witness_JSON"])
        artifact_pairs = result.get("labels")
        if csv_pairs != artifact_pairs:
            return False
        _family, graph = graphs_by_name[row["Instance"]]
        node_by_repr = {repr(node): node for node in graph.nodes()}
        labels = {}
        for node_repr, value in artifact_pairs:
            if node_repr not in node_by_repr or isinstance(value, bool) or not isinstance(value, int):
                return False
            labels[node_by_repr[node_repr]] = value
        if len(labels) != len(graph) or set(labels) != set(graph.nodes()):
            return False
        span = max(labels.values(), default=0) - min(labels.values(), default=0)
        if span != int(row["Best_Span"]) or str(span) != str(row.get("Span")):
            return False
        valid, _ = validate_labeling(list(graph.edges()), _distance_two(graph), labels,
            span, int(row["h"]), int(row["k"]), vertices=graph.nodes())
        return bool(valid)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _incremental_row_complete(row, _witness):
    """Completed solver results resume; interruptions and infrastructure failures retry."""
    if row.get("Status") == "OPT" and _parse_bool(row.get("Optimality_Proven")):
        return True
    return row.get("Termination") not in {
        "WALL_TIMEOUT", "WORKER_ERROR", "WORKER_EXIT", "INVALID_WITNESS",
        "SOLVER_UNAVAILABLE", "SOLVER_ERROR",
    } and row.get("Solver_Outcome") not in {"ERROR", "UNAVAILABLE", "INVALID", "INTERRUPTED"}


def _read_manifest(path: Path):
    raw = path.read_bytes()
    entries = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    names = [entry["instance"] for entry in entries]
    if len(entries) != 69 or len(set(names)) != len(entries):
        raise ValueError("expected exactly 69 unique manifest graphs")
    import networkx as nx
    graphs = []
    for entry in entries:
        payload = entry["graph"]
        graph = nx.Graph()
        graph.add_nodes_from(range(payload["n"]))
        graph.add_edges_from(map(tuple, payload["edges"]))
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"manifest graph hash mismatch: {entry['instance']}")
        graphs.append((entry["instance"], entry["family"], graph))
    return graphs, hashlib.sha256(raw).hexdigest()


def _publish(connection, event):
    try:
        connection.send(event)
    except (BrokenPipeError, EOFError, OSError):
        pass


def _worker(connection, instance, family, graph, h, k, method, initial_labels, limit):
    """Run one method; parent enforces a hard end-to-end process deadline."""
    started = time.perf_counter()
    best = {"status": "FEASIBLE", "solver_outcome": "NOT_RUN", "termination": "COMPLETED",
            "optimality_source": "none", "error_info": "",
            "span": max(initial_labels.values(), default=0),
            "lower_bound": lower_bound(graph, h, k), "labels": dict(initial_labels), "source": "shared_greedy",
            "sat_runtime": 0.0, "ga_runtime": 0.0, "validation_runtime": 0.0,
            "evaluations": 0, "seeds_completed": 0, "variables": None,
            "clauses": None, "sat_calls": 0, "solver_stats": {}}

    def validate_candidate(labels, claimed_span):
        check_started = time.perf_counter()
        actual = max(labels.values(), default=0) - min(labels.values(), default=0)
        normalized = {v: value - min(labels.values(), default=0) for v, value in labels.items()}
        valid, errors = validate_labeling(
            list(graph.edges()), _distance_two(graph), normalized, actual, h, k,
            vertices=graph.nodes())
        best["validation_runtime"] += time.perf_counter() - check_started
        if not valid or actual != claimed_span:
            raise ValueError(f"independent witness validation failed: {errors[:4]}")
        return normalized, actual

    def improve(labels, span, *, status=None, lower_bound=None, **metrics):
        normalized, actual = validate_candidate(labels, span)
        if actual <= best["span"]:
            best.update(span=actual, labels=normalized, source=metrics.pop("source", best["source"]))
        if status:
            best["status"] = status
        if lower_bound is not None:
            best["lower_bound"] = max(best["lower_bound"], int(lower_bound))
        best.update(metrics)
        _publish(connection, {"kind": "progress", "state": deepcopy(best),
                              "elapsed": time.perf_counter() - started})

    try:
        if method in {"sat_original", "sat_incremental", "sat_ga_bound"}:
            initial = initial_labels
            if method == "sat_ga_bound":
                for seed in range(GA_CONFIG["seed_base"],
                                  GA_CONFIG["seed_base"] + GA_CONFIG["repeats"]):
                    ga_start = time.perf_counter()
                    candidate = genetic_search(graph, h, k, seed=seed,
                        population_size=GA_CONFIG["population_size"],
                        evaluation_budget=GA_CONFIG["evaluation_budget"],
                        crossover_probability=GA_CONFIG["crossover_probability"],
                        mutation_probability=GA_CONFIG["mutation_probability"],
                        tournament_size=GA_CONFIG["tournament_size"])
                    best["ga_runtime"] += time.perf_counter() - ga_start
                    best["evaluations"] += candidate.evaluations
                    best["seeds_completed"] += 1
                    checked, span = validate_candidate(candidate.labels, candidate.span)
                    if span < max(initial.values(), default=0):
                        initial = checked
                        improve(checked, span, source="validated_ga",
                                ga_runtime=best["ga_runtime"], evaluations=best["evaluations"],
                                seeds_completed=best["seeds_completed"])
                    else:
                        _publish(connection, {"kind": "progress", "state": deepcopy(best),
                                              "elapsed": time.perf_counter() - started})
                # The outer parent still enforces the shared wall cap. A solver
                # starts only if GA and independent witness checks leave budget.
            sat_started = time.perf_counter()
            def sat_progress(result):
                outcome = _last_sat_outcome(result)
                result_status = "UNKNOWN" if outcome == "UNKNOWN" and result.status != "OPT" else result.status
                proof_source = (
                    "sat_search" if result.completed_attempts else "elementary_bound"
                ) if result.status == "OPT" else "none"
                improve(result.labels, result.span, status=result_status,
                        lower_bound=result.proven_lower_bound, source=result.source,
                        solver_outcome=outcome,
                        termination="SOLVER_UNKNOWN" if outcome == "UNKNOWN" else "COMPLETED",
                        optimality_source=proof_source,
                        sat_runtime=result.sat_solve_time, variables=result.variable_count,
                        clauses=result.clause_count, sat_calls=result.completed_attempts,
                        solver_stats=dict(result.solver_stats))
            result = solve_sat(graph, solver_name="cadical",
                strategy="incremental" if method != "sat_original" else "hybrid",
                timeout_sec=None, h=h, k=k, progress_callback=sat_progress,
                initial_labels=initial if method == "sat_ga_bound" else None)
            best["sat_runtime"] = time.perf_counter() - sat_started
            outcome = _last_sat_outcome(result)
            result_status = "UNKNOWN" if outcome == "UNKNOWN" and result.status != "OPT" else result.status
            proof_source = (
                "sat_search" if result.completed_attempts else "elementary_bound"
            ) if result.status == "OPT" else "none"
            improve(result.labels, result.span, status=result_status,
                    lower_bound=result.proven_lower_bound,
                    source=result.source, sat_runtime=best["sat_runtime"],
                    solver_outcome=outcome,
                    termination="SOLVER_UNKNOWN" if outcome == "UNKNOWN" else "COMPLETED",
                    optimality_source=proof_source,
                    variables=result.variable_count, clauses=result.clause_count,
                    sat_calls=result.completed_attempts,
                    solver_stats=dict(result.solver_stats))
        elif method == "ilp":
            def ilp_progress(state):
                improve(state["labels"], state["span"], status=state["status"],
                        lower_bound=state["proven_lower_bound"], source=state["source"],
                        variables=state["variable_count"], clauses=state["clause_count"])
            span, variables, constraints, runtime, status, labels = solve_ilp(
                graph, solver_name="gurobi", timeout_sec=limit, h=h, k=k,
                formulation="assignment", progress_callback=ilp_progress)
            outcome = {
                "OPT": "OPTIMAL", "FEASIBLE": "FEASIBLE", "TIMEOUT": "TIME_LIMIT",
                "INFEASIBLE": "INFEASIBLE", "UNAVAILABLE": "UNAVAILABLE",
                "INVALID": "INVALID",
            }.get(status, "ERROR")
            termination = {
                "TIMEOUT": "SOLVER_TIME_LIMIT", "UNAVAILABLE": "SOLVER_UNAVAILABLE",
                "INVALID": "INVALID_WITNESS", "ERROR": "SOLVER_ERROR",
                "INFEASIBLE": "SOLVER_ERROR" if best["labels"] else "COMPLETED",
            }.get(status, "COMPLETED")
            result_status = "TIMEOUT" if status == "TIMEOUT" else status
            if status == "UNAVAILABLE":
                best["error_info"] = "Gurobi runtime or license unavailable"
            elif status == "ERROR":
                best["error_info"] = "ILP solver returned an error without a verified result"
            elif status == "INFEASIBLE" and best["labels"]:
                result_status = "ERROR"
                best["error_info"] = "Gurobi reported infeasible despite a verified incumbent"
            elif status == "INVALID":
                result_status = "ERROR"
                best["error_info"] = "ILP solver returned an invalid witness"
            if labels:
                improve(labels, span, status=result_status,
                        lower_bound=span if status == "OPT" else best["lower_bound"],
                        variables=variables, clauses=constraints, source="gurobi",
                        solver_outcome=outcome, termination=termination,
                        optimality_source="gurobi_optimal" if status == "OPT" else "none")
            else:
                best.update(status=result_status, solver_outcome=outcome,
                            termination=termination)
        else:
            from src.core.graph_utils import graph_constraints
            search = genetic_search if method == "ga" else random_order_search
            for seed in range(GA_CONFIG["seed_base"], GA_CONFIG["seed_base"] + GA_CONFIG["repeats"]):
                options = {"seed": seed, "evaluation_budget": GA_CONFIG["evaluation_budget"]}
                if method == "ga":
                    options.update({key: GA_CONFIG[key] for key in (
                        "population_size", "crossover_probability", "mutation_probability",
                        "tournament_size")})
                search_started = time.perf_counter()
                candidate = search(graph, h, k, **options)
                best["ga_runtime"] += time.perf_counter() - search_started
                best["evaluations"] += candidate.evaluations
                best["seeds_completed"] += 1
                checked, span = validate_candidate(candidate.labels, candidate.span)
                if span < best["span"]:
                    improve(checked, span, source=candidate.method,
                            ga_runtime=best["ga_runtime"], evaluations=best["evaluations"],
                            seeds_completed=best["seeds_completed"])
                else:
                    _publish(connection, {"kind": "progress", "state": deepcopy(best),
                                          "elapsed": time.perf_counter() - started})
            best.update(status="FEASIBLE", solver_outcome="NOT_APPLICABLE",
                        termination="COMPLETED")
        _publish(connection, {"kind": "done", "state": best,
                              "elapsed": time.perf_counter() - started})
    except Exception as error:
        message = _safe_error(error)
        best.update(status="ERROR", solver_outcome="ERROR", termination="WORKER_ERROR",
                    error_info=message, optimality_source="none")
        _publish(connection, {"kind": "error", "error": message,
                              "state": best, "elapsed": time.perf_counter() - started})
    finally:
        connection.close()


def _distance_two(graph):
    import networkx as nx
    return [(u, v) for u, distances in nx.all_pairs_shortest_path_length(graph, cutoff=2)
            for v, distance in distances.items() if distance == 2 and u < v]


def _run_arm(instance, family, graph, h, k, method, timeout, context):
    # Common, validated incumbent is prepared once for each arm and every arm
    # pays for this setup inside the same end-to-end wall budget.
    started = time.perf_counter()
    _, initial = greedy_labeling(graph, h, k)
    pconn, cconn = context.Pipe(duplex=False)
    process = context.Process(target=_worker,
        args=(cconn, instance, family, graph, h, k, method, initial, timeout))
    state = {"status": "FEASIBLE", "solver_outcome": "NOT_RUN", "termination": "COMPLETED",
             "optimality_source": "none", "error_info": "",
             "span": max(initial.values(), default=0),
             "lower_bound": lower_bound(graph, h, k), "labels": initial, "source": "shared_greedy",
             "sat_runtime": 0.0, "ga_runtime": 0.0, "validation_runtime": 0.0,
             "evaluations": 0, "seeds_completed": 0, "variables": None,
             "clauses": None, "sat_calls": 0, "solver_stats": {}}
    termination, error = "COMPLETED", ""
    received_done = False
    process.start()
    cconn.close()
    while process.is_alive() or pconn.poll():
        remaining = timeout - (time.perf_counter() - started)
        if remaining <= 0:
            termination = "WALL_TIMEOUT"
            process.terminate()
            break
        if pconn.poll(min(0.1, remaining)):
            try:
                event = pconn.recv()
            except EOFError:
                break
            if event.get("state"):
                state = event["state"]
            if event["kind"] == "error":
                termination, error = "WORKER_ERROR", event["error"]
                break
            if event["kind"] == "done":
                received_done = True
                break
    process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join()
        if not received_done and termination == "COMPLETED":
            termination = "WORKER_EXIT"
            error = f"worker did not exit after publishing its final state (exit code {process.exitcode})"
    elif not received_done and termination == "COMPLETED":
        termination = "WORKER_EXIT"
        error = f"worker exited without a final result (exit code {process.exitcode})"
    pconn.close()
    elapsed = time.perf_counter() - started
    state["termination"] = termination
    if termination == "WALL_TIMEOUT" and state.get("status") != "OPT":
        state.update(status="TIMEOUT", solver_outcome="INTERRUPTED", optimality_source="none")
    elif termination == "WORKER_ERROR":
        state.update(status="ERROR", solver_outcome="ERROR", optimality_source="none")
    elif termination == "WORKER_EXIT":
        state.update(status="ERROR", solver_outcome="ERROR", optimality_source="none")
    if (state["lower_bound"] >= state["span"] and state["status"] not in
            {"ERROR", "UNAVAILABLE", "TIMEOUT", "UNKNOWN", "INFEASIBLE"}):
        state["status"] = "OPT"
        state["lower_bound"] = state["span"]
        if state.get("optimality_source") == "none":
            state["optimality_source"] = "elementary_bound"
    valid = False
    check_start = time.perf_counter()
    if state["labels"]:
        valid, _ = validate_labeling(list(graph.edges()), _distance_two(graph),
            state["labels"], state["span"], h, k, vertices=graph.nodes())
    validation_wall = time.perf_counter() - check_start
    if not valid and state["labels"]:
        termination = state["termination"] = "INVALID_WITNESS"
        error = state["error_info"] = "parent witness validation failed"
        state.update(status="ERROR", solver_outcome="INVALID", optimality_source="none")
    elif not state["labels"] and state.get("status") in {"OPT", "FEASIBLE"}:
        termination = state["termination"] = "WORKER_ERROR"
        error = state["error_info"] = "solver returned no data and no verified witness"
        state.update(status="ERROR", solver_outcome="ERROR", optimality_source="none")
    state["error_info"] = state.get("error_info") or error
    has_witness = bool(valid)
    best_span = state["span"] if has_witness else None
    optimality_proven = state["status"] == "OPT" and has_witness
    return {
        "Graph": f"{instance}__h{h}_k{k}__{method}", "Instance": instance,
        "Manifest_SHA256": "", "Family": family, "h": h, "k": k, "Method": method,
        "Status": state["status"], "Solver_Outcome": state.get("solver_outcome", "NOT_RUN"),
        "Termination": termination,
        "Timeout_Or_Interruption": termination in {"WALL_TIMEOUT", "SOLVER_TIME_LIMIT", "WORKER_EXIT"},
        "Span": best_span, "Best_Span": best_span,
        "Lower_Bound": state["lower_bound"], "Optimality_Proven": optimality_proven,
        "Optimality_Source": state.get("optimality_source", "none") if optimality_proven else "none",
        "Feasible_Witness": has_witness, "Valid_Witness": has_witness,
        "Error_Info": state["error_info"], "Log_Reference": "",
        "Runtime_Seconds": f"{elapsed:.6f}",
        "SAT_Runtime_Seconds": f"{state['sat_runtime']:.6f}",
        "GA_Runtime_Seconds": f"{state['ga_runtime']:.6f}",
        "Validation_Runtime_Seconds": f"{state['validation_runtime'] + validation_wall:.6f}",
        "Evaluations": state["evaluations"], "Seeds_Completed": state["seeds_completed"],
        "Variables": state["variables"], "Clauses_or_Constraints": state["clauses"],
        "SAT_Calls": state["sat_calls"],
        "SAT_Conflicts": state["solver_stats"].get("conflicts", 0),
        "SAT_Decisions": state["solver_stats"].get("decisions", 0),
        "SAT_Propagations": state["solver_stats"].get("propagations", 0),
        "Timeout_Seconds": timeout,
        "Witness_JSON": json.dumps([[repr(v), label] for v, label in state["labels"].items()]),
        "_labels": dict(state["labels"]),
        "_error": state["error_info"],
    }


def run(output, *, timeout, methods, max_instances, resume=False):
    graphs, manifest_hash = _read_manifest(MANIFEST)
    if max_instances is not None:
        graphs = graphs[:max_instances]
    tasks = len(graphs) * len(PAIRS)
    observations = tasks * len(methods)
    config = {
        "study": "incremental-sat-min-ub-v1", "manifest": str(MANIFEST.relative_to(ROOT)),
        "manifest_sha256": manifest_hash, "cohort_graph_count": len(graphs),
        "graph_parameter_instances": tasks, "methods": list(methods),
        "pairs": [list(pair) for pair in PAIRS], "per_method_wall_limit_seconds": timeout,
        "wall_limit_scope": "one hard end-to-end wall cap per graph/parameter/method, including shared greedy incumbent generation, witness validation, solver/model construction, and search",
        "sat_backend": "CaDiCaL195", "sat_original_strategy": "hybrid",
        "sat_incremental_strategy": "incremental", "ilp": "Gurobi assignment; Threads=1, zero MIP gap",
        "ga": GA_CONFIG, "heuristic_witnesses_independently_validated": True,
        "seed_policy": "fixed seeds 0..9; 1000 evaluations per completed seed",
        "cohort_note": "repository certificate-validation cohort; not established as Appendix C and separate from historical 117-instance cohort",
        "limitation": "time-limited outputs are not proof traces; OPT claims rely on solver status and validated witnesses",
        "result_schema": "incremental-sat-observation-v2",
    }
    graphs_by_name = {name: (family, graph) for name, family, graph in graphs}

    def record_validator(row, witness):
        if not _incremental_record_valid(row, witness, graphs_by_name):
            return False
        expected = f"{row['Instance']}__h{row['h']}_k{row['k']}__{row['Method']}"
        if (row["Graph"] != expected or row["Manifest_SHA256"] != manifest_hash or
                row["Instance"] not in graphs_by_name or
                row["Family"] != graphs_by_name[row["Instance"]][0] or
                (int(row["h"]), int(row["k"])) not in PAIRS or row["Method"] not in methods):
            return False
        return True

    writer = BenchmarkWriter(output, fields=FIELDS, resume=resume, config=config,
        record_validator=record_validator, completion_validator=_incremental_row_complete,
        artifact_policy="incremental-sat-witness-v2")
    writer.log(f"Manifest: {manifest_hash}; {len(graphs)} graphs, {tasks} graph/(h,k) tasks, {observations} observations")
    writer.log(f"Maximum end-to-end method wall budget: {observations * timeout / 3600:.2f} hours; sequential execution")
    context = mp.get_context("spawn")
    for graph_index, (instance, family, graph) in enumerate(graphs, 1):
        for h, k in PAIRS:
            for method in methods:
                key = f"{instance}__h{h}_k{k}__{method}"
                if key in writer.completed:
                    continue
                row = _run_arm(instance, family, graph, h, k, method, timeout, context)
                row["Manifest_SHA256"] = manifest_hash
                labels = row.pop("_labels")
                row.pop("_error", None)
                row["Log_Reference"] = str(writer.log_path)
                witness_result = {field: row[field] for field in (
                    "Instance", "Family", "h", "k", "Method", "Status", "Solver_Outcome",
                    "Termination", "Span", "Best_Span", "Lower_Bound", "Optimality_Proven",
                    "Optimality_Source", "Feasible_Witness", "Valid_Witness", "Witness_JSON")}
                writer.append_with_witness(
                    row, key, SimpleNamespace(labels=labels, **witness_result), configuration=config)
                suffix = f" error={row['Error_Info']}" if row["Error_Info"] else ""
                writer.log(f"[{graph_index}/{len(graphs)}] {key}: {row['Status']} span={row['Span']} lb={row['Lower_Bound']} wall={row['Runtime_Seconds']}s{suffix}")
    pending = writer.recorded - writer.completed
    writer.log(f"Completed {len(writer.completed)} observations; retryable={len(pending)}; output={output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output("incremental_sat_comparison"))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--max-instances", type=int, help="development smoke subset; not the full cohort")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0 or (args.max_instances is not None and args.max_instances < 1):
        parser.error("timeout and max-instances must be positive")
    graphs, _ = _read_manifest(MANIFEST)
    count = min(args.max_instances, len(graphs)) if args.max_instances else len(graphs)
    observations = count * len(PAIRS) * len(args.methods)
    print(f"Plan: {count} graphs, {count * len(PAIRS)} graph/(h,k) instances, {observations} observations")
    print(f"Maximum sequential end-to-end budget: {observations * args.timeout / 3600:.2f} hours")
    print(f"Output: {args.output}")
    if not args.plan_only:
        run(args.output, timeout=args.timeout, methods=args.methods,
            max_instances=args.max_instances, resume=args.resume)


if __name__ == "__main__":
    main()
