#!/usr/bin/env python3
"""One local Warden. Run once or watch continuously. Python standard library only."""
from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import ariadne
from ariadne_core.engine import Warden
from ariadne_core.history import snapshot, recover, state_at, verify_history
from ariadne_core.store import event, verify_events
from ariadne_core.report import render


@contextmanager
def single_writer(root):
    """OS-released lock: process death cannot leave a stale PID lock."""
    path = Path(root)/'db/warden.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:
                raise RuntimeError('A Warden writer is already running') from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError('A Warden writer is already running') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(handle,fcntl.LOCK_UN)


def _prepare_field_census(con, w):
    """Run P0 before any Warden compile/reconnect/original synthesis."""
    from ariadne_core.field_census import (ensure_all, gate_status, install, process,
                                           queue_prior_art_leads, settings,
                                           sync_question_config)
    from ariadne_core.history import install_history
    install(con)
    # Field-census tables are additive and receive the same append-only row history.
    install_history(con)
    sync_question_config(con, ariadne.ROOT)
    ensure_all(con, w.config)
    con.commit()
    from ariadne_core.acquisition import acquire
    acquire(con, ariadne.ROOT, budget=max(4, len(settings(w.config)['providers'])))
    process(con, ariadne.ROOT, w.config)
    # Bibliographic index responses teach vocabulary and prior-art identity only.
    # Keep them out of E0 evidence even though the exact bytes remain in custody.
    for row in con.execute('''SELECT DISTINCT j.source_id FROM field_queries q
        JOIN acquisition_jobs j USING(job_id) WHERE j.source_id IS NOT NULL''').fetchall():
        con.execute('INSERT OR REPLACE INTO source_lanes VALUES(?,?,?)',
                    (row[0],'G0','P0 field-census bibliographic metadata; discovery guidance only'))
    gate=gate_status(con,w.config)
    if not gate['blocked']:
        for q in gate['questions']:
            if q['status'] in ('READY','SATURATED'):
                queue_prior_art_leads(con,q['question_id'],w.config.get('field_census_surface_k',12))
        # A metadata map is not the same as inspecting the surfaced scholarship.
        # Attempt acquisition of the top prior-art leads before ordinary synthesis.
        prior_pending=con.execute('''SELECT COUNT(DISTINCT j.job_id)
            FROM acquisition_links l JOIN acquisition_jobs j USING(job_id)
            WHERE l.relation='PRIOR_ART_LEAD'
              AND (j.status='QUEUED' OR (j.status='FETCH_FAILED' AND j.attempts<3))''').fetchone()[0]
        if prior_pending:
            gate=dict(gate)
            gate['blocked']=True
            gate['stage']='PRIOR_ART_ACQUISITION'
            gate['prior_art_pending']=prior_pending
            gate['blocked_questions']=[q for q in gate['questions'] if q['status'] in ('READY','SATURATED')]
    else:
        gate['stage']='FIELD_CENSUS'
    con.commit()
    return gate


