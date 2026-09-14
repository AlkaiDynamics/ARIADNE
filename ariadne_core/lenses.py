"""Optional attention lenses. Their outputs never adjudicate evidence."""
from .store import encoded, event, identity


def run_multiscale(warden):
    from .fractal import multiscale
    con = warden.con
    name = 'NEURITE_INSPIRED_MULTISCALE'
    parameters = dict(enabled=warden.config['multiscale_enabled'],
                      role='ATTENTION_ONLY', evidence_authority=False,
                      scope='CURRENT_E0_TYPED_GRAPH',
                      limitation='Recurrence does not validate fractality or the overarching theory')
    run_id = identity('LENS',name,warden.revision,warden.implementation_id,parameters)
    prior = con.execute('SELECT status FROM lens_runs WHERE run_id=?',(run_id,)).fetchone()
    if prior:
        return prior[0]
    state = con.execute('SELECT COALESCE(MAX(revision),0) FROM state_versions').fetchone()[0]
    status, detail = 'DISABLED', dict(reason='Optional lens disabled; baseline discovery retained')
    if parameters['enabled']:
        con.execute('SAVEPOINT attention_lens')
        try:
            added = multiscale(warden)
        except Exception as exc:
            # Roll back this optional pass, including its partial graph/history
            # writes. Prior source custody and baseline connections survive.
            con.execute('ROLLBACK TO attention_lens')
            status, detail = 'FAILED', dict(error_type=type(exc).__name__,error=str(exc),
                                           reason='Lens failed; baseline discovery continues')
        else:
            status, detail = 'COMPLETED', dict(new_patterns=added,
                                              interpretation='UNVALIDATED_SEARCH_CUES')
        finally:
            con.execute('RELEASE attention_lens')
    con.execute('INSERT INTO lens_runs VALUES(?,?,?,?,?,?,?,?,?)',
                (run_id,name,warden.implementation_id,warden.revision,warden.config_hash,
                 state,encoded(parameters),status,encoded(detail)))
    event(con,'ATTENTION_LENS',run_id,dict(status=status,parameters=parameters,detail=detail))
    return status
