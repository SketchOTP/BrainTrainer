"""Speculative *copy-only* preview of the next passive action forecast.

The caller must compare the state token before the real tick and invalidate the
preview on any intervening change.  No clone outcome or clone state is returned.
This does not change tick ordering or mutate the true brain, body, or model.
"""
import hashlib
import json
from complete_action_prediction import observed_snapshot,restore_observed


def state_token(host,observer,*,opportunity_deadline=None):
    data=json.dumps({'snapshot':observed_snapshot(host,observer),'opportunity_deadline':opportunity_deadline},sort_keys=True,separators=(',',':'),allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def preview_next_action(host,observer,*,opportunity_deadline=None):
    snapshot=observed_snapshot(host,observer)
    token=state_token(host,observer,opportunity_deadline=opportunity_deadline)
    shadow,shadow_observer=restore_observed(snapshot)
    result=shadow_observer.tick(shadow,opportunity_deadline=opportunity_deadline)
    forecasts=[x for x in result['action_prediction_events'] if x['kind']=='forecast']
    if len(forecasts)>1:raise RuntimeError('multiple forecasts in a single tick')
    return {'state_token':token,'forecast':forecasts[0] if forecasts else None}
