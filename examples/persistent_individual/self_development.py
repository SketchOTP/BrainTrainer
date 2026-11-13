"""Bounded evaluator for creature-requested executable practice changes.

Tests are branched worlds, not lived competence. The finite program language and
mandatory regressions are authored; newer brains learn test order from failures.
"""
from creature_brain.practice_policy import PracticePolicy
from creature_brain.development import supports

BASE_PROFILES=(('continuation',None,2),('switch','switch',2),
    ('counter','counter',2),('delayed-two','delayed-switch',2),
    ('delayed-three','delayed-switch',3),('inert','inert',2))
PROGRESS_PROFILES=(('progress-then-inert','delayed-switch',2),
                   ('progress-then-slower','delayed-switch',3))


def install(companion, policy, *, request_id, resume_goal=None):
    companion._append('implementation-change', {
        'operation':'install-practice-policy','actor':'creature-development',
        'request_id':request_id,'source':policy.source,'sha256':policy.sha256,
        'resume_goal':resume_goal})


def evaluation_plan(companion, request, *, use_memory=True):
    profiles=list(BASE_PROFILES)
    if request.get('regression_scope')=='progress-sensitive-practice-v1':
        profiles.extend(PROGRESS_PROFILES)
    adaptive=supports(companion._mind.version,'repeated_development')
    memory=companion._mind.curriculum.evaluation_memory if adaptive and use_memory else []
    failures={profile:sum(profile in row['failed_profiles'] for row in memory) for profile,_,_ in profiles}
    profiles.sort(key=lambda row:-failures[row[0]]) # Stable ties preserve declared order.
    return profiles,{'strategy':'prior-failure-first' if memory else 'declared-profile-order',
        'evidence_events':[row['event'] for row in memory],
        'failure_counts':failures,'required_profiles':[row[0] for row in profiles],
        'early_rejection':adaptive,'acceptance':'every required profile must pass'}


def evaluate(companion, request, *, use_evaluation_memory=True, use_retained_decisions=True):
    from continuing_companion import digest
    profiles,plan=evaluation_plan(companion,request,use_memory=use_evaluation_memory)
    retained_enabled=supports(companion._mind.version,'retained_continuations')
    if retained_enabled:plan['retained_decision_checks_enabled']=use_retained_decisions
    candidates=[]
    for specification in request['candidates']:
        policy=PracticePolicy(specification['source'])
        cases=[]
        retained=companion._mind.curriculum.retained_policy_checks(policy) if retained_enabled and use_retained_decisions else []
        retained_failure=any(case['candidate_would_stop'] for case in retained)
        prediction=None
        if supports(companion._mind.version,'stop_counterfactual'):
            counters=request['recorded_counters']
            prediction={'kind':'executable-counterfactual','evidence_event':request['evidence'][-1],
                'inputs':dict(counters),'candidate_sha256':policy.sha256,
                'candidate_would_stop':policy.should_stop(**counters),
                'original_stop':request['stop_decision'],
                'basis':'executing the candidate rule on recorded counters',
                'real_outcomes_added':0,'scope':'same recorded decision only; future benefit requires branch tests'}
        for profile,function,delay in profiles:
            if retained_failure or (prediction and prediction['candidate_would_stop']):break
            child=companion.fork(purpose=f"practice-policy evaluation: {profile}: {policy.sha256}")
            install(child,policy,request_id=request['request_id'],
                    resume_goal=request['goal_id'] if function is None else None)
            child._append('external-intervention',{'actor':'development-evaluator',
                'operation':'evaluation-control','automatic_improvement':False})
            if function is not None:
                for identity in ('object-0','object-1'):
                    child.place(identity,0,actor='development-evaluator',visible=False)
                child.configure_device('toy',function=function,delay=delay,
                    type_id=f'evaluation:{profile}',actor='development-evaluator')
                child.place('toy',child._host.position+.5,actor='development-evaluator')
            start=child.time
            goal=None;changed_environment=False
            for _ in range(32):
                if profile.startswith('progress-then-') and goal and goal['changes']==1 and not changed_environment:
                    child.configure_device('toy',function='inert' if profile=='progress-then-inert' else 'delayed-switch',
                        delay=4,type_id=f'evaluation:{profile}',actor='development-evaluator')
                    changed_environment=True
                child.tick(allow_improvement=False)
                goal=next((g for g in child._mind.curriculum.goals if
                    (g['id']==request['goal_id'] if function is None else g['type_id']==f'evaluation:{profile}')),None)
                if (goal is not None and goal['status']!='active' and
                    child._mind.curriculum.investigation_plan() is None):break
            if profile=='progress-then-inert':
                passed=bool(changed_environment and goal and goal['status']=='effect-unresolved-review-needed'
                            and goal['changes']==1 and goal['no_change_streak']<=4)
            else:
                passed=bool(goal and (goal['status']=='effect-unresolved-review-needed' and goal['trials']<=(3+goal['investigation']['plan']['additional_attempts'] if goal.get('investigation',{}).get('status')=='no-effect-within-budget' else 3)
                    if function=='inert' else goal['status']=='demonstrated-visible-effect'))
            snapshot=child.snapshot()
            cases.append({'profile':profile,'passed':passed,'ticks':child.time-start,
                'goal':goal,'lineage':snapshot['lineage'],
                'checkpoint_sha256':digest(snapshot),
                'test_events':snapshot['events'][len(companion._events):]})
            if not passed and plan['early_rejection']:break
        tested={c['profile'] for c in cases}
        entry={**specification,**policy.describe(),'cases':cases,
               'passed':not retained_failure and len(cases)==len(profiles) and all(c['passed'] for c in cases)}
        if plan['early_rejection']:
            entry.update(untested_profiles=[p[0] for p in profiles if p[0] not in tested],
                         coverage='complete' if len(cases)==len(profiles) else 'stopped-after-failed-regression')
        if prediction is not None:
            entry['stop_prediction']=prediction
            if prediction['candidate_would_stop']:
                entry['coverage']='rejected-by-recorded-stop-counterfactual'
        if retained_enabled:
            entry['retained_decision_checks']=retained
            if retained_failure:entry['coverage']='rejected-by-retained-continuation'
        candidates.append(entry)
    selected=next((c for c in candidates if c['passed']),None)
    report={'request_id':request['request_id'],'request':request,
        'origin':'own-practice-review','evidence_kind':'branched-tests',
        'candidates':candidates,'selected_sha256':selected['sha256'] if selected else None,
        'scope':'finite executable practice policy; authored diagnosis and test suite'}
    if plan['early_rejection']:report['evaluation_plan']=plan
    return report
