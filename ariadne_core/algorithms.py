"""Small, bounded classical algorithms; scores are not probabilities of truth."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter, deque
from itertools import product


def normalize(text):
    # NFC preserves script distinctions; transliteration is explicit configuration.
    return unicodedata.normalize("NFC", text).casefold()


def tokens(text):
    return re.findall(r"\w+", normalize(text))


def grams(text, n=3):
    text = " ".join(tokens(text))
    return {text[i:i+n] for i in range(max(1, len(text)-n+1))} if text else set()


def jaccard(a, b):
    return len(a & b) / len(a | b) if a or b else 0.0


def osa_distance(a, b):
    """Optimal string alignment distance (restricted Damerau-Levenshtein)."""
    d = [list(range(len(b)+1))]
    for i, x in enumerate(a, 1):
        row = [i] + [0]*len(b)
        for j, y in enumerate(b, 1):
            row[j] = min(d[-1][j]+1, row[j-1]+1, d[-1][j-1]+(x != y))
            if i > 1 and j > 1 and x == b[j-2] and a[i-2] == y:
                row[j] = min(row[j], d[-2][j-2]+1)
        d.append(row)
    return d[-1][-1]


class AhoCorasick:
    """Trie + failure links for simultaneous alias/torch term matching."""
    def __init__(self, terms):
        self.next, self.fail, self.out = [{}], [0], [[]]
        for term in sorted(set(terms)):
            state = 0
            for ch in normalize(term):
                if ch not in self.next[state]:
                    self.next[state][ch] = len(self.next)
                    self.next.append({}); self.fail.append(0); self.out.append([])
                state = self.next[state][ch]
            if term:
                self.out[state].append(term)
        q = deque(self.next[0].values())
        while q:
            state = q.popleft()
            for ch, child in self.next[state].items():
                q.append(child)
                f = self.fail[state]
                while f and ch not in self.next[f]:
                    f = self.fail[f]
                self.fail[child] = self.next[f].get(ch, 0)
                self.out[child] += self.out[self.fail[child]]

    def find(self, text):
        text, state, found = normalize(text), 0, set()
        for i, ch in enumerate(text):
            while state and ch not in self.next[state]:
                state = self.fail[state]
            state = self.next[state].get(ch, 0)
            for term in self.out[state]:
                start = i+1-len(normalize(term))
                if (start == 0 or not text[start-1].isalnum()) and (i+1 == len(text) or not text[i+1].isalnum()):
                    found.add(term)
        return sorted(found)


def tfidf_scores(query, documents):
    counts = [Counter(tokens(t)) for t in documents]
    df = Counter(t for c in counts for t in c)
    idf = {t: math.log((1+len(counts))/(1+n))+1 for t, n in df.items()}
    def vector(c):
        return {t: (1+math.log(n))*idf.get(t, 1) for t, n in c.items()}
    q = vector(Counter(tokens(query)))
    qnorm = math.sqrt(sum(x*x for x in q.values()))
    scores = []
    for c in counts:
        v = vector(c)
        den = qnorm*math.sqrt(sum(x*x for x in v.values()))
        scores.append(sum(x*v.get(t, 0) for t, x in q.items())/den if den else 0)
    return scores


def minhash(items, size=32):
    """Seeded reproducible signatures; a candidate filter, never an identity merge."""
    return tuple(min((int.from_bytes(hashlib.blake2b(f"{i}:{x}".encode(), digest_size=8).digest(), "big")
                      for x in items), default=0) for i in range(size))


def rrf(rankings, k=60):
    scores = Counter()
    for ranking in rankings:
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] += 1/(k+rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def pareto_layers(items, objectives):
    remaining = list(items)
    result, layer = {}, 0
    while remaining:
        front = [a for a in remaining if not any(
            all(b[k] >= a[k] for k in objectives) and any(b[k] > a[k] for k in objectives)
            for b in remaining if b is not a)]
        for a in front:
            result[a['id']] = layer
        ids = {a['id'] for a in front}
        remaining = [a for a in remaining if a['id'] not in ids]
        layer += 1
    return result


def ucb(reward, pulls, total):
    return reward/pulls + math.sqrt(2*math.log(total+1)/pulls) if pulls else 2.0


def missing_mass(observations):
    """Descriptive singleton fraction; adaptive retrieval violates IID assumptions."""
    c = Counter(observations)
    return sum(v == 1 for v in c.values())/sum(c.values()) if c else None


def anti_unify(a, b, bindings=None):
    """First-order syntactic LGG. Generalizations are proposals, not semantic rules."""
    bindings = {} if bindings is None else bindings
    if a == b:
        return a
    if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b) and a[0] == b[0]:
        return (a[0], *(anti_unify(x, y, bindings) for x, y in zip(a[1:], b[1:])))
    key = (repr(a), repr(b))
    if key not in bindings:
        bindings[key] = f"?v{len(bindings)}"
    return bindings[key]


def consistent_environments(environments, nogoods):
    """ATMS-style subset filter; rejected environments remain in the caller's ledger."""
    return [e for e in environments if not any(set(n) <= set(e) for n in nogoods)]


def minimal_unsat_core(clauses, max_variables=12, max_clauses=64):
    """Deletion-minimal propositional core, NOT minimum-cardinality / full MaxSAT.

    Signed integer literals. Exponential but explicitly bounded. Call only on
    user-declared formal constraints, never on inferred natural-language truth.
    """
    if len(clauses) > max_clauses:
        raise ValueError("formal constraint clause budget exceeded")
    if any(type(x) is not int or x == 0 for c in clauses for x in c):
        raise ValueError("literals must be nonzero integers")
    variables = sorted({abs(x) for c in clauses for x in c})
    if len(variables) > max_variables:
        raise ValueError("formal constraint variable budget exceeded")
    def sat(cs):
        for vals in product((False, True), repeat=len(variables)):
            world = dict(zip(variables, vals))
            if all(any(world[abs(x)] == (x > 0) for x in c) for c in cs):
                return True
        return False
    if sat(clauses):
        return []
    core = list(range(len(clauses)))
    for i in list(core):
        other = [j for j in core if j != i]
        if not sat([clauses[j] for j in other]):
            core = other
    return core
