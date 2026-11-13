"""Predeclared seed-paired CB-04 fresh completion and expenditure analysis."""
import argparse,collections,hashlib,json,random,statistics
from pathlib import Path


def bootstrap(values):
 rng=random.Random(20261107);n=len(values)
 draws=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
 return [draws[249],draws[9749]]


def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 rows=[json.loads(line) for line in a.raw.read_text().splitlines()]
 if sorted(r['seed'] for r in rows)!=list(range(500,516)):raise ValueError('expected 16 unique seeds')
 cases={(c['seed'],c['scenario'],c['condition']):c for row in rows for c in row['cases']}
 expected={(s,sc,c) for s in range(500,516) for sc in ('sustained','intermittent') for c in ('normal','effort','baseline','candidate')}
 if len(cases)!=128 or set(cases)!=expected or sum(len(r['cases']) for r in rows)!=128:raise ValueError('incomplete or duplicate fresh cases')
 metrics={};counts={}
 def values(sc,condition,phase,metric,late=False):
  result=[]
  for seed in range(500,516):
   caseslice=[v for v in cases[(seed,sc,condition)]['results'] if v['phase']==phase]
   if len(caseslice)!=8:raise ValueError('invalid phase length')
   if late:caseslice=caseslice[-4:]
   result.append(sum(metric(v) for v in caseslice)/len(caseslice))
  return result
 def delta(sc,phase,metric,left,right,late=False):
  a=values(sc,left,phase,metric,late);b=values(sc,right,phase,metric,late)
  d=[x-y for x,y in zip(a,b)]
  return {'mean':statistics.mean(d),'ci95':bootstrap(d),'seed_differences':d,'left_mean':statistics.mean(a),'right_mean':statistics.mean(b)}
 def complete(v):return int(v['completed'])
 def cost(v):return v['reserve_cost']
 for sc in ('sustained','intermittent'):
  for phase in ('healthy','impaired','recovery'):
   metrics[f'{sc}_{phase}_completion_candidate_minus_baseline']=delta(sc,phase,complete,'candidate','baseline')
   for condition in ('normal','effort','baseline','candidate'):
    grouped=[v for seed in range(500,516) for v in cases[(seed,sc,condition)]['results'] if v['phase']==phase]
    count=collections.Counter()
    for v in grouped:
     count['opportunities']+=1;count['completed']+=v['completed'];count['no_request']+=not v['requested_eat'];count['contact']+=v['contact']
     count['timeout']+=v['timed_out'];count['interrupted']+=v['interruptions']>0;count['blocked']+=v['blocked'];count['exhausted']+=v['exhausted']
     count['unsupported_choice_ticks']+=sum(t['event']['outcome']['status']=='unavailable-action' for t in v['events'])
     count['motor_measured_failures']+=sum(m['motor_success'] is False for m in v['motor']);count['motor_unknown_blocks']+=sum(m['motor_success'] is None for m in v['motor'])
    times=[v['ticks'] for v in grouped if v['completed']]
    counts[f'{sc}_{phase}_{condition}']={**count,'mean_total_cost_per_opportunity':statistics.mean(v['reserve_cost'] for v in grouped),
       'mean_completion_ticks_conditional':statistics.mean(times) if times else None,
       'opportunity_costs':[v['reserve_cost'] for v in grouped]}
 metrics['sustained_impaired_completion_candidate_minus_normal']=delta('sustained','impaired',complete,'candidate','normal')
 metrics['sustained_late_recovery_cost_candidate_minus_baseline']=delta('sustained','recovery',cost,'candidate','baseline',True)
 metrics['healthy_cost_candidate_minus_baseline']=delta('sustained','healthy',cost,'candidate','baseline')
 healthy_equal=all(cases[(s,'sustained',c)]['results'][:8]==cases[(s,'intermittent',c)]['results'][:8] for s in range(500,516) for c in ('normal','effort','baseline','candidate'))
 preservation={f'{sc}_{phase}':metrics[f'{sc}_{phase}_completion_candidate_minus_baseline']['ci95'][0]>=-.02 for sc in ('sustained','intermittent') for phase in ('healthy','impaired','recovery')}
 imp=metrics['sustained_impaired_completion_candidate_minus_normal'];late=metrics['sustained_late_recovery_cost_candidate_minus_baseline'];healthy=metrics['healthy_cost_candidate_minus_baseline']
 gates={'completion_preservation':preservation,'impaired_improvement':imp['mean']>=.1 and imp['ci95'][0]>0,
        'late_cost':late['right_mean']>0 and late['left_mean']<=.9*late['right_mean'] and late['ci95'][1]<0,
        'healthy_cost':healthy_equal and healthy['right_mean']>0 and healthy['left_mean']<=1.05*healthy['right_mean'] and healthy['ci95'][1]<=.05*healthy['right_mean']}
 result={'seeds':list(range(500,516)),'cases':128,'metrics':metrics,'counts':counts,'healthy_phase_identical_between_schedules':healthy_equal,'gates':gates,
         'all_gates_pass':all(preservation.values()) and all(gates[k] for k in ('impaired_improvement','late_cost','healthy_cost')),
         'cpu_seconds_sum':sum(r['cpu_seconds'] for r in rows),'elapsed_case_seconds_sum':sum(r['elapsed_seconds'] for r in rows),
         'max_worker_peak_kib':max(r['peak_worker_kib'] for r in rows),'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest()}
 with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'cases':result['cases'],'gates':gates,'all_gates_pass':result['all_gates_pass'],'metrics':metrics},indent=2))

if __name__=='__main__':main()
