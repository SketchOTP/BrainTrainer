"""First developmental executive over the recovered neural substrate.

Authored mechanisms learn from the individual's outcomes. Reflection and review
are evidence computations, not language performance. Dreams are explicit learned
model rehearsals, never additional lived outcomes or proof of an ability.
"""
from dataclasses import replace
from copy import deepcopy
from creature_brain.neural import DECISION_FROM_ACTION
from .curriculum import LearningCurriculum
from .maintenance import Maintenance
from .shared_activity import SharedActivity
from .action_feasibility import ActionFeasibility
from .spatial_exploration import SpatialExploration
from .world_motion_review import WorldMotionReview
from .reflective_trials import ReflectiveTrials

LEGACY_MODEL = 'developmental-executive-v1'
REHEARSAL_MODEL = 'developmental-executive-v2'
CURRICULUM_MODEL = 'developmental-executive-v3'
EXECUTABLE_MODEL = 'developmental-executive-v4'
ASSISTANCE_MODEL = 'developmental-executive-v5'
MAINTENANCE_MODEL = 'developmental-executive-v6'
FAMILIAR_MODEL = 'developmental-executive-v7'
RECOVERY_MODEL = 'developmental-executive-v8'
REPEATED_MODEL = 'developmental-executive-v9'
SHARED_MODEL = 'developmental-executive-v10'
FEASIBILITY_MODEL = 'developmental-executive-v11'
EXPLORATION_MODEL = 'developmental-executive-v12'
APPROACH_MODEL = 'developmental-executive-v13'
SPATIAL_REVIEW_MODEL = 'developmental-executive-v14'
GUIDED_REVIEW_MODEL = 'developmental-executive-v15'
ROUTE_REVIEW_MODEL = 'developmental-executive-v16'
COUNTERFACTUAL_MODEL = 'developmental-executive-v17'
REHEARSAL_FEEDBACK_MODEL = 'developmental-executive-v18'
PRACTICE_TIMING_MODEL = 'developmental-executive-v19'
RETAINED_CONTINUATION_MODEL = 'developmental-executive-v20'
ACTIVITY_COMMITMENT_MODEL = 'developmental-executive-v21'
WORLD_MOTION_MODEL = 'developmental-executive-v22'
LEARNED_NEED_MODEL = 'developmental-executive-v23'
RELIEF_REVIEW_MODEL = 'developmental-executive-v24'
FIRST_EFFECT_MODEL = 'developmental-executive-v25'
INVESTIGATION_FEEDBACK_MODEL = 'developmental-executive-v26'
ACTIVITY_OPPORTUNITIES_MODEL = 'developmental-executive-v27'
SHARED_HISTORY_MODEL = 'developmental-executive-v28'
IMPLEMENTATION_FOLLOWUP_MODEL = 'developmental-executive-v29'
ASSISTANCE_ESCALATION_MODEL = 'developmental-executive-v30'
INVESTIGATION_RESPONSE_MODEL = 'developmental-executive-v31'
REPORT_REASSESSMENT_MODEL = 'developmental-executive-v32'
MODEL = 'developmental-executive-v33'
SUPPORTED_MODELS = (LEGACY_MODEL, REHEARSAL_MODEL, CURRICULUM_MODEL, EXECUTABLE_MODEL, ASSISTANCE_MODEL, MAINTENANCE_MODEL, FAMILIAR_MODEL, RECOVERY_MODEL, REPEATED_MODEL, SHARED_MODEL, FEASIBILITY_MODEL, EXPLORATION_MODEL, APPROACH_MODEL, SPATIAL_REVIEW_MODEL, GUIDED_REVIEW_MODEL, ROUTE_REVIEW_MODEL, COUNTERFACTUAL_MODEL, REHEARSAL_FEEDBACK_MODEL, PRACTICE_TIMING_MODEL, RETAINED_CONTINUATION_MODEL, ACTIVITY_COMMITMENT_MODEL, WORLD_MOTION_MODEL, LEARNED_NEED_MODEL, RELIEF_REVIEW_MODEL, FIRST_EFFECT_MODEL, INVESTIGATION_FEEDBACK_MODEL, ACTIVITY_OPPORTUNITIES_MODEL, SHARED_HISTORY_MODEL, IMPLEMENTATION_FOLLOWUP_MODEL, ASSISTANCE_ESCALATION_MODEL, INVESTIGATION_RESPONSE_MODEL, REPORT_REASSESSMENT_MODEL, MODEL)


