"""Small, solver-independent RUP checker using only the standard library.

Every addition must follow by reverse unit propagation. Deletions can be
honored or ignored: previously verified RUP clauses remain logical consequences
of the original formula. This is sound for RUP, and is not a general RAT checker.
The checker must reach a verified empty clause before accepting a proof.
"""
from collections import defaultdict, deque
import gzip
from pathlib import Path


class RupChecker:
    def __init__(self, formula):
        self.clauses = []
        self.watches = defaultdict(list)
        self.units = []
        self.known = set()
        self.multiplicity = defaultdict(int)
        self.indices = {}
        self.empty = False
        for clause in formula:
            self.add(clause)

    @staticmethod
    def normalize(clause):
        if any(type(lit) is not int or not lit for lit in clause):
            raise ValueError('clauses require nonzero integer literals')
        return list(dict.fromkeys(clause))

    def add(self, clause):
        clause = self.normalize(clause)
        key = frozenset(clause)
        self.multiplicity[key] += 1
        if key in self.known or any(-lit in key for lit in key):
            return
        self.known.add(key)
        if not clause:
            self.empty = True
        elif len(clause) == 1:
            self.units.append(clause[0])
        else:
            index = len(self.clauses)
            self.indices[key] = index
            self.clauses.append(clause)
            self.watches[clause[0]].append(index)
            self.watches[clause[1]].append(index)

    def delete(self, clause):
        key = frozenset(self.normalize(clause))
        if key not in self.known:
            return
        self.multiplicity[key] -= 1
        if self.multiplicity[key]:
            return
        self.known.remove(key)
        if not key:
            self.empty = False
        elif len(key) == 1:
            self.units.remove(next(iter(key)))
        else:
            self.clauses[self.indices.pop(key)] = None

    def is_rup(self, clause):
        clause = self.normalize(clause)
        if self.empty:
            return True
        assigned, pending = {}, deque()

        def assign(literal):
            vertex, value = abs(literal), literal > 0
            if vertex in assigned:
                return assigned[vertex] == value
            assigned[vertex] = value
            pending.append(literal)
            return True

        for literal in [-lit for lit in clause] + self.units:
            if not assign(literal):
                return True
        while pending:
            false = -pending.popleft()
            watched = self.watches[false]
            index = 0
            while index < len(watched):
                clause_id = watched[index]
                current = self.clauses[clause_id]
                if current is None:
                    watched[index] = watched[-1]
                    watched.pop()
                    continue
                if current[0] == false:
                    current[0], current[1] = current[1], current[0]
                other = current[0]
                if assigned.get(abs(other)) == (other > 0):
                    index += 1
                    continue
                replacement = False
                for slot in range(2, len(current)):
                    literal = current[slot]
                    if abs(literal) not in assigned or assigned[abs(literal)] == (literal > 0):
                        current[1], current[slot] = current[slot], current[1]
                        watched[index] = watched[-1]
                        watched.pop()
                        self.watches[literal].append(clause_id)
                        replacement = True
                        break
                if replacement:
                    continue
                if not assign(other):
                    return True
                index += 1
        return False


def verify_lines(formula, lines, *, honor_deletions=False):
    checker = RupChecker(formula)
    additions = deletions = 0
    for line_number, line in enumerate(lines, 1):
        tokens = line.split()
        if not tokens or tokens[0] == 'c':
            continue
        deletion = tokens[0] == 'd'
        if deletion:
            tokens = tokens[1:]
        literals = [int(token) for token in tokens]
        if not literals or literals[-1] != 0 or 0 in literals[:-1]:
            raise ValueError(f'malformed proof line {line_number}')
        clause = literals[:-1]
        if deletion:
            if honor_deletions:
                checker.delete(clause)
            deletions += 1
            continue
        if not checker.is_rup(clause):
            raise ValueError(f'non-RUP addition at proof line {line_number}')
        additions += 1
        if not clause:
            return dict(verified=True, additions=additions, deletions=deletions,
                        honor_deletions=honor_deletions)
        checker.add(clause)
    raise ValueError('proof has no verified empty clause')


def verify_file(formula, path, *, honor_deletions=False):
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='ascii') as stream:
        return verify_lines(formula, stream, honor_deletions=honor_deletions)
