"""Check the committed summaries; does not execute Helix or a solver."""
import csv
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def rows(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))

placement=rows('results/figure9/summary.csv')
assert len(placement)==6
for topology,expected in [('single',(1.19,1.99)),('distributed',(1.47,2.36))]:
    values={r['layout']:float(r['decode_throughput_tokens_s']) for r in placement if r['topology']==topology}
    for baseline,ratio in zip(['petals','swarm'],expected):
        assert math.isclose(values['helix']/values[baseline],ratio,abs_tol=.01)
schedule=rows('results/figure10/summary.csv')
assert len(schedule)==7
assert [float(r['decode_throughput_tokens_s']) for r in schedule if r['scheduler']=='maxflow']==[249.0,99.8]
pruning=rows('results/figure11/figure11a_throughput.csv')
assert len(pruning)==2 and pruning[0]['source']=='local official-parameter run'
assert 'precomputed' in pruning[1]['source']
for r in pruning:
    gain=(float(r['pruned_decode_tokens_s'])/float(r['unpruned_decode_tokens_s'])-1)*100
    assert math.isclose(gain,float(r['artifact_gain_pct']),abs_tol=.02)
milestones={r['event']:float(r['seconds']) for r in rows('results/figure12/figure12_milestones.csv')}
assert milestones['optimal_solution_first_found']==277
assert milestones['optimality_confirmed']==3802.88
print('PASS: Figures 9/10/11 summary arithmetic and Figure 12 milestones; 42-node precomputed provenance retained. No simulation or solver rerun.')
