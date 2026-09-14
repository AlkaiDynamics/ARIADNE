"""Offline report: all rows retained; top-K is a view with visible counts."""
import html
import json
from .store import encoded


def render(warden):
    con,root = warden.con,warden.root
    def esc(x):
        return html.escape(str(x) if x is not None else 'UNKNOWN')
    def table(headers,rows):
        return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div>'
    all_branches = warden.ranked()
    k = warden.config['display_limit']
    def queue(rows):
        return table(['Branch / return address','Direction','State','Priority','Pareto layer','Protected','Why / stopping condition'],
            ((b['id'],b['direction'],b['status'],round(b['score'],3),b['pareto_layer'],bool(b['protected']),b['reason']) for b in rows))
    findings = con.execute("SELECT f.finding_id,f.kind,f.cell,f.data,p.source_id,p.locator,COALESCE(l.lane,'E0') lane FROM discovery_findings f JOIN passages p USING(passage_id) LEFT JOIN source_lanes l USING(source_id) ORDER BY f.finding_id").fetchall()
    historical=con.execute('SELECT finding_id,kind,version,data FROM findings WHERE finding_id NOT IN (SELECT finding_id FROM discovery_findings) ORDER BY finding_id').fetchall()
    challenges = con.execute('SELECT c.proposal_id,c.verdict,c.checks FROM challenges c JOIN proposals p USING(proposal_id) JOIN active_findings a ON p.left_id=a.finding_id JOIN active_findings b ON p.right_id=b.finding_id ORDER BY c.proposal_id').fetchall()
    profiles = con.execute('SELECT source_id,family,tradition,language,witness_class FROM source_profiles ORDER BY source_id').fetchall()
    scales = con.execute('SELECT level,signature,source_count,members,interpretation FROM scale_patterns ORDER BY level,pattern_id').fetchall()
    traces = con.execute('SELECT branch_id,finding_id,parent_id FROM branch_origins ORDER BY branch_id,finding_id,parent_id').fetchall()
    head = con.execute('SELECT MAX(revision) FROM state_versions').fetchone()[0]
    source_links = []
    for s in con.execute('SELECT source_id,custody_path,original_name FROM sources ORDER BY source_id'):
        from urllib.parse import quote
        source_links.append('<li><a href="../'+quote(s['custody_path'],safe='/')+'">'+esc(s['source_id']+' · '+s['original_name'])+'</a></li>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ARIADNE — Evidence and next searches</title>
    <style>body{background:#111722;color:#e8eef6;font:15px/1.5 system-ui;margin:0}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:36px;margin-bottom:0}h2{margin-top:32px}a{color:#92daca}small,p{color:#b8c5d4}.notice{padding:16px;border-left:4px solid #edc978;background:#1e2938}.scroll{overflow:auto;max-height:600px;border:1px solid #354456}table{border-collapse:collapse;width:100%}th,td{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #354456;max-width:650px;overflow-wrap:anywhere}th{position:sticky;top:0;background:#263549}details{margin:16px 0}summary{cursor:pointer;padding:10px;background:#263549}code{color:#edc978}</style><main>
    <h1>ARIADNE</h1><p>Preserve → detect residuals → remember threads → reconnect → rank the next search</p>
    <div class="notice">All automated connections remain MACHINE_PREDICTION. Priority measures investigation value, not truth. UNKNOWN controls remain unknown. Banking concerns local search yield; open-world coverage is unknown.</div>'''
    page += f'<p>State revision {head} · Corpus {esc(getattr(warden,"revision","not compiled"))} · {len(findings)} findings · {len(all_branches)} retained branches</p>'
    page += f'<h2>Where to look next</h2><p>Showing K={min(k,len(all_branches))} of N={len(all_branches)}. All other branches remain below and in the JSON export.</p>'+queue(all_branches[:k])
    page += '<details><summary>Show all retained branches</summary>'+queue(all_branches)+'</details>'
    page += '<h2>Kitchen: connections under challenge</h2>'+table(['Proposal','Verdict','Checks'],challenges)
    page += '<h2>Multiscale discovery</h2><p>Exact → proportional → operator family → graph neighborhood. Recurrence is a search cue, not a fractal or historical proof.</p>'+table(['Scale','Signature','Sources','Members','Status'],scales)
    page += '<h2>Current evidence and guidance records</h2>'+table(['Finding','Kind','Cell','Typed fields','Source','Location','Lane'],findings)
    page += f'<details><summary>Superseded extraction versions: {len(historical)} retained</summary>'+table(['Finding','Kind','Implementation','Fields'],historical)+'</details>'
    page += '<details><summary>Source profiles and original custody files</summary>'+table(['Source','Declared family','Tradition','Language','Witness class'],profiles)+'<ul>'+''.join(source_links)+'</ul></details>'
    page += '<details><summary>All breadcrumbs and return paths</summary>'+table(['Branch','Evidence anchor','Parent branch or scale pattern'],traces)+'</details>'
    page += '<p>Full exports: <a href="pipeline_state.json">pipeline_state.json</a> · <a href="neurite_notes.md">Neurite notes</a>. Historical snapshots are in artifacts/snapshots.</p></main></html>'
    directory = root/'artifacts';directory.mkdir(parents=True,exist_ok=True)
    path = directory/'latest_report.html'
    temporary = path.with_suffix('.tmp');temporary.write_text(page,encoding='utf-8');temporary.replace(path)
    export = dict(state_revision=head,branches=all_branches,findings=[dict(r) for r in findings],
                  challenges=[dict(r) for r in challenges],scale_patterns=[dict(r) for r in scales],return_paths=[dict(r) for r in traces])
    (directory/'pipeline_state.json').write_text(encoded(export),encoding='utf-8')
    from .fractal import export_neurite
    export_neurite(con,directory/'neurite_notes.md')
    return path
