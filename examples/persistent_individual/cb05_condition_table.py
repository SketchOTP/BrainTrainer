"""Predeclared balanced complete-action prediction panel condition schedule."""
import itertools
import json
from pathlib import Path
import random

SEEDS=tuple(range(700,716))
PHASES=('healthy','impaired','recovery')

def table():
    rows=[]
    combos=list(itertools.product((.8,.05),(0,1),(-1,1)))
    for seed in SEEDS:
        # Independent of side, hunger and parity: exactly four even and four
        # odd seed IDs for each assigned beneficial food type.
        good=(seed//2)%2
        for phase_index,phase in enumerate(PHASES):
            conditions=combos.copy()
            random.Random(2026110705+seed*13+phase_index).shuffle(conditions)
            for index,(hunger,food,side) in enumerate(conditions):
                rows.append({'seed':seed,'opportunity':phase_index*8+index,
                    'phase':phase,'hunger':hunger,'food_index':food,
                    'side':side,'beneficial_food_index':good})
    return rows

def verify(rows):
    if len(rows)!=384:raise ValueError('expected 384 scheduled opportunities')
    combos=set(itertools.product((.8,.05),(0,1),(-1,1)))
    for seed in SEEDS:
        selected=[x for x in rows if x['seed']==seed]
        if len(selected)!=24 or sorted(x['opportunity'] for x in selected)!=list(range(24)):
            raise ValueError('bad opportunity coverage')
        if {x['beneficial_food_index'] for x in selected}!={(seed//2)%2}:raise ValueError('inconsistent assignment')
        for phase in PHASES:
            phase_rows=[x for x in selected if x['phase']==phase]
            if len(phase_rows)!=8 or {(x['hunger'],x['food_index'],x['side']) for x in phase_rows}!=combos:
                raise ValueError('unbalanced phase')
    for parity in (0,1):
        for good in (0,1):
            if sum(1 for seed in SEEDS if seed%2==parity and (seed//2)%2==good)!=4:
                raise ValueError('value assignment coupled to parity')
    return True

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    rows=table();verify(rows);a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as out:json.dump({'schema':'cb05-condition-table-v1','rows':rows},out,indent=2);out.write('\n')
    print('verified',len(rows),'opportunities')

if __name__=='__main__':main()
