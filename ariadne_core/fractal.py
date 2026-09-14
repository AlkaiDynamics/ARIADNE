"""Neurite-inspired multiscale navigation, without fractal-to-truth inference.

Three deterministic abstraction scales retain all members: literal cardinality,
proportional partition, and typed operator. WL neighborhood refinement looks for
repeated local graph shape. Neither is a proof of fractality or transmission.
"""
import json
from collections import defaultdict
from fractions import Fraction
from .store import encoded, identity, event


def multiscale(warden):
    con = warden.con
    groups = defaultdict(list)
    findings = con.execute('SELECT * FROM active_findings ORDER BY finding_id').fetchall()
    labels = {f['finding_id']:f['kind'] for f in findings}
    neighbors = defaultdict(list)
    for e in con.execute("SELECT * FROM graph_edges WHERE relation IN ('STRUCTURAL_ALIGNMENT','SCOPED_CONFLICT') ORDER BY edge_id"):
        if e['src'] not in labels or e['dst'] not in labels:
            continue
        neighbors[e['src']].append((e['relation'],'OUT',e['dst']))
        neighbors[e['dst']].append((e['relation'],'IN',e['src']))
    for f in findings:
        if f['kind'] != 'PARTITION':
            continue
        d = json.loads(f['data'])
        if not d.get('arithmetic_valid') or not d['full_set']:
            continue
        member = f['finding_id']
        groups[(0,encoded(['PARTITION',d['full_set'],d['displayed_set'],d['residual_count']]))].append(member)
        groups[(1,encoded(['PARTITION',str(Fraction(d['displayed_set'],d['full_set'])),str(Fraction(d['residual_count'],d['full_set']))]))].append(member)
        groups[(2,'PARTITION:N=D+R')].append(member)
    # Two WL rounds, bounded by an already materialized graph. Hash collisions do
    # not establish isomorphism; keep signatures as proposals with exact members.
    for radius in (1,2):
        labels = {node:identity('WL',labels[node],sorted((rel,direction,labels.get(other,'UNKNOWN')) for rel,direction,other in neighbors[node])) for node in sorted(labels)}
        for node,label in labels.items():
            if neighbors[node]:
                groups[(2+radius,label)].append(node)
    added = 0
    for (level,signature),members in sorted(groups.items()):
        if len(members)<2:
            continue
        source_count = len({warden.get_finding(m)['source_id'] for m in members})
        pid = identity('SCALE',level,signature,sorted(members))
        cur = con.execute('INSERT OR IGNORE INTO scale_patterns VALUES(?,?,?,?,?,?)',
            (pid,level,signature,encoded(sorted(members)),source_count,'EXPLORATORY_RECURRENCE_NOT_FRACTAL_PROOF'))
        if cur.rowcount:
            for m in members:
                warden.edge(m,pid,'SCALE_MEMBER',{'level':level,'signature':signature})
            # Each newly recurring pattern re-exposes its exact evidence anchors.
            for m in members:
                warden.spawn(m,parent=pid,depth=0)
            event(con,'FRACTAL_GUARD',pid,{'level':level,'members':members,'source_count':source_count})
            added += 1
    return added


def export_neurite(con,path):
    """Plain Zettelkasten text with default Neurite ## / [[...]] links."""
    parts = ['## ARIADNE research view\nMachine proposals; original evidence outranks this view.\n']
    for f in con.execute('SELECT f.*,p.source_id,p.locator,p.text FROM active_findings f JOIN passages p USING(passage_id) ORDER BY finding_id'):
        # Avoid corpus-supplied note delimiters or references becoming synthetic links.
        raw = f['text'].replace('[[','［［').replace(']]','］］')
        raw = '\n'.join('> '+line for line in raw.splitlines())
        links = [r[0] for r in con.execute('SELECT dst FROM graph_edges WHERE src=? AND relation IN (\'STRUCTURAL_ALIGNMENT\',\'SCOPED_CONFLICT\') ORDER BY dst',(f['finding_id'],))]
        parts.append(f"## {f['finding_id']}\n{f['kind']} · MACHINE_PREDICTION\nSource: {f['source_id']} · {f['locator']}\n{raw}\n"+' '.join(f'[[{x}]]' for x in links)+'\n')
    path.write_text('\n'.join(parts),encoding='utf-8')
    return path