def cycle(paths=None,budget=None):
    ariadne.ingest(paths or [])
    con = ariadne.connect()
    try:
        w = Warden(con,ariadne.ROOT)
        con.commit()
        gate=_prepare_field_census(con,w)
        if gate['blocked']:
            pending=con.execute("""SELECT COUNT(*) FROM acquisition_jobs
                WHERE status='QUEUED' OR (status='FETCH_FAILED' AND attempts<3)""").fetchone()[0]
            event(con,'P0_GATE_BLOCKED',gate.get('stage','FIELD_CENSUS'),{
                'blocked_questions':gate.get('blocked_questions',[]),
                'pending_acquisitions':pending,
                'rule':'RESEARCH_THE_RESEARCH_BEFORE_ORIGINAL_ANALYSIS'})
            con.commit()
            result=dict(executed=0,pending=pending,revision='P0_'+gate.get('stage','FIELD_CENSUS'),p0=gate)
            backup = snapshot(con,ariadne.ROOT)
            print(json.dumps(dict(result,snapshot=str(backup))),flush=True)
            return result
        result = w.run(budget)
        result['p0']=gate
        con.commit()
        report = render(w)
        backup = snapshot(con,ariadne.ROOT)
        print(json.dumps(dict(result,report=str(report),snapshot=str(backup))),flush=True)
        return result
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def watch(interval=30,budget=None,cycles=None,stop_event=None,mutex=None):
    if interval<=0 or (cycles is not None and cycles<1):
        raise ValueError('interval and cycles must be positive')
    stop = stop_event or threading.Event()
    def halt(*_):
        stop.set()
    old = {sig:signal.signal(sig,halt) for sig in (signal.SIGINT,signal.SIGTERM)} if threading.current_thread() is threading.main_thread() else {}
    previous,processed,pending = None,None,False
    count = 0
    try:
        while not stop.is_set() and (cycles is None or count<cycles):
            try:
                paths = [*ariadne.inbox_files(),*ariadne.CONFIG_DIR.glob('*.json')]
                current = tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in sorted(paths))
                # Two stable polls avoid booking half-written files. No-change idle
                # creates no new research versions or costly query work.
                import time
                with ariadne.connect() as con:
                    acquisition_due=bool(con.execute("SELECT 1 FROM acquisition_jobs WHERE status IN ('QUEUED','FETCH_FAILED') AND attempts<3 AND next_attempt<=? LIMIT 1",(time.time(),)).fetchone())
                if current == previous and (current != processed or pending or acquisition_due):
                    # Publish active work before a potentially slow network batch.
                    (ariadne.ARTIFACTS_DIR/'watch_status.json').write_text(
                        json.dumps(dict(status='PROCESSING',poll=count,pending=True)),
                        encoding='utf-8')
                    from contextlib import nullcontext
                    with (mutex if mutex is not None else nullcontext()):
                        result = cycle(budget=budget)
                    pending = result['pending']>0;processed=current
                previous=current
                health = dict(status='WAITING' if not pending else 'PROCESSING',poll=count,pending=pending)
            except Exception as exc:
                health = dict(status='ERROR_RETRY',error=str(exc),poll=count)
                print(json.dumps(health),file=sys.stderr,flush=True)
                try:
                    with ariadne.connect() as con:
                        event(con,'WATCH_ERROR','watch',health)
                except sqlite3.Error:
                    pass
            (ariadne.ARTIFACTS_DIR/'watch_status.json').write_text(json.dumps(health),encoding='utf-8')
            count += 1
            if cycles is None or count<cycles:
                stop.wait(interval)
    finally:
        for sig,handler in old.items():
            signal.signal(sig,handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    for command in ('run','ingest'):
        p=sub.add_parser(command);p.add_argument('paths',nargs='*');p.add_argument('--budget',type=int)
    p=sub.add_parser('watch');p.add_argument('--interval',type=float,default=30);p.add_argument('--budget',type=int);p.add_argument('--cycles',type=int)
    p=sub.add_parser('search');p.add_argument('query')
    sub.add_parser('report');sub.add_parser('snapshot');sub.add_parser('verify')
    p=sub.add_parser('trace');p.add_argument('node');p.add_argument('--hops',type=int,default=4)
    p=sub.add_parser('history');p.add_argument('--at',type=int,required=True)
    p=sub.add_parser('recover');p.add_argument('snapshot');p.add_argument('target')
    p=sub.add_parser('constraints');p.add_argument('file')
    p=sub.add_parser('acquire');p.add_argument('manifest',help='Path to text containing URLs/DOIs')
    p=sub.add_parser('question');p.add_argument('question');p.add_argument('--scope',default='');p.add_argument('--term',action='append',default=[])
    p=sub.add_parser('field-map');p.add_argument('question_id',nargs='?')
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=8765);p.add_argument('--interval',type=float,default=10)
    args=parser.parse_args(argv)
    if args.command=='recover':
        print(recover(args.snapshot,args.target));return 0
    with single_writer(ariadne.ROOT):
        ariadne.init_db()
        if args.command in ('run','ingest'):
            cycle(args.paths,args.budget);return 0
        if args.command=='watch':
            watch(args.interval,args.budget,args.cycles);return 0
        if args.command=='serve':
            from ariadne_core.server import serve
            serve(args.port,args.interval);return 0
        con=ariadne.connect()
        try:
            w=Warden(con,ariadne.ROOT)
            from ariadne_core.field_census import install
            from ariadne_core.history import install_history
            install(con);install_history(con)
            rev=con.execute("SELECT value FROM pipeline_state WHERE key='revision'").fetchone()
            w.revision=rev[0] if rev else 'UNCOMPILED'
            if args.command=='init':
                print(f'Warden ready: {ariadne.ROOT}')
            elif args.command=='search':
                hits,coverage=w.search(args.query);print(json.dumps(dict(hits=hits,coverage=coverage),ensure_ascii=False,indent=2))
            elif args.command=='report':
                print(render(w))
            elif args.command=='snapshot':
                print(snapshot(con,ariadne.ROOT))
            elif args.command=='verify':
                custody=all((ariadne.ROOT/r['custody_path']).exists() and ariadne.sha256_file(ariadne.ROOT/r['custody_path'])==r['sha256'] for r in con.execute('SELECT * FROM sources'))
                checks=dict(events=verify_events(con),history=verify_history(con),custody=custody,
                            sqlite=con.execute('PRAGMA integrity_check').fetchone()[0]=='ok',foreign_keys=not con.execute('PRAGMA foreign_key_check').fetchall())
                print(json.dumps(checks));return 0 if all(checks.values()) else 1
            elif args.command=='trace':
                print(json.dumps(w.trace(args.node,args.hops),indent=2))
            elif args.command=='history':
                print(json.dumps(state_at(con,args.at),ensure_ascii=False,indent=2))
            elif args.command=='constraints':
                from ariadne_core.algorithms import minimal_unsat_core
                clauses=json.loads(Path(args.file).read_text(encoding='utf-8'))
                result=dict(clauses=clauses,core_indices=minimal_unsat_core(clauses),scope='USER_DECLARED_PROPOSITIONAL_ONLY')
                event(con,'FORMAL_GUARD',str(Path(args.file)),result)
                print(json.dumps(result))
            elif args.command=='acquire':
                from ariadne_core.acquisition import queue_manifest
                count=queue_manifest(con,Path(args.manifest).read_text(encoding='utf-8'))
                print(json.dumps({'queued_pointers':count}))
            elif args.command=='question':
                from ariadne_core.field_census import register_question,ensure_initial_queries
                qid=register_question(con,args.question,args.scope,args.term)
                queued=ensure_initial_queries(con,qid,w.config)
                print(json.dumps({'question_id':qid,'field_queries_queued':queued}))
            elif args.command=='field-map':
                from ariadne_core.field_census import field_map
                ids=[args.question_id] if args.question_id else [r[0] for r in con.execute('SELECT question_id FROM research_questions ORDER BY created_at')]
                print(json.dumps([field_map(con,q,w.config.get('field_census_surface_k',12)) for q in ids],ensure_ascii=False,indent=2))
            con.commit()
        except BaseException:
            con.rollback();raise
        finally:
            con.close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())