CAPABILITIES = {
    'curriculum':(CURRICULUM_MODEL,EXECUTABLE_MODEL,ASSISTANCE_MODEL,MAINTENANCE_MODEL,FAMILIAR_MODEL,RECOVERY_MODEL,REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'executable':(EXECUTABLE_MODEL,ASSISTANCE_MODEL,MAINTENANCE_MODEL,FAMILIAR_MODEL,RECOVERY_MODEL,REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'assistance':(ASSISTANCE_MODEL,MAINTENANCE_MODEL,FAMILIAR_MODEL,RECOVERY_MODEL,REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'rest':(MAINTENANCE_MODEL,FAMILIAR_MODEL,RECOVERY_MODEL,REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'familiar':(FAMILIAR_MODEL,RECOVERY_MODEL,REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'recovery_investigation':(RECOVERY_MODEL,REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'repeated_development':(REPEATED_MODEL,SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'shared_activity':(SHARED_MODEL,FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'action_feasibility':(FEASIBILITY_MODEL,EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'exploration':(EXPLORATION_MODEL,APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'approach_review':(APPROACH_MODEL,SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'spatial_avoidance_review':(SPATIAL_REVIEW_MODEL,GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'guided_practice_review':(GUIDED_REVIEW_MODEL,ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'world_route_review':(ROUTE_REVIEW_MODEL,COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'stop_counterfactual':(COUNTERFACTUAL_MODEL,REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'rehearsal_feedback':(REHEARSAL_FEEDBACK_MODEL,PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'observed_practice_timing':(PRACTICE_TIMING_MODEL,RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'retained_continuations':(RETAINED_CONTINUATION_MODEL,ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'activity_commitment':(ACTIVITY_COMMITMENT_MODEL,WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'world_motion_review':(WORLD_MOTION_MODEL,LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'learned_need_relief':(LEARNED_NEED_MODEL,RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'relief_review':(RELIEF_REVIEW_MODEL,FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'first_effect_investigation':(FIRST_EFFECT_MODEL,INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'investigation_feedback':(INVESTIGATION_FEEDBACK_MODEL,ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'activity_opportunities':(ACTIVITY_OPPORTUNITIES_MODEL,SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'shared_history':(SHARED_HISTORY_MODEL,IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'implementation_followup':(IMPLEMENTATION_FOLLOWUP_MODEL,ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'assistance_escalation':(ASSISTANCE_ESCALATION_MODEL,INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'investigation_response':(INVESTIGATION_RESPONSE_MODEL,REPORT_REASSESSMENT_MODEL,MODEL),
    'report_reassessment':(REPORT_REASSESSMENT_MODEL,MODEL),
    'reflective_trials':(MODEL,),
}

def supports(model,capability):
    return model in CAPABILITIES[capability]


class DevelopmentalBrain:
    def __init__(self):
        self.version=LEGACY_MODEL
        self.curriculum=LearningCurriculum()
        self.maintenance=Maintenance()
        self.shared=SharedActivity()
        self.feasibility=ActionFeasibility()
        self.exploration=SpatialExploration()
        self.world_motion=WorldMotionReview()
        self.reflective_trials=ReflectiveTrials()
        self.goals=[]
        self.reviews=[]
        self.dreams=[]
        self.last_decision=None
        self.attempts=0
        self.completions=0

    def observe(self, record):
        event=record['payload']
        if event.get('operation')=='adopt-reflective-trial' and not supports(self.version,'reflective_trials'):
            raise ValueError('reflective trials are not enabled')
        if supports(self.version,'reflective_trials'):self.reflective_trials.observe(record)
        if supports(self.version,'world_motion_review'):self.world_motion.observe(record)
        self.maintenance.observe(record)
        self.feasibility.observe(record)
        if "world_motion" not in event:self.exploration.observe(record)
        if record['kind']!='experience':
            self.curriculum.observe(record,discover=False)
            self.shared.observe(record,self.curriculum.goals)
        if record['kind']=='implementation-change' and event.get('operation')=='enable-development':
            if event.get('model') not in SUPPORTED_MODELS:
                raise ValueError('unknown developmental implementation')
            self.version=event['model']
            self.curriculum.repeated_improvement=supports(self.version,'repeated_development')
            self.curriculum.progress_aware_approach=supports(self.version,'approach_review')
            self.curriculum.guided_practice_review=supports(self.version,'guided_practice_review')
            self.curriculum.world_route_review=supports(self.version,'world_route_review')
            self.curriculum.stop_counterfactual=supports(self.version,'stop_counterfactual')
            self.curriculum.observed_practice_timing=supports(self.version,'observed_practice_timing')
            self.curriculum.retain_continuations=supports(self.version,'retained_continuations')
            self.curriculum.first_effect_investigation=supports(self.version,'first_effect_investigation')
            self.curriculum.investigation_feedback=supports(self.version,'investigation_feedback')
            self.curriculum.activity_opportunities=supports(self.version,'activity_opportunities')
            self.shared.history_sensitive=supports(self.version,'shared_history')
            self.curriculum.implementation_followup=supports(self.version,'implementation_followup')
            self.curriculum.assistance_escalation=supports(self.version,'assistance_escalation')
            self.curriculum.investigation_response=supports(self.version,'investigation_response')
            self.curriculum.report_reassessment=supports(self.version,'report_reassessment')
            return
        if record['kind']=='implementation-change' and event.get('operation')=='enable-world':
            for goal in self.exploration.goals:
                if goal['status']=='active':goal['status']='superseded-by-body-migration'
            return
        if record['kind']=='dream':
            if (event.get('model') not in SUPPORTED_MODELS or event.get('real_outcomes_added')!=0 or
                event.get('world_ticks_advanced')!=0):
                raise ValueError('rehearsal must not claim real outcomes or world time')
            self.dreams.append(deepcopy(event))
            for revision in event.get('goal_revisions',[]):
                goal=next((g for g in self.goals if g['id']==revision['goal_id']),None)
                expected_wait=goal.get('retry_wait_ticks',4) if goal and supports(self.version,'rehearsal_feedback') else 4
                if goal is None or revision['method']!='wait-and-probe' or revision['wait_ticks']!=expected_wait:
                    raise ValueError('invalid rehearsal goal revision')
                goal.update(method='wait-and-probe',status='active',wait_remaining=expected_wait,
                            needs_review=False,plan_evidence=record['sequence'])
                if supports(self.version,'rehearsal_feedback'):
                    goal['pending_rehearsal_review']={'dream_event':record['sequence'],
                        'wait_ticks':expected_wait,'target':goal.get('last_stall_target')}
            return
        if record['kind']!='experience':
            return
        self.curriculum.observe(record,discover=supports(self.version,'curriculum'))
        if supports(self.version,'familiar'):
            self.curriculum.offer_familiar_activity(record)
        self.shared.observe(record,self.curriculum.goals)
        outcome=event['outcome'];action=event['executed_action']
        executive=event.get('executive')
        waiting=executive is not None and executive['reason']=='rehearsed-wait-before-probe'
        # Pending approach/contact is not failed execution. Movement is likewise
        # a distinct observed result, not a failed consumption.
        terminal=not waiting and (outcome['completed'] or outcome['status'] in ('not-completed','target-lost','unavailable-action'))
        if terminal:
            self.attempts+=1
            self.completions+=int(outcome['completed'])
        adverse=outcome['completed'] and outcome['hunger_adjustment']>0
        if adverse:
            key=(action['action'],action['attention'])
            existing=next((g for g in self.goals if g['key']==list(key) and g['status']=='active'),None)
            if existing is None:
                self.goals.append({'id':f"goal:{record['sequence']}",'key':list(key),
                    'objective':'avoid-repeating-observed-adverse-outcome','status':'active',
                    'origin':'own-experienced-outcome','evidence':[record['sequence']],
                    'method':'revise-action-selection','progress':0})
            else:
                existing['evidence'].append(record['sequence'])
                existing['method']='review-ineffective-strategy'
        if executive and executive['reason']=='avoid-observed-harm':
            goal=next((g for g in self.goals if g['id']==executive['goal_id']),None)
            reviewable=True
            if supports(self.version,'spatial_avoidance_review') and 'world_motion' in event:
                before=next((o for o in event['observation']['objects'] if o['identity']==action['target']),None)
                after=next((o for o in event.get('observation_after',{}).get('objects',[]) if o['identity']==action['target']),None)
                motion=event['world_motion']
                matched=(outcome['action_id']==action['id'] and outcome['target']==action['target'] and outcome['action']==action['action'])
                same_region=motion['before']['region']==motion['after']['region']
                moved=any(abs(motion['after'][axis]-motion['before'][axis])>1e-9 for axis in ('x','y'))
                known=bool(matched and same_region and before and after)
                away=bool(known and moved and after['distance']>before['distance']+1e-9)
                if goal:
                    goal['motion_review']={'event':record['sequence'],'distance_before':before['distance'] if before else None,
                        'distance_after':after['distance'] if after else None,'progress_observed':away,
                        'assessment':'increased-observed-separation' if away else 'no-observed-progress' if known else 'insufficient-evidence',
                        'cause':'unknown'}
                # Lost observations or an unrelated outcome are not evidence of failed movement.
                reviewable=known
            else:
                before,after=event['body_motion']['before'],event['body_motion']['after']
                relative=next((o['relative_position'] for o in event['observation']['objects'] if o['identity']==action['target']),None)
                away=relative is not None and (after-before)*relative<0
            if goal and supports(self.version,'rehearsal_feedback'):
                pending=goal.get('pending_rehearsal_review')
                matched=(outcome['action_id']==action['id'] and outcome['target']==action['target'] and outcome['action']==action['action'])
                probe_observed=all(any(o['identity']==action['target'] for o in event.get(key,{}).get('objects',[])) for key in ('observation','observation_after'))
                if pending and not goal.get('wait_remaining',0) and reviewable and matched and probe_observed and pending['target']==action['target']:
                    recovered=bool(away and not outcome['completed'])
                    next_wait=4 if recovered else min(8,pending['wait_ticks']*2)
                    goal.setdefault('rehearsal_reviews',[]).append({**pending,'outcome_event':record['sequence'],
                        'assessment':'movement-recovered' if recovered else 'no-observed-recovery',
                        'next_wait_ticks':next_wait,'cause':'unknown','evidence_kind':'real-probe'})
                    goal['retry_wait_ticks']=next_wait
                    del goal['pending_rehearsal_review']
                if reviewable and matched and not away:goal['last_stall_target']=action['target']
            if goal and away and not outcome['completed']:
                goal['progress']+=1
                if goal['progress']>=3:
                    goal['status']='demonstrated-local-strategy'
                    goal['success_evidence']=record['sequence']
                if self.version!=LEGACY_MODEL:
                    goal.update(stalled=0,needs_review=False,wait_remaining=0)
                    goal['method']='revise-action-selection'
            elif goal and self.version!=LEGACY_MODEL and reviewable:
                goal['stalled']=goal.get('stalled',0)+1
                goal['last_stall_event']=record['sequence']
                if goal['stalled']>=3:
                    goal.update(method='review-ineffective-strategy',status='active',needs_review=True)
        if executive and executive['reason']=='rehearsed-wait-before-probe':
            goal=next((g for g in self.goals if g['id']==executive['goal_id']),None)
            if goal:
                goal['wait_remaining']=max(0,goal.get('wait_remaining',0)-1)
        if terminal or adverse or executive:
            self.reviews.append({'event':record['sequence'],'action_id':action['id'],
                'assessment':'waiting-for-probe' if waiting else 'adverse-consequence' if adverse else 'completed' if outcome['completed'] else outcome['status'],
                'implementation_cause':'unknown','real_attempts':self.attempts,'real_completions':self.completions})

    def choose(self, proposed, observation, memory, *, reserve=None, position=None, intrinsic_actions=(0,8), exploration_pending=False):
        if supports(self.version,'rest') and reserve is not None:
            rest=self.maintenance.choose(proposed,reserve,investigate=supports(self.version,'recovery_investigation'))
            if rest is not None:
                selected,decision=rest
                self.last_decision={'model':self.version,**decision}
                return selected
        if supports(self.version,'reflective_trials'):
            trial=self.reflective_trials.choose(proposed,observation)
            if trial is not None:
                selected,decision=trial;self.last_decision={'model':self.version,**decision};return selected
        selected=proposed;reason='retain-substrate-proposal';goal_id=None;evidence=None
        target=next((o for o in observation.objects if o.identity==proposed.target),None)
        row=memory.effects.get((target.type_id,target.category,proposed.action)) if target else None
        controlling_goal=None
        # An active goal owns its action sequence. It must not depend on the
        # substrate proposing the very action the goal was trying to change.
        # A known useful resource takes precedence over local avoidance practice.
        useful=memory.intention(observation) if self.version!=LEGACY_MODEL else None
        if useful is not None and supports(self.version,'learned_need_relief'):
            resource=next((o for o in observation.objects if o.identity==useful['target']),None)
            if resource is not None:
                action=useful['action'] if resource.contact else 4
                if action in resource.available_actions:
                    selected=replace(proposed,target=resource.identity,attention=resource.category,
                        action=action,decision=DECISION_FROM_ACTION[action])
                    self.last_decision={'model':self.version,'reason':'recheck-remembered-need-relief' if useful.get('recheck') else 'use-observed-need-relief',
                        'goal_id':None,'target':resource.identity,'selected_action':action,
                        'proposal_action':proposed.action,'evidence_event':useful['evidence_event'],
                        'expected_relief':useful['expected_relief'],'observed_hunger':observation.hunger,
                        'uncertainty':useful['uncertainty'],
                        **({'nonrelief_evidence':useful['nonrelief_evidence']} if useful.get('recheck') else {})}
                    return selected
        if self.version!=LEGACY_MODEL and useful is None:
            for pending in reversed(self.goals):
                if pending['status']!='active':
                    continue
                candidates=[o for o in observation.objects if o.category==pending['key'][1]
                            and 5 in o.available_actions and
                            memory.effects.get((o.type_id,o.category,pending['key'][0]),{}).get('mean_relief',0)<0]
                if candidates:
                    target=min(candidates,key=lambda o:(o.distance,o.identity))
                    row=memory.effects[(target.type_id,target.category,pending['key'][0])]
                    controlling_goal=pending
                    break
        if row and row['mean_relief']<0:
            goal=controlling_goal or next((g for g in reversed(self.goals) if g['key']==[proposed.action,target.category]),None)
            if goal is not None and 5 in target.available_actions:
                # This executive changes the action, rather than depending on
                # the substrate obeying another sensory cue. Retreat is an
                # authored initial strategy, subject to measured outcome review.
                action=5
                reason='avoid-observed-harm'
                if self.version!=LEGACY_MODEL and goal.get('wait_remaining',0)>0 and 0 in target.available_actions:
                    action=0;reason='rehearsed-wait-before-probe'
                selected=replace(proposed,action=action,decision=DECISION_FROM_ACTION[action],
                                 target=target.identity,attention=target.category)
                goal_id=goal['id'];evidence=row['last_event']
        if supports(self.version,'curriculum') and useful is None:
            practice=self.curriculum.choose(proposed,observation)
            if practice is not None and supports(self.version,'exploration') and ((position is not None and self.exploration.active()) or (supports(self.version,'activity_commitment') and exploration_pending)) and practice[1].get('activity_objective')=='revisit-familiar-activity' and not any(o.identity==practice[0].target and o.distance<=1 for o in observation.objects):
                practice=None
            if practice is not None and (reason=='retain-substrate-proposal' or practice[0].target!=selected.target):
                selected,decision=practice
                if goal_id is not None:
                    decision['deferred_goal_id']=goal_id
                self.last_decision={'model':self.version,**decision}
                return selected
        if reason=='retain-substrate-proposal' and useful is None and supports(self.version,'exploration') and position is not None:
            exploration=self.exploration.choose(proposed,position,intrinsic_actions)
            if exploration is not None:
                selected,decision=exploration
                self.last_decision={'model':self.version,**decision}
                return selected
        if reason=='retain-substrate-proposal' and supports(self.version,'action_feasibility'):
            alternative=self.feasibility.alternative(proposed,observation,intrinsic_actions=intrinsic_actions)
            if alternative is not None:
                selected,decision=alternative
                self.last_decision={'model':self.version,**decision}
                return selected
        self.last_decision={'model':self.version,'reason':reason,'goal_id':goal_id,
                            'evidence_event':evidence,'proposal_action':proposed.action,
                            'selected_action':selected.action}
        if reason=='rehearsed-wait-before-probe':
            self.last_decision['dream_event']=goal['plan_evidence']
        return selected

    def improvement_request(self):
        return self.curriculum.improvement_request() if supports(self.version,'executable') else None

    def assistance_request(self):
        if supports(self.version,'world_motion_review'):
            request=self.world_motion.assistance_request()
            if request:return request
        if supports(self.version,'recovery_investigation'):
            request=self.maintenance.assistance_request()
            if request:return request
        return self.curriculum.assistance_request() if supports(self.version,'assistance') else None

    def communication_request(self):
        request=self.assistance_request()
        if request:return request
        if supports(self.version,'shared_activity'):
            if any(g['status'] in ('active','recovery-needs-investigation') for g in self.maintenance.goals):return None
            invitation=self.shared.invitation(self.curriculum.goals)
            if invitation and supports(self.version,'exploration') and invitation['goal_id']!=(self.last_decision or {}).get('goal_id'):return None
            return invitation
        return None

    def rehearsal_due(self):
        return (self.version!=LEGACY_MODEL and any(g.get('needs_review') for g in self.goals)) or self.curriculum.investigation_plan() is not None

    def dream(self, memory):
        """Offline model rehearsal with explicit uncertainty, no world execution."""
        possibilities=[]
        for (type_id,category,action),row in sorted(memory.effects.items()):
            possibilities.append({'type_id':type_id,'category':category,'action':action,
                'predicted_response_relief':row['mean_relief'],'observations':row['count'],
                'source_event':row['last_event'],'classification':'model-prediction-not-experience',
                'candidate_strategy':'consider-alternative' if row['mean_relief']<0 else 'reuse-if-relevant',
                'uncertainty':'unobserved-alternatives-remain-unknown'})
        revisions=[]
        if self.version!=LEGACY_MODEL:
            for goal in self.goals:
                if goal.get('needs_review'):
                    feedback=supports(self.version,'rehearsal_feedback')
                    wait=goal.get('retry_wait_ticks',4) if feedback else 4
                    revisions.append({'goal_id':goal['id'],'method':'wait-and-probe','wait_ticks':wait,
                        'evidence_event':goal['last_stall_event'],
                        'prediction':f'defer repeated ineffective motion; test recovery after {wait} held actions' if feedback else 'defer repeated ineffective motion; test recovery after four held actions',
                        **({'review_event':goal['rehearsal_reviews'][-1]['outcome_event']} if feedback and goal.get('rehearsal_reviews') else {}),
                        'uncertainty':'recovery timing and failure cause unknown; interval adapts to observed probes within authored bounds' if feedback else 'recovery timing and failure cause unknown; wait interval is authored'})
        return {'model':self.version,'kind':'offline-rehearsal','possibilities':possibilities,
                'goal_revisions':revisions,
                **({'curriculum_investigation':self.curriculum.investigation_plan()} if self.curriculum.investigation_plan() is not None else {}),
                'goals_considered':[g['id'] for g in self.goals if g['status']=='active'],
                'real_outcomes_added':0,'world_ticks_advanced':0}

    def review(self):
        result={'model':self.version,'goals':deepcopy(self.goals),'recent_reflections':deepcopy(self.reviews[-16:]),
                'real_attempts':self.attempts,'real_completions':self.completions,
                'dream_count':len(self.dreams),'recent_dreams':[
                    {'kind':dream.get('kind','offline-learned-model-rehearsal'),
                     'source_event':dream.get('source_event'),'source_tick':dream.get('source_tick'),
                     'hypothesis_count':len(dream.get('hypotheses',[])),
                     'candidate_goal_method':dream.get('candidate_goal',{}).get('method'),
                     'candidate_goal_evidence':dream.get('candidate_goal',{}).get('evidence_ids',[]),
                     'trial_target':(dream.get('candidate_trial') or {}).get('target'),
                     'real_outcomes_added':dream.get('real_outcomes_added',0),
                     'world_ticks_advanced':dream.get('world_ticks_advanced',0)}
                    for dream in self.dreams[-3:]],
                'limitations':['local action strategy only',
                'dreams do not establish real competence','executable revision limited to an authored practice-policy language' if supports(self.version,'executable') else 'executable self-modification unavailable in this version']}
        if supports(self.version,'curriculum'):
            result.update(self.curriculum.review())
        result.update(self.maintenance.review())
        if supports(self.version,'shared_activity'):result.update(self.shared.review())
        if supports(self.version,'action_feasibility'):result.update(self.feasibility.review())
        if supports(self.version,'exploration'):result.update(self.exploration.review())
        if supports(self.version,'world_motion_review'):result.update(self.world_motion.review())
        if supports(self.version,'reflective_trials'):result.update(self.reflective_trials.review())
        return result
