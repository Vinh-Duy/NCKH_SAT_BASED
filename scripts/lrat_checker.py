"""Check the RUP-only fragment of ASCII LRAT, without a SAT library.

Positive hint IDs specify the complete unit-propagation chain for each new
clause. RAT hints (negative IDs) are deliberately unsupported. An acceptance
requires a derived empty clause; all graph-to-CNF reconstruction happens in
the calling audit. This implementation is tested, not formally verified.
"""
import gzip
from pathlib import Path


def verify_lines(formula, lines):
    clauses = {}
    for index, clause in enumerate(formula, 1):
        if any(type(lit) is not int or lit == 0 for lit in clause):
            raise ValueError('invalid initial literal')
        clauses[index] = tuple(dict.fromkeys(clause))
    last_id = len(formula)
    additions = hints_checked = 0
    for line_number, line in enumerate(lines, 1):
        tokens = line.split()
        if not tokens or tokens[0] == 'c':
            continue
        if len(tokens) < 3:
            raise ValueError(f'malformed LRAT line {line_number}')
        index = int(tokens[0])
        if tokens[1] == 'd':
            removed = [int(t) for t in tokens[2:]]
            if not removed or removed[-1] != 0 or any(i <= 0 for i in removed[:-1]):
                raise ValueError('invalid deletion')
            for identifier in removed[:-1]:
                clauses.pop(identifier, None)
            continue
        if index <= last_id:
            raise ValueError('addition IDs must strictly increase')
        values = [int(t) for t in tokens[1:]]
        if values.count(0) != 2 or values[-1] != 0:
            raise ValueError('an addition requires a clause and hints terminated by zero')
        separator = values.index(0)
        proposed = tuple(dict.fromkeys(values[:separator]))
        hints = values[separator + 1:-1]
        if any(i <= 0 for i in hints):
            raise ValueError('only positive RUP hints are supported')
        assignment = {}
        contradiction = False
        for lit in proposed:
            value = lit < 0
            if abs(lit) in assignment and assignment[abs(lit)] != value:
                contradiction = True
            assignment[abs(lit)] = value
        for identifier in hints:
            if identifier not in clauses:
                raise ValueError('hint references a missing or deleted clause')
            if contradiction:
                break
            pending = []
            for lit in clauses[identifier]:
                if abs(lit) not in assignment:
                    pending.append(lit)
                elif assignment[abs(lit)] == (lit > 0):
                    raise ValueError('hint is satisfied rather than unit or conflicting')
            hints_checked += 1
            if not pending:
                contradiction = True
            elif len(pending) == 1:
                assignment[abs(pending[0])] = pending[0] > 0
            else:
                raise ValueError('hint is not unit')
        if not contradiction:
            raise ValueError(f'RUP hints do not establish conflict at line {line_number}')
        additions += 1
        if not proposed:
            return dict(verified=True, additions=additions, hints_checked=hints_checked)
        clauses[index] = proposed
        last_id = index
    raise ValueError('proof has no derived empty clause')


def verify_file(formula, path):
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='ascii') as stream:
        return verify_lines(formula, stream)
