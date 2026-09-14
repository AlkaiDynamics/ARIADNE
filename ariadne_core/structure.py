"""Conservative extraction: explicit notation, not an invented historical decoder."""
import re


PARTITION = re.compile(r'(?<![\w.])(?P<n>\d+)\s*(?:→|->|=)\s*(?P<d>\d+)\s*\+\s*(?P<r>\d+)(?![\w.])')
FACTOR = re.compile(r'(?<![\w.])(?P<a>\d+)\s*[×x*]\s*(?P<b>\d+)\s*(?:→|->|=)\s*(?P<n>\d+)(?![\w.])')
ARROW = re.compile(r'\b([A-Za-z_]+)\s*(?:→|->)\s*([A-Za-z_]+)\b')


def extract(line):
    results = []
    for m in PARTITION.finditer(line):
        n, d, r = (int(m[k]) for k in ('n', 'd', 'r'))
        # A nearby adjective is retained as a candidate cue, never certified function.
        active = bool(re.search(r'\bactive\b', line[m.end():m.end()+60], re.I))
        data = dict(full_set=n, displayed_set=d, residual_count=r,
                    residual_status='ACTIVE_CUE' if active else 'UNKNOWN',
                    residual_function=None, carrier=m[0], decoder=None,
                    abstraction_class='PARTITION', arithmetic_valid=n == d+r,
                    residual_role='UNVERIFIED')
        results.append(('PARTITION', f'PARTITION:k={r}', str(n), data))
    for m in FACTOR.finditer(line):
        a, b, n = (int(m[k]) for k in ('a', 'b', 'n'))
        results.append(('FACTOR', 'FACTOR', str(n), dict(factors=[a,b], total=n,
                       carrier=m[0], decoder=None, arithmetic_valid=a*b == n)))
    for m in ARROW.finditer(line):
        results.append(('DECODER_SHIFT', f'SHIFT:{m[1]}:{m[2]}', None,
                        dict(carrier=m[0], from_class=m[1], to_class=m[2], decoder=None)))
    for m in re.finditer(r'\b(\d+)\s+(?:vs\.?|versus)\s+(\d+)\b', line, re.I):
        results.append(('DISCREPANCY', 'DISCREPANCY', None,
                        dict(left=m[1], right=m[2], scope='UNKNOWN', conflict_proven=False)))
    if re.search(r'\b(missing|withheld|unpaired|untranslated|unknown|omitted)\b', line, re.I):
        results.append(('RESIDUAL', 'RESIDUAL', None, dict(raw=line, residual_count=None)))
    return results


def structured_record(record):
    """Typed JSON adapter. Input assertions are still machine-imported candidates."""
    if not isinstance(record, dict):
        raise ValueError('Each record must be an object')
    kind = record.get('kind')
    if kind == 'partition':
        fields = ('full_set','displayed_set','residual_count')
        if any(type(record.get(f)) is not int or record[f] < 0 for f in fields):
            raise ValueError('Partition counts must be nonnegative integers')
        data = dict(record)
        data['arithmetic_valid'] = record['full_set'] == record['displayed_set']+record['residual_count']
        data.setdefault('residual_function', None)
        data.setdefault('residual_status', 'UNKNOWN')
        data.setdefault('carrier', None); data.setdefault('decoder', None)
        return 'PARTITION', f"PARTITION:k={record['residual_count']}", str(record['full_set']), data
    if kind == 'claim':
        if not all(isinstance(record.get(f), str) and record[f] for f in ('subject','predicate','value','scope')):
            raise ValueError('Claims require subject, predicate, value and explicit scope strings')
        return 'CLAIM', 'CLAIM:'+record['predicate'], None, dict(record)
    raise ValueError('Unsupported typed record kind; retained as an extraction residual')
