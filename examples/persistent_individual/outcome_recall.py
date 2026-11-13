"""Experience-derived sensory suggestions, not motor commands or hidden value access.

The ledger owns history. This incremental projection can be rebuilt from it and
has no separately editable checkpoint. Numeric valuation and cue strength are
explicit authored mechanisms; preferences depend on completed attributed outcomes.
"""
from creature_brain.benchmark.contract import ChosenAction, Outcome, attributed_adjustment

MODEL = 'attributed-outcome-recall-v1'
RELIEF_RECHECK_TICKS = 16


class OutcomeRecall:
    def __init__(self):
        self.effects = {}
        self.review_relief = False

    def observe(self, record):
        kind, event = record['kind'], record['payload']
        if kind=='implementation-change' and event.get('operation')=='enable-development':
            from creature_brain.development import supports
            self.review_relief=supports(event['model'],'relief_review')
            return
        if kind != 'experience':
            return
        action = ChosenAction(**event['executed_action'])
        outcome = Outcome(**event['outcome'])
        adjustment = attributed_adjustment(action, outcome)
        if adjustment is None:
            return
        seen = next((o for o in event['observation']['objects'] if o['identity'] == action.target), None)
        if seen is None:
            return
        key = (seen['type_id'], seen['category'], action.action)
        row = self.effects.setdefault(key, {'count': 0, 'mean_relief': 0., 'last_event': None})
        if self.review_relief:
            hunger=event['observation'].get('hunger')
            if adjustment < -1e-9:
                row['nonrelief_evidence']=[];row.pop('retry_after',None)
            elif abs(adjustment)<=1e-9 and type(hunger) in (int,float) and hunger>.05 and row['mean_relief']>0:
                evidence=row.setdefault('nonrelief_evidence',[]);evidence.append(record['sequence']);del evidence[:-3]
                if len(evidence)>=3:row['retry_after']=event['time']+RELIEF_RECHECK_TICKS
        row['count'] += 1
        # Recency weighting allows later observed reversals to revise expectation.
        rate = max(.2, 1. / row['count'])
        row['mean_relief'] += rate * (-adjustment - row['mean_relief'])
        row['last_event'] = record['sequence']

    def intention(self, observation):
        """Return a grounded recall or help request from present need and history."""
        if observation.hunger <= .05:
            return None
        candidates = []
        for obj in observation.objects:
            for (type_id, category, action), row in self.effects.items():
                if (obj.type_id != type_id or obj.category != category or
                    action not in obj.available_actions or row['mean_relief'] <= 0):
                    continue
                if self.review_relief and observation.time<row.get('retry_after',0):continue
                value = row['mean_relief'] * observation.hunger / (1 + .08 * obj.distance)
                candidates.append((value, obj.identity, category, action, row))
        if candidates:
            _, target, category, action, row = max(candidates, key=lambda x: (x[0], x[1], x[3]))
            recheck=self.review_relief and 'retry_after' in row
            return {'kind': 'recall', 'model': MODEL, 'target': target,
                    'category': category, 'action': action, 'strength': .7,
                    'reason': 'observed-need-relief', 'observations': row['count'],
                    'expected_relief': row['mean_relief'], 'evidence_event': row['last_event'],
                    'uncertainty': 'recent-relief-failed; bounded-recheck' if recheck else 'limited-observations' if row['count'] < 5 else 'context-limited',
                    **({'recheck':True,'nonrelief_evidence':list(row['nonrelief_evidence'])} if recheck else {})}
        return None
