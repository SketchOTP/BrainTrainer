"""Experience-driven discovery and practice of visible object affordances.

An authored curiosity mechanism selects unknown interactions. The environment
advertises available actions, but supplies no successful-action examples or task
goals. Learned effect evidence and target transfer remain distinct.
"""
from copy import deepcopy
from dataclasses import replace
from .benchmark.contract import ChosenAction, Outcome, attributed_adjustment
from .neural import DECISION_FROM_ACTION
from .practice_policy import PracticePolicy, source_for

INTERACTIONS=frozenset((1,2,3,6,7,8,12,13))


class LearningCurriculum:
    def __init__(self):
        self.goals=[]
        self.skills={}
        self.policy=PracticePolicy()
        self.development_results=[]
        self.implementation_followup=False
        self.implementation_reviews=[]
        self.evaluation_memory=[]
        self.repeated_improvement=False
        self.progress_aware_approach=False
        self.guided_practice_review=False
        self.world_route_review=False
        self.stop_counterfactual=False
        self.observed_practice_timing=False
        self.retain_continuations=False
        self.first_effect_investigation=False
        self.investigation_feedback=False
        self.activity_opportunities=False
        self.assistance=[]
        self.assistance_escalation=False
        self.investigation_response=False
        self.report_reassessment=False
        self.investigation_reports=[]
        self.guidance=[]
        self.last_practice_tick=0

    def observe(self, record, *, discover):
        payload=record['payload']
        if record['kind']=='communication' and payload.get('operation') in ('request-practice-help','request-practice-investigation'):
            if payload['operation']=='request-practice-investigation' and payload!=self.assistance_request():
                raise ValueError('investigation request does not match failed guidance evidence')
            self.assistance.append({**deepcopy(payload),'event':record['sequence']})
            return
        if record['kind']=='supplied-information' and payload.get('operation')=='investigation-response':
            goal=self.validate_investigation_response(payload['goal_id'],payload['response'],payload['source'])
            entry={**deepcopy(payload),'event':record['sequence'],
                'evidence_kind':'supplied-information','starting_trials':goal['trials'],
                'starting_changes':goal['changes'],'status':'reported-not-verified'}
            if payload['response']=='not-responsive':
                goal['status']='set-aside-on-report'
            else:
                allowance=max(3,min(8,goal.get('observed_gap',0)+1))
                goal.update(status='active',practice_allowance=goal['trials']+allowance)
                entry.update(status='awaiting-experience',additional_attempts=allowance)
            # Previous advice has already been evaluated; later outcomes belong
            # to this new report, not retroactive credit for the earlier advice.
            goal.pop('guidance_event',None)
            self.investigation_reports.append(entry)
            return
        if record['kind']=='supplied-information' and payload.get('operation')=='practice-guidance':
            goal=self.validate_guidance(payload['goal_id'],payload['additional_attempts'],payload['source'])
            goal.update(status='active',practice_allowance=goal['trials']+payload['additional_attempts'])
            entry={**deepcopy(payload),'event':record['sequence'],'status':'unverified',
                   'starting_trials':goal['trials'],'starting_changes':goal['changes']}
            self.guidance.append(entry)
            goal['guidance_event']=record['sequence']
            return
        if record['kind']=='dream' and 'curriculum_investigation' in payload:
            plan=payload['curriculum_investigation']
            if not isinstance(plan,dict) or plan!=self.investigation_plan():
                raise ValueError('investigation does not match unresolved experience')
            goal=next(g for g in self.goals if g['id']==plan['goal_id'])
            goal.update(status='active',practice_allowance=goal['trials']+plan['additional_attempts'],
                investigation={'dream_event':record['sequence'],'starting_trials':goal['trials'],
                    'status':'prediction-awaiting-experience','plan':deepcopy(plan)})
            return
        if record['kind']=='development-evaluation':
            self.development_results.append(deepcopy(payload))
            failures=sorted({case['profile'] for candidate in payload['candidates'] for case in candidate['cases'] if not case['passed']})
            self.evaluation_memory.append({'event':record['sequence'],'failed_profiles':failures})
            return
        if record['kind']=='implementation-change' and payload.get('operation')=='install-practice-policy':
            policy=PracticePolicy(payload['source'])
            if policy.sha256!=payload.get('sha256'):
                raise ValueError('practice implementation digest differs')
            self.policy=policy
            goal=next((g for g in self.goals if g['id']==payload.get('resume_goal')),None)
            if goal is not None:
                if self.implementation_followup:
                    for prior in self.implementation_reviews:
                        if prior['status']=='awaiting-experience':prior['status']='superseded-before-outcome'
                    self.implementation_reviews.append({'implementation_event':record['sequence'],
                        'policy_sha256':policy.sha256,'goal_id':goal['id'],'request_id':payload['request_id'],
                        'starting_trials':goal['trials'],'starting_changes':goal['changes'],
                        'status':'awaiting-experience','evidence_kind':'post-installation-experience',
                        'scope':'resumed goal only; no general benefit established'})
                goal['status']='active'
                if self.guided_practice_review and 'practice_allowance' in goal:
                    goal['superseded_practice_allowance']={'limit':goal.pop('practice_allowance'),
                        'implementation_event':record['sequence'],'request_id':payload['request_id']}

            return
        if record['kind']!='experience':return
        event=record['payload'];before=event['observation']['objects']
        if discover:
            for obj in before:
                for action in sorted(set(obj['available_actions']) & INTERACTIONS):
                    key=(obj['type_id'],action)
                    skill=self.skills.get(key)
                    if skill and (obj['identity'] in skill['targets'] or (skill.get('last_relief') is not None and skill['last_relief']<0)):continue
                    if any(g['type_id']==key[0] and g['action']==action and g['target']==obj['identity'] for g in self.goals):continue
                    known=skill is not None and skill['changes']>=2
                    self.new_goal(record,target=obj['identity'],type_id=obj['type_id'],action=action,
                        objective='verify-known-skill' if known else 'discover-object-effect',
                        origin='observed-unfamiliar-affordance',required_changes=1 if known else 2)
        chosen=ChosenAction(**event['executed_action']);outcome=Outcome(**event['outcome'])
        target=next((o for o in before if o['identity']==chosen.target),None)
        executive=event.get('executive',{})
        goal=next((g for g in self.goals if g['id']==executive.get('goal_id')),None)
        if executive.get('reason')=='practice-approach' and goal:
            matched=(outcome.action_id==chosen.id and outcome.target==chosen.target and outcome.action==chosen.action)
            if not self.progress_aware_approach:
                goal['approach_ticks']+=1
                if goal['approach_ticks']>=32:
                    goal['status']='needs-movement-investigation'
                    goal['evidence'].append(record['sequence'])
            elif matched:
                goal['approach_ticks']+=1
                after=next((o for o in event.get('observation_after',{}).get('objects',[]) if o['identity']==chosen.target),None)
                progress=bool(target and after and after['distance']<target['distance']-1e-9)
                contact=bool(after and after.get('contact'))
                route=event.get('world_motion',{}).get('route_progress') if self.world_route_review else None
                route_matched=bool(route and route['action_id']==chosen.id and route['target']==chosen.target
                    and route['action']==chosen.action and route['distance_after'] is not None
                    and route['basis']=='inherited-collision-map-route')
                if route_matched:
                    progress=route['distance_after']<route['distance_before']-1e-9
                prior=goal.get('approach_review',{})
                stalled=0 if progress or contact else prior.get('consecutive_no_progress',0)+1
                goal['approach_review']={'event':record['sequence'],
                    'distance_before':target['distance'] if target else None,
                    'distance_after':after['distance'] if after else None,
                    'progress_observed':progress,'consecutive_no_progress':stalled,
                    'assessment':'contact-observed' if contact else 'getting-closer' if progress else 'no-observed-progress',
                    'cause':'unknown'}
                if route_matched:
                    goal['approach_review'].update(progress_basis=route['basis'],
                        route_distance_before=route['distance_before'],route_distance_after=route['distance_after'],
                        assessment='contact-observed' if contact else 'advancing-along-planned-route' if progress else 'no-observed-route-progress')
                if stalled>=3:
                    goal['status']='needs-movement-investigation'
                    goal['evidence'].append(record['sequence'])
        if target is None or chosen.action not in INTERACTIONS:return
        if goal is None:
            goal=next((g for g in self.goals if g['target']==chosen.target and g['type_id']==target['type_id'] and g['action']==chosen.action and g['status']=='active'),None)
        matched=(outcome.action_id==chosen.id and outcome.target==chosen.target and outcome.action==chosen.action)
        if not matched:return
        if outcome.status in ('approaching','contact','not-in-contact'):return
        adjustment=attributed_adjustment(chosen,outcome)
        relief=-adjustment if adjustment is not None else None
        after=next((o for o in event.get('observation_after',{}).get('objects',[]) if o['identity']==chosen.target),None)
        after_observed='observation_after' in event
        changed=bool(outcome.completed and after_observed and (after is None or target['appearance']!=after['appearance']))
        after_appearance=after['appearance'] if after else None
        if self.report_reassessment and changed:
            for report in self.investigation_reports:
                if report['response']!='not-responsive' or report.get('later_assessment'):continue
                reported_goal=next(g for g in self.goals if g['id']==report['goal_id'])
                if (reported_goal['target']!=chosen.target or reported_goal['type_id']!=target['type_id']
                        or reported_goal['action']!=chosen.action):continue
                report['later_assessment']={'status':'later-effect-observed',
                    'experience_event':record['sequence'],'observed_tick':event['time'],
                    'scope':'same target, type and action at a later time',
                    'original_report_accuracy':'not-established','cause':'not-established'}
                if reported_goal['status']=='set-aside-on-report':
                    reported_goal.update(status='set-aside-superseded-by-observed-effect',
                        superseding_experience_event=record['sequence'])
        key=(target['type_id'],chosen.action)
        skill=self.skills.setdefault(key,{'trials':0,'changes':0,'targets':[], 'evidence':[], 'last_relief':None, 'transitions':[]})
        skill['trials']+=1;skill['changes']+=int(changed);skill['evidence'].append(record['sequence'])
        recent=skill.setdefault('recent_effects',[])
        recent.append({'changed':changed,'event':record['sequence']})
        del recent[:-8]
        if relief is not None:skill['last_relief']=relief
        if outcome.completed and after_observed:
            transition=next((t for t in skill['transitions'] if t['before']==target['appearance'] and t['after']==after_appearance),None)
            if transition is None:
                skill['transitions'].append({'before':target['appearance'],'after':after_appearance,'count':1,'evidence_event':record['sequence']})
            else:
                transition['count']+=1;transition['evidence_event']=record['sequence']
        if changed and chosen.target not in skill['targets']:skill['targets'].append(chosen.target)
        if goal:
            self.last_practice_tick=event['time']
            if self.activity_opportunities:goal['last_trial_tick']=event['time']
            goal['trials']+=1;goal['changes']+=int(changed);goal['evidence'].append(record['sequence'])
            if self.investigation_feedback and changed and goal['changes']==1:
                goal['first_effect_trial']=goal['trials']
            if self.observed_practice_timing and changed:
                gap=goal['no_change_streak']+1
                if gap>goal.get('observed_gap',0):
                    goal.update(observed_gap=gap,timing_evidence=record['sequence'])
                if gap>skill.get('observed_gap',0):
                    skill.update(observed_gap=gap,timing_evidence=record['sequence'])
            goal['no_change_streak']=0 if changed else goal['no_change_streak']+1
            if relief is not None and relief<0:
                goal['status']='adverse-result-stop-practice'
            elif goal['changes']>=goal['required_changes']:
                goal['status']='demonstrated-visible-effect'
            elif (goal['trials']>=goal['practice_allowance'] if 'practice_allowance' in goal else self.policy.should_stop(**self.policy_inputs(goal))):
                goal['status']='effect-unresolved-review-needed'
                goal['stop_decision']={'policy_sha256':self.policy.sha256,
                    'inputs':self.policy_inputs(goal),'result':True}
                if 'practice_allowance' in goal:
                    goal['stop_decision']={'rule':'bounded-practice-allowance','limit':goal['practice_allowance'],
                        'inputs':{'trials':goal['trials']},'result':True}
            if ('investigation' in goal and goal['investigation']['status']=='prediction-awaiting-experience'
                    and goal['status']!='active'):
                goal['investigation'].update(status='observed-effect' if goal['changes'] else 'no-effect-within-budget',
                    outcome_event=record['sequence'],observed_changes=goal['changes'],
                    additional_trials=goal['trials']-goal['investigation']['starting_trials'])
            if self.investigation_response:
                for report in self.investigation_reports:
                    if report['goal_id']!=goal['id'] or report['status']!='awaiting-experience':continue
                    report.update(observed_trials=goal['trials']-report['starting_trials'],
                        observed_changes=goal['changes']-report['starting_changes'],
                        latest_experience_event=record['sequence'])
                    if goal['status']!='active':
                        report.update(status='effect-observed' if report['observed_changes'] else 'no-effect-within-recheck',
                            outcome_event=record['sequence'],cause='not-established')
            if self.implementation_followup:
                for followup in self.implementation_reviews:
                    if followup['goal_id']!=goal['id'] or followup['status']!='awaiting-experience':continue
                    followup.update(observed_trials=goal['trials']-followup['starting_trials'],
                        observed_changes=goal['changes']-followup['starting_changes'],
                        latest_experience_event=record['sequence'])
                    if goal['status']!='active':
                        followup.update(status='goal-completed-in-experience' if goal['status']=='demonstrated-visible-effect' else 'goal-unresolved-in-experience',
                            goal_status=goal['status'],outcome_event=record['sequence'],
                            cause='not-established')
            if self.retain_continuations:
                if goal['status']=='active' and 'practice_allowance' not in goal:
                    goal.setdefault('policy_continuations',[]).append({'event':record['sequence'],
                        'inputs':self.policy_inputs(goal)})
                elif goal['status']=='demonstrated-visible-effect':
                    retained=skill.setdefault('successful_continuations',[])
                    for case in goal.get('policy_continuations',[]):
                        if not any(prior['inputs']==case['inputs'] for prior in retained):
                            retained.append({**deepcopy(case),'completion_event':record['sequence'],
                                'goal_id':goal['id'],'target':goal['target']})
            if (goal.get('guidance_event') is not None and goal['status']!='active' and
                    not (self.guided_practice_review and goal.get('superseded_practice_allowance'))):
                guidance=next(g for g in self.guidance if g['event']==goal['guidance_event'])
                guidance.update(status='supported-in-this-context' if goal['status']=='demonstrated-visible-effect' else 'not-supported',
                    outcome_event=record['sequence'],observed_new_changes=goal['changes']-guidance['starting_changes'])
                if goal['status']=='demonstrated-visible-effect':
                    skill['retained_practice']={'observed_trials':goal['trials'],
                        'source_event':record['sequence'],'guidance_event':guidance['event'],
                        'teacher':guidance['source'],'scope':'same observed type; new target requires verification'}


    def new_goal(self,record,*,target,type_id,action,objective,origin,required_changes,preference_basis=None):
        familiar=objective=='revisit-familiar-activity'
        goal={'id':f"familiar:{record['sequence']}:{target}" if familiar else f"learn:{record['sequence']}:{target}:{action}",
            'objective':objective,'type_id':type_id,'action':action,'target':target,
            'status':'active','origin':origin,'evidence':[record['sequence']],
            'trials':0,'changes':0,'no_change_streak':0,'approach_ticks':0,'required_changes':required_changes}
        learned=self.skills.get((type_id,action),{}).get('retained_practice')
        if learned:
            goal.update(practice_allowance=learned['observed_trials'],practice_evidence=deepcopy(learned))
        if preference_basis is not None:goal['preference_basis']=deepcopy(preference_basis)
        if self.observed_practice_timing:
            timing=self.skills.get((type_id,action),{})
            goal['observed_gap']=timing.get('observed_gap',0)
            if timing.get('timing_evidence') is not None:goal['timing_evidence']=timing['timing_evidence']
        self.goals.append(goal)

    def investigation_plan(self):
        if not self.first_effect_investigation:return None
        investigated={(g['type_id'],g['action']) for g in self.goals if 'investigation' in g}
        for goal in self.goals:
            if (goal['status']!='effect-unresolved-review-needed' or goal['changes'] or
                goal['objective']!='discover-object-effect' or 'practice_allowance' in goal or
                (goal['type_id'],goal['action']) in investigated or goal['trials']!=3):continue
            budget,evidence=self.investigation_budget(goal['action'])
            return {'goal_id':goal['id'],'method':'bounded-first-effect-investigation',
                **({'budget_evidence':evidence,'budget_origin':'observed-investigation-outcomes'} if self.investigation_feedback else {}),
                'additional_attempts':budget,'evidence':list(goal['evidence']),
                'hypothesis':'an effect may require more attempts than the initial trial allowed',
                'alternative':'this interaction may produce no observable effect',
                'prediction':f'at most {budget} further trials may reveal an effect; success is unknown' if self.investigation_feedback else 'at most two further trials may reveal an effect; success is unknown',
                'classification':'hypothesis-not-experience',
                'stop_condition':f'{budget} additional trials, adverse outcome, or goal completion' if self.investigation_feedback else 'two additional trials, adverse outcome, or goal completion',
                'scope':'one investigation per observed type and action; authored cost bound'}
        return None

    def investigation_budget(self,action):
        budget=2;evidence=[]
        if not self.investigation_feedback:return budget,evidence
        completed=[g for g in self.goals if g['action']==action and
            g.get('investigation',{}).get('status') in ('observed-effect','no-effect-within-budget') and
            'budget_evidence' in g['investigation']['plan']]
        for goal in sorted(completed,key=lambda g:g['investigation']['outcome_event']):
            trial=goal['investigation'];old=budget
            if trial['status']=='no-effect-within-budget':budget=max(2,budget-1)
            elif goal.get('first_effect_trial')==trial['starting_trials']+trial['plan']['additional_attempts']:
                budget=min(5,budget+1)
            evidence.append({'outcome_event':trial['outcome_event'],'assessment':trial['status'],
                'previous_budget':old,'next_budget':budget})
        return budget,evidence

    def policy_inputs(self,goal):
        inputs={key:goal[key] for key in ('trials','changes','no_change_streak')}
        if self.observed_practice_timing:inputs['observed_gap']=goal.get('observed_gap',0)
        return inputs

    def retained_policy_checks(self,policy):
        checks=[]
        for (type_id,action),skill in sorted(self.skills.items()):
            for case in skill.get('successful_continuations',[]):
                checks.append({**deepcopy(case),'type_id':type_id,'action':action,
                    'candidate_would_stop':policy.should_stop(**case['inputs']),
                    'evidence_kind':'recorded-successful-continuation-counterfactual'})
        return checks

    def offer_familiar_activity(self,record):
        event=record['payload'];objects=event.get('observation_after',{}).get('objects',[])
        if event['time']-self.last_practice_tick<32:return
        if any(g['status']=='active' and any(o['identity']==g['target'] and o['type_id']==g['type_id'] for o in objects) for g in self.goals):return
        candidates=[]
        for obj in objects:
            # Familiar play uses a demonstrated non-nutritional interaction.
            skill=self.skills.get((obj['type_id'],1))
            if (1 not in obj['available_actions'] or not skill or skill['changes']<2 or
                (skill['last_relief'] is not None and skill['last_relief']<0)):
                continue
            recent=skill.get('recent_effects',[])
            if not recent:continue
            review={}
            if self.activity_opportunities:
                failures=[]
                for prior in reversed(self.goals):
                    if prior['target']!=obj['identity'] or prior['type_id']!=obj['type_id'] or prior['action']!=1:continue
                    if prior['status']=='demonstrated-visible-effect':break
                    if prior['status']=='effect-unresolved-review-needed' and prior['changes']==0:failures.append(prior)
                if failures:
                    latest=failures[0]
                    # Only observed outcomes establish the retry interval. Older
                    # versions without a tick do not invent an elapsed duration.
                    if 'last_trial_tick' in latest:
                        wait=64*(2**min(len(failures),4))
                        if event['time']-latest['last_trial_tick']<wait:continue
                        review={'recheck_after_failure':latest['evidence'][-1],
                            'retry_interval_ticks':wait,'consecutive_failed_goals':len(failures)}
            if not any(e['changed'] for e in recent) and not review:continue
            candidates.append({'target':obj['identity'],'type_id':obj['type_id'],
                'expected_visible_effect':sum(e['changed'] for e in recent)/len(recent),
                **review,
                'distance':obj['distance'],'evidence':[e['event'] for e in recent]})
        if not candidates:return
        if self.activity_opportunities:
            returns=[g for g in self.goals if g['objective']=='revisit-familiar-activity']
            for candidate in candidates:
                last=next((i for i in range(len(returns)-1,-1,-1)
                    if returns[i]['target']==candidate['target'] and
                    returns[i]['type_id']==candidate['type_id']),None)
                skipped= len(returns) if last is None else len(returns)-last-1
                value=candidate['expected_visible_effect']
                if not value and candidate.get('recheck_after_failure') is not None:
                    skill=self.skills[(candidate['type_id'],1)]
                    value=skill['changes']/skill['trials']
                    candidate['recheck_basis']='historical-effects; current-effect-unknown'
                candidate.update(skipped_opportunities=skipped,
                    selection_value=value*(1+skipped),
                    last_selected_event=returns[last]['evidence'][0] if last is not None else None,
                    latest_opportunity_event=returns[-1]['evidence'][0] if returns else None)
            candidates.sort(key=lambda c:(c.get('recheck_after_failure') is None,
                -c['selection_value'],c['distance'],c['target']))
        else:
            candidates.sort(key=lambda c:(-c['expected_visible_effect'],c['distance'],c['target']))
        selected=candidates[0]
        self.new_goal(record,target=selected['target'],type_id=selected['type_id'],action=1,
            objective='revisit-familiar-activity',origin='retained-activity-experience',
            required_changes=1,preference_basis=candidates)
        self.last_practice_tick=event['time']

    def choose(self, proposed, observation):
        for goal in self.goals:
            if goal['status']!='active':continue
            known=self.skills.get((goal['type_id'],goal['action']))
            if known and known['last_relief'] is not None and known['last_relief']<0:continue
            obj=next((o for o in observation.objects if o.identity==goal['target'] and o.type_id==goal['type_id'] and goal['action'] in o.available_actions),None)
            if obj is None:continue
            action=goal['action'] if obj.contact else 4
            if action not in obj.available_actions:continue
            choice=replace(proposed,target=obj.identity,attention=obj.category,action=action,decision=DECISION_FROM_ACTION[action])
            skill=self.skills.get((goal['type_id'],goal['action']),{})
            predictions=sorted({t['after'] for t in skill.get('transitions',[]) if t['before']==obj.appearance},key=lambda value:(value is not None,str(value))) if obj.contact else []
            return choice,{'expected_appearance':predictions,'prediction_scope':'observed-context-only' if predictions else 'unknown',
                'reason':'practice-interaction' if obj.contact else 'practice-approach',
                'goal_id':goal['id'],'evidence_event':goal['evidence'][0],
                'activity_objective':goal['objective'],
                'proposal_action':proposed.action,'selected_action':action}
        return None

    def validate_investigation_response(self,goal_id,response,source):
        if not self.investigation_response:
            raise ValueError('investigation responses are not enabled')
        if response not in ('not-responsive','changed') or not isinstance(source,str) or not source.strip():
            raise ValueError('investigation response requires a supported report and attributed source')
        goal=next((g for g in self.goals if g['id']==goal_id),None)
        if goal is None or goal['status'] not in ('effect-unresolved-review-needed','set-aside-on-report'):
            raise ValueError('investigation response requires an unresolved or set-aside goal')
        if not any(r['goal_id']==goal_id and r['operation']=='request-practice-investigation' for r in self.assistance):
            raise ValueError('investigation response must answer an actual investigation request')
        if goal['status']=='set-aside-on-report' and response=='not-responsive':
            raise ValueError('this activity is already set aside')
        return goal

    def validate_guidance(self,goal_id,additional_attempts,source):
        if not isinstance(source,str) or not source.strip() or type(additional_attempts) is not int or not 1<=additional_attempts<=8:
            raise ValueError('guidance requires an attributed source and one to eight additional attempts')
        goal=next((g for g in self.goals if g['id']==goal_id),None)
        if goal is None or goal['status']!='effect-unresolved-review-needed':
            raise ValueError('guidance must address an unresolved practice goal')
        if not any(r['goal_id']==goal_id for r in self.assistance):
            raise ValueError('guidance must answer an actual assistance request')
        if any(g['goal_id']==goal_id for g in self.guidance):
            raise ValueError('this goal already tested practice-extension advice; investigate another method')
        return goal

    def assistance_request(self):
        requested={r['goal_id'] for r in self.assistance}
        pending=self.improvement_request()
        for goal in self.goals:
            if goal['status']!='effect-unresolved-review-needed':continue
            if pending and pending['goal_id']==goal['id']:continue
            if goal['id'] in requested:
                if self.assistance_escalation and not any(r['goal_id']==goal['id'] and r['operation']=='request-practice-investigation' for r in self.assistance):
                    advice=next((g for g in reversed(self.guidance) if g['goal_id']==goal['id'] and g['status']=='not-supported'),None)
                    if advice:
                        return {'operation':'request-practice-investigation','goal_id':goal['id'],
                            'target':goal['target'],'origin':'unsuccessful-guided-practice',
                            'guidance_event':advice['event'],'outcome_event':advice['outcome_event'],
                            'observed_new_attempts':goal['trials']-advice['starting_trials'],
                            'observed_new_changes':advice['observed_new_changes'],
                            'message':'I tried the extra practice, but this activity is still unresolved. Can you help check what is preventing it?',
                            'requested_help':'investigate the object or circumstances rather than repeat the same advice',
                            'unknowns':['whether the object can currently respond','whether the limitation is in the body, surroundings, or knowledge']}
                continue
            followup=next((r for r in reversed(self.implementation_reviews)
                if r['goal_id']==goal['id'] and r['status']=='goal-unresolved-in-experience'
                and r.get('observed_changes')==0 and goal['changes']==r['starting_changes']),None)
            return {'operation':'request-practice-help','goal_id':goal['id'],
                **({'implementation_followup':deepcopy(followup)} if followup else {}),
                'origin':'own-unresolved-practice','target':goal['target'],
                'evidence':deepcopy(goal['evidence']),'observed_attempts':goal['trials'],
                'observed_changes':goal['changes'],
                'message':('I tried the revised practice rule but saw no further effect. Can you help me investigate?' if followup else 'I stopped practicing because I could not establish a reliable effect. Can you help me investigate?'),
                'unknowns':['whether the object can respond','whether more attempts would help'],
                'requested_help':'a bounded suggestion for further practice'}
        return None

    def improvement_request(self):
        reviewed={r['request_id'] for r in self.development_results}
        for goal in self.goals:
            if self.implementation_followup and any(
                row['goal_id']==goal['id'] and row['status']=='goal-unresolved-in-experience'
                and row.get('observed_changes')==0 and goal['changes']==row['starting_changes']
                for row in self.implementation_reviews):
                # A prior visible effect is not new evidence that another patch
                # can help after the installed change produced no further effect.
                continue
            request_id=f"{goal['id']}:review:{goal['evidence'][-1]}"
            if (goal['status']!='effect-unresolved-review-needed' or goal['changes']==0 or
                request_id in reviewed or (self.policy.counter!='trials' and not self.repeated_improvement) or
                (self.policy.counter=='progress_sensitive' and not self.observed_practice_timing) or
                self.policy.limit>=32 or
                ('practice_allowance' in goal and not self.guided_practice_review)):
                continue
            total=self.policy.counter=='trials'
            candidates=([{'hypothesis':'increase total attempt budget','source':source_for('trials',min(32,self.policy.limit*2))},
                         {'hypothesis':'stop on consecutive absence of progress','source':source_for('no_change_streak',self.policy.limit)}]
                        if total else
                        [{'hypothesis':'increase uniform no-progress threshold','source':source_for('no_change_streak',self.policy.limit+1)},
                         {'hypothesis':'allow more time only after observed progress','source':source_for('progress_sensitive',self.policy.limit+1)}])
            if self.observed_practice_timing and self.policy.counter in ('progress_sensitive','observed_gap_sensitive'):
                margin=self.policy.limit+1 if self.policy.counter=='observed_gap_sensitive' else 1
                uniform=min(32,goal.get('observed_gap',0)+margin) if self.policy.counter=='observed_gap_sensitive' else min(32,self.policy.limit+1)
                candidates=[{'hypothesis':'increase the uniform post-progress wait',
                    'source':source_for('progress_sensitive',uniform)},
                    {'hypothesis':'use the response gap demonstrated by this activity type',
                    'source':source_for('observed_gap_sensitive',margin)}]
            guided='practice_allowance' in goal
            if guided:
                # The observed stop belongs to advice, not to the executable rule.
                # A candidate must replace that exhausted allowance in a test copy.
                source=source_for('progress_sensitive',min(32,max(4,self.policy.limit+1)))
                if not any(candidate['source']==source for candidate in candidates):
                    candidates.append({'hypothesis':'retain a short initial bound and allow extra attempts after progress',
                        'source':source})
            if self.investigation_feedback and goal.get('observed_gap',0)>0:
                source=source_for('observed_gap_sensitive',1)
                if not any(candidate['source']==source for candidate in candidates):
                    candidates.append({'hypothesis':'use the actual response gap discovered during investigation',
                        'source':source})
            return {'request_id':request_id,'goal_id':goal['id'],
                'origin':'own-practice-review','evidence':deepcopy(goal['evidence']),
                'observed_problem':'practice stopped despite a visible effect',
                **({'regression_scope':'progress-sensitive-practice-v1'} if not total or guided else {}),
                'diagnosis':(('the rehearsed investigation allowance was exhausted despite a visible effect' if 'investigation' in goal else 'the supplied or retained practice allowance was exhausted despite a visible effect') if guided else
                    'the current executable stopping rule counts total attempts' if total else
                    'the uniform no-progress threshold stopped an activity with demonstrated prior progress'),
                **({'superseded_intervention':{'kind':'bounded-practice-allowance','limit':goal['practice_allowance'],
                    'guidance_event':goal.get('guidance_event'),'retained_evidence':deepcopy(goal.get('practice_evidence'))}} if guided else {}),
                'unknowns':['why the device needs multiple attempts','general benefit outside tested tasks'],
                'objective':('retain productive practice without extending unproductive repetition' if total else
                    'preserve the initial stopping bound while permitting limited extra attempts after observed progress'),
                'current_policy':self.policy.describe(),'stop_decision':deepcopy(goal['stop_decision']),
                **({'recorded_counters':self.policy_inputs(goal)} if self.stop_counterfactual else {}),
                'candidates':candidates}
        return None

    def review(self):
        return {'learning_goals':deepcopy(self.goals),'practice_policy':self.policy.describe(),
                'development_results':deepcopy(self.development_results),
                'implementation_reviews':deepcopy(self.implementation_reviews),
                'assistance_requests':deepcopy(self.assistance),'guidance_history':deepcopy(self.guidance),
                'investigation_reports':deepcopy(self.investigation_reports),
                'skills':[{'type_id':key[0],'action':key[1],**deepcopy(row)} for key,row in sorted(self.skills.items())]}
