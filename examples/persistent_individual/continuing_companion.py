"""Provenance-owning research host; no claim of cognitive self-understanding.

Only this envelope is a complete checkpoint. The contained prepared host remains
responsible for brain, body, motor evidence and pending actions. A restore resumes
one history; fork explicitly creates a divergent experimental continuation.
"""
import json
from copy import deepcopy
from pathlib import Path
import uuid
from event_history import ArchivedHistory, canonical, digest

from creature_brain.development import DevelopmentalBrain, MODEL as DEVELOPMENT_MODEL, SUPPORTED_MODELS, supports
from outcome_recall import OutcomeRecall, MODEL as RECALL_MODEL
from confirmation_individual import ConfirmationMotorIndividual
from inherited_preparation import prepare_inherited, prepared_snapshot, restore_prepared

SCHEMA = 'creature-brain-continuing-companion-v1'
KINDS = {'experience', 'external-intervention', 'supplied-information',
         'hypothesis', 'implementation-change', 'inherited-preparation', 'branch', 'dream', 'development-evaluation', 'communication'}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


class ContinuingCompanion:
    """One explicitly attributed research continuation with complete retained events.

    The event capacity is a caller-selected memory bound. Reaching it stops before
    another action instead of dropping personal history. Long-lived archival and
    behavioral use of memory are subsequent work, not claims of this host.
    """
    def __init__(self, program, *, seed=0, event_capacity=10000, good_type=0):
        if type(event_capacity) is not int or event_capacity < 1:
            raise ValueError('event capacity must be a positive integer')
        self._host = ConfirmationMotorIndividual(program, seed=seed, good_type=good_type)
        receipt = prepare_inherited(self._host, program)
        self._lineage = {'individual_id': self._host.identity,
                         'branch_id': str(uuid.uuid4()), 'parent': None,
                         'context': 'research', 'purpose': 'development individual'}
        self._events = []
        self._recall_enabled = False
        self._memory = OutcomeRecall()
        self._mind = DevelopmentalBrain()
        self._development_enabled = False
        self._llm_development_enabled = False
        self._llm_dreams_enabled = False
        self._llm_self_review_enabled = False
        self._llm_self_review_revision = 0
        self._capacity = event_capacity
        self._append('inherited-preparation', {'receipt': receipt})

    @property
    def identity(self):
        return self._host.identity

    @property
    def time(self):
        return self._host.time

    def _room(self, count=1):
        if len(self._events)+count > self._capacity:
            raise ValueError('experience capacity reached; preserve checkpoint before continuing')

    def extend_memory_budget(self, capacity, *, actor):
        """Allocate more retained-event capacity without discarding lived history."""
        if type(capacity) is not int or capacity <= self._capacity:
            raise ValueError('new memory budget must be an integer greater than the current budget')
        if not nonempty(actor):
            raise ValueError('memory budget extension requires an attributed actor')
        previous=self._capacity
        self._capacity=capacity
        self._append('external-intervention',{'operation':'extend-memory-budget',
            'actor':actor,'previous_capacity':previous,'capacity':capacity,
            'scope':'retained event allocation; no learning or code improvement claimed'})

    def _append(self, kind, payload):
        self._room()
        # Validate JSON before accepting a record; checkpoint must preserve it.
        value = json.loads(canonical(payload))
        self._events.append({'sequence': len(self._events), 'tick': self.time,
                             'branch_id': self._lineage['branch_id'],
                             'context': self._lineage['context'],
                             'kind': kind, 'payload': value})
        self._memory.observe(self._events[-1])
        self._mind.observe(self._events[-1])

    def tick(self, *, allow_improvement=True):
        request=(self._mind.improvement_request() if self._development_enabled and
            not self._llm_development_enabled and allow_improvement and
            self._mind.reflective_trials.active() is None else None)
        # Reserve evaluation, possible adoption, rehearsal and actual experience.
        if request:
            self._room(4+int(supports(self._mind.version,'assistance')))
            from self_development import evaluate, install
            from creature_brain.practice_policy import PracticePolicy
            report=evaluate(self,request)
            self._append('development-evaluation',report)
            selected=next((c for c in report['candidates'] if c['sha256']==report['selected_sha256']),None)
            if selected:
                install(self,PracticePolicy(selected['source']),request_id=request['request_id'],
                    resume_goal=request['goal_id'],origin=request.get('candidate_origin','authored-development'))
        rehearse=self._development_enabled and self._mind.rehearsal_due()
        rollback_pending=bool(self._mind.curriculum.failed_lived_candidate())
        self._room(1+int(rehearse)+int(self._development_enabled and supports(self._mind.version,'assistance'))+int(rollback_pending))
        if rehearse:
            self.dream()
        intention = self.intention()
        cue = intention if intention is not None and intention['kind'] == 'recall' else None
        def choose(proposed,observation):
            world=self._host.world
            from world_body import exploration_pending
            selected=self._mind.choose(proposed,observation,self._memory,
                reserve=self._host.reserve if self._host.rest_enabled else None,
                position=self._host.position if world is None else None,intrinsic_actions=self._host.intrinsic_actions(),
                exploration_pending=exploration_pending(self._host) if world is not None else False)
            if world is not None and self._mind.last_decision['reason'] in ('retain-substrate-proposal','defer-unavailable-action','quiet-after-unresolved-motion'):
                from world_body import exploration
                decision=exploration(self._host,proposed)
                if decision is not None:
                    if supports(self._mind.version,'world_motion_review'):decision=self._mind.world_motion.choose(*decision)
                    selected,self._mind.last_decision=decision
            return selected
        executive=choose if self._development_enabled else None
        self._host._route_review_enabled=self._development_enabled and supports(self._mind.version,'world_route_review')
        reserve_before=self._host.reserve
        event = self._host.tick(recall=cue,executive=executive)
        if self._host.rest_enabled:
            event['body_resources']={'before':reserve_before,'after':self._host.reserve}
            self._host.last_event['body_resources']=event['body_resources']
        if executive is not None:
            event['executive']=self._mind.last_decision
            # Include the same decision attribution in the host's durable event.
            self._host.last_event['executive']=event['executive']
        if self._host.world is not None and executive is not None and supports(self._mind.version,'activity_commitment'):
            from world_body import review_exploration
            review_exploration(self._host,event)
            self._host.last_event['world_motion']=deepcopy(event['world_motion'])
        recorded = dict(event)
        if self._recall_enabled:
            recorded['intention'] = intention
        self._append('experience', recorded)
        failed_candidate=self._mind.curriculum.failed_lived_candidate()
        if failed_candidate is not None:
            policy=self._mind.curriculum.policy
            self._append('implementation-change',{'operation':'restore-practice-policy',
                'actor':'creature-development','request_id':failed_candidate['request_id'],
                'rejected_sha256':failed_candidate['policy_sha256'],
                'source':failed_candidate['previous_policy_source'],
                'sha256':failed_candidate['previous_policy_sha256'],
                'scope':'rejected after lived body follow-up produced no additional effect; prior executable policy restored while the failed candidate and all experience remain in history'})
        assistance=self._mind.communication_request() if self._development_enabled else None
        if assistance:
            self._append('communication',assistance)
        return event

    def enable_world(self, *, actor):
        if not nonempty(actor):raise ValueError('world migration requires an actor')
        if self._host.world is not None:return
        self._room()
        from world_body import enable,pack_hash,MODEL
        previous_position=self._host.position
        pending_action=self._host.active_action
        enable(self._host)
        self._append('implementation-change',{'operation':'enable-world','actor':actor,
            'model':MODEL,'pack_sha256':pack_hash(),'previous_position':previous_position,
            'cancelled_action':pending_action,'cancellation_reason':'body-migration',
            'scope':'new top-down body, inherited collision map and path planner; old history retained'})

    def open_home_interiors(self, *, actor):
        if not nonempty(actor):raise ValueError('town expansion requires actor')
        from world_body import expand_home,town_pack_hash
        if self._host.world and self._host.world['pack_sha256']==town_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        expand_home(self._host)
        self._append('implementation-change',{'operation':'open-home-interiors','actor':actor,
            'previous_pack':previous,'pack_sha256':town_pack_hash(),'cancelled_action':cancelled,
            'scope':'original Littleroot buildings and upstairs rooms, added companion workshop; outside connections closed'})

    def make_rural_home(self, *, actor):
        if not nonempty(actor):raise ValueError('rural home change requires actor')
        from world_body import rural_home,rural_pack_hash
        if self._host.world and self._host.world['pack_sha256']==rural_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        rural_home(self._host)
        self._append('implementation-change',{'operation':'make-rural-home','actor':actor,
            'previous_pack':previous,'pack_sha256':rural_pack_hash(),'cancelled_action':cancelled,
            'scope':'expanded rural town; home and workshop retained; pond blocked; berry plots walkable; old history retained'})

    def repair_rural_art(self, *, actor):
        if not nonempty(actor):raise ValueError('visual repair requires actor')
        from world_body import rural_home,visual_pack_hash
        if self._host.world and self._host.world['pack_sha256']==visual_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        rural_home(self._host,visual_pack_hash())
        self._append('implementation-change',{'operation':'repair-rural-art','actor':actor,
            'previous_pack':previous,'pack_sha256':visual_pack_hash(),'cancelled_action':cancelled,
            'scope':'complete native tree assemblies; source-matched roofs; old history retained'})

    def install_interactive_habitat_art(self, *, actor):
        if not nonempty(actor):raise ValueError('habitat art update requires actor')
        from world_body import rural_home,visual_pack_hash,interactive_pack_hash
        if self._host.world and self._host.world['pack_sha256']==interactive_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        rural_home(self._host,interactive_pack_hash())
        self._append('implementation-change',{'operation':'install-interactive-habitat-art','actor':actor,
            'previous_pack':previous,'pack_sha256':interactive_pack_hash(),'cancelled_action':cancelled,
            'scope':'re-skinned Littleroot town, doors, pond, farm, furnished interiors and object cutouts; prior experiences retained'})

    def align_town_paths(self, *, actor):
        if not nonempty(actor):raise ValueError('path alignment requires actor')
        from world_body import rural_home,interactive_pack_hash,path_aligned_pack_hash
        if self._host.world and self._host.world['pack_sha256']==path_aligned_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        rural_home(self._host,path_aligned_pack_hash())
        self._append('implementation-change',{'operation':'align-town-paths','actor':actor,
            'previous_pack':previous,'pack_sha256':path_aligned_pack_hash(),'cancelled_action':cancelled,
            'scope':'connected trail masks and aligned paths from both doors, the farm aisle and pond approach; personal history retained'})

    def install_town_canopy(self, *, actor):
        if not nonempty(actor):raise ValueError('town visual update requires actor')
        from world_body import rural_home,path_aligned_pack_hash,town_canopy_pack_hash
        if self._host.world and self._host.world['pack_sha256']==town_canopy_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        rural_home(self._host,town_canopy_pack_hash())
        self._append('implementation-change',{'operation':'install-town-canopy','actor':actor,
            'previous_pack':previous,'pack_sha256':town_canopy_pack_hash(),'cancelled_action':cancelled,
            'scope':'irregular grass patches, continuous tree rim and doorway-scale creature; free terrain movement and personal history retained'})

    def scope_town_world(self, *, actor):
        if not nonempty(actor):raise ValueError('town scope update requires actor')
        from world_body import rural_home,town_canopy_pack_hash,scoped_town_pack_hash
        if self._host.world and self._host.world['pack_sha256']==scoped_town_pack_hash():return
        self._room();previous=self._host.world['pack_sha256'];cancelled=self._host.active_action
        rural_home(self._host,scoped_town_pack_hash())
        self._append('implementation-change',{'operation':'scope-town-world','actor':actor,
            'previous_pack':previous,'pack_sha256':scoped_town_pack_hash(),'cancelled_action':cancelled,
            'scope':'active home regions limited to Littleroot, the starter house levels and companion workshop; Birch lab and guest-house teleports unavailable; map history retained'})

    def set_home_town(self, region, *, actor):
        if not nonempty(actor):raise ValueError('home change requires an actor')
        if self._host.world is None:raise ValueError('top-down body required')
        if self._host.world.get('home_region')==region:return
        self._room()
        from world_body import confine_home,pose
        before=pose(self._host);cancelled=self._host.active_action
        confine_home(self._host,region)
        self._append('external-intervention',{'operation':'set-home-town','actor':actor,
            'region':region,'before':before,'after':pose(self._host),'cancelled_action':cancelled,
            'scope':'owner-selected development habitat; town exits disabled; past visits retained'})

    def enable_development(self, *, actor):
        if not nonempty(actor):
            raise ValueError('development adoption requires an attributed actor')
        if self._development_enabled and self._mind.version==DEVELOPMENT_MODEL:
            return
        self._append('implementation-change', {'actor':actor, 'operation':'enable-development',
                     'model':DEVELOPMENT_MODEL, 'body_model':'intrinsic-rest-and-hold-v2',
                     'scope':'new executive with intrinsic rest and hold actions over recovered substrate'})
        self._development_enabled=True
        self._host.rest_enabled=True
        self._host.hold_enabled=True

    def enable_llm_directed_development(self, *, actor):
        if not nonempty(actor):raise ValueError('LLM-directed development requires an attributed actor')
        if not self._development_enabled or not supports(self._mind.version,'reflective_trials'):
            raise ValueError('LLM-directed development requires the embodied developmental brain and reflection capability')
        if self._llm_development_enabled:return
        self._append('implementation-change',{'operation':'enable-llm-directed-development',
            'model':'llm-bounded-code-development-v1','actor':actor,
            'scope':'the creature may request a restricted executable practice-policy candidate; branch regressions run before installation and live body outcomes determine retention or rollback'})
        self._llm_development_enabled=True

    def enable_reflective_dreams(self, *, actor):
        if not nonempty(actor):raise ValueError('reflective dream adoption requires an attributed actor')
        if not supports(self._mind.version,'reflective_trials'):
            raise ValueError('reflective dream cycle requires the OAuth reflection capability')
        if self._llm_dreams_enabled:return
        self._append('implementation-change',{'operation':'enable-rest-linked-reflective-dreams',
            'model':'llm-rest-linked-dream-v1','actor':actor,
            'scope':'after an observed completed rest, the reflective component may form evidence-cited hypotheses; it adds no experience or action'})
        self._llm_dreams_enabled=True

    def enable_lived_self_review(self, *, actor):
        if not nonempty(actor):raise ValueError('lived self-review adoption requires an attributed actor')
        if not supports(self._mind.version,'reflective_trials'):
            raise ValueError('lived self-review requires the OAuth reflection capability')
        if self._llm_self_review_enabled:return
        self._append('implementation-change',{'operation':'enable-lived-self-review',
            'model':'llm-lived-self-review-v1','actor':actor,
            'scope':'after a bounded body trial, the reflective component reviews its actual outcomes and may propose the next embodied goal'})
        self._llm_self_review_enabled=True
        self._llm_self_review_revision=1

    def improve_lived_self_review(self, *, actor):
        if not nonempty(actor):raise ValueError('self-review improvement requires an attributed actor')
        if not self._llm_self_review_enabled or self._llm_self_review_revision!=1:
            raise ValueError('the first lived self-review implementation must be active')
        self._append('implementation-change',{'operation':'improve-lived-self-review',
            'model':'llm-lived-self-review-v2','actor':actor,
            'scope':'compare repeated lived outcomes and defer identical goals unless a new target or appearance prediction adds evidence'})
        self._llm_self_review_revision=2

    def record_reflective_dream(self, packet, response):
        from llm_reflection import validate_response
        if not isinstance(packet,dict) or not isinstance(packet.get('branch'),dict):
            raise ValueError('dream packet requires an attributed branch')
        if not self._llm_dreams_enabled or packet.get('purpose')!='dream':
            raise ValueError('rest-linked reflective dreaming is not active')
        if (packet.get('identity')!=self.identity or
                packet.get('branch',{}).get('branch_id')!=self._lineage['branch_id'] or
                type(packet.get('tick')) is not int or packet['tick']>self.time):
            raise ValueError('dream belongs to a different individual, branch or future')
        focus=packet.get('focus')
        rest_event=focus.get('rest_event') if isinstance(focus,dict) else None
        if type(rest_event) is not int or not 0<=rest_event<len(self._events):
            raise ValueError('dream has no cited completed-rest event')
        source=self._events[rest_event]
        if (rest_event not in packet.get('citable_evidence_ids',[]) or
                not any(row.get('sequence')==rest_event for row in packet.get('evidence',[])) or
                focus.get('rest_tick')!=source['tick'] or source['tick']>packet['tick'] or
                source['branch_id']!=self._lineage['branch_id']):
            raise ValueError('dream rest citation differs from this branch history')
        action=source['payload'].get('executed_action',{})
        outcome=source['payload'].get('outcome',{})
        if (source['kind']!='experience' or action.get('action')!=0 or action.get('target') is not None or
                outcome.get('status')!='rested' or not outcome.get('completed')):
            raise ValueError('dream source is not an observed completed rest')
        validate_response(response,packet)
        self._append('dream',{'model':self._mind.version,'kind':'rest-linked-llm-hypothesis-v1',
            'request_id':packet['request_id'],'source_event':rest_event,'source_tick':source['tick'],
            'hypotheses':deepcopy(response['hypotheses']),'candidate_goal':deepcopy(response['next_goal']),
            'candidate_trial':deepcopy(response['trial']),'real_outcomes_added':0,'world_ticks_advanced':0,
            'limitation':'hypotheses only; abilities require subsequent body experience'})

    def dream(self):
        if not self._development_enabled:
            raise ValueError('developmental brain is not enabled')
        rehearsal=self._mind.dream(self._memory)
        self._append('dream',rehearsal)
        return rehearsal

    def self_review(self):
        review=self._mind.review()
        review['llm_development_enabled']=self._llm_development_enabled
        return review

    def enable_recall(self, *, actor):
        if not nonempty(actor):
            raise ValueError('recall adoption requires an attributed actor')
        if self._recall_enabled:
            return
        self._append('implementation-change', {'actor': actor, 'operation': 'enable-recall',
                     'model': RECALL_MODEL, 'scope': 'authored sensory adapter, not creature-directed change'})
        self._recall_enabled = True

    def intention(self):
        return self._memory.intention(self._host.observe()) if self._recall_enabled else None

    def configure_recovery(self, *, reserve, rest_rate, actor):
        import math
        if not nonempty(actor) or any(type(v) not in (int,float) or not math.isfinite(v) for v in (reserve,rest_rate)) or not 0<=reserve<=100 or not 0<=rest_rate<=1:
            raise ValueError('invalid attributed body recovery configuration')
        self._room()
        self._host.reserve=float(reserve);self._host.rest_rate=float(rest_rate)
        self._append('external-intervention',{'operation':'configure-recovery','actor':actor,
            'reserve':reserve,'rest_rate':rest_rate})

    def configure_berry_relief(self, *, oran, pecha, actor):
        if not nonempty(actor) or any(type(v) not in (int,float) or not 0<=v<=.2 for v in (oran,pecha)):
            raise ValueError('berry effectiveness requires an actor and relief between zero and 0.2')
        nutrition=(self._host.world or {}).get('garden',{}).get('nutrition')
        if nutrition is None:raise ValueError('stored food capability required')
        self._room();nutrition['relief']={'oran':oran,'pecha':pecha}
        self._append('external-intervention',{'operation':'configure-berry-relief','actor':actor,'relief':dict(nutrition['relief'])})

    def enable_berry_nutrition(self, *, actor):
        from garden import enable_nutrition,NUTRITION_MODEL
        if not nonempty(actor):raise ValueError('stored food adoption requires an actor')
        if 'nutrition' in (self._host.world or {}).get('garden',{}):return
        self._room();enable_nutrition(self._host)
        self._append('implementation-change',{'operation':'enable-berry-nutrition','model':NUTRITION_MODEL,'actor':actor})

    def enable_garden(self, *, actor):
        from garden import enable,model_for_pack
        if not nonempty(actor):raise ValueError('garden adoption requires an actor')
        if (self._host.world or {}).get('garden') is not None:return
        self._room();enable(self._host)
        model=model_for_pack(self._host.world['pack_sha256'])
        self._append('implementation-change',{'operation':'enable-garden','model':model,'actor':actor})

    def refine_town_layout(self, *, actor):
        if not nonempty(actor):raise ValueError('town layout update requires an actor')
        from garden import GROWTH_MODEL
        from world_body import rural_home,scoped_town_pack_hash,natural_town_pack_hash
        if self._host.world and self._host.world['pack_sha256']==natural_town_pack_hash():return
        self._room()
        previous=self._host.world['pack_sha256']
        if previous!=scoped_town_pack_hash():raise ValueError('the scoped v8 Littleroot town is required')
        cancelled=self._host.active_action
        garden_before=(self._host.world.get('garden') or {}).get('model')
        rural_home(self._host,natural_town_pack_hash())
        garden_after=(self._host.world.get('garden') or {}).get('model')
        if garden_before is None:
            garden_after=None
        elif garden_after!=GROWTH_MODEL:
            raise ValueError('town layout update did not migrate berry tree growth')
        self._append('implementation-change',{'operation':'refine-town-layout','actor':actor,
            'previous_pack':previous,'pack_sha256':natural_town_pack_hash(),
            'garden_model_before':garden_before,'garden_model_after':garden_after,
            'cancelled_action':cancelled,
            'scope':'irregular town paths and garden positions; mature tree stages retained; personal history retained'})

    def connect_pond_trail(self, *, actor):
        if not nonempty(actor):raise ValueError('pond path update requires an actor')
        from garden import GROWTH_MODEL
        from world_body import connect_pond_trail,natural_town_pack_hash,connected_town_pack_hash
        if self._host.world and self._host.world['pack_sha256']==connected_town_pack_hash():return
        self._room()
        previous=self._host.world['pack_sha256'] if self._host.world else None
        if previous!=natural_town_pack_hash():raise ValueError('the v9 Littleroot town is required')
        garden_model=(self._host.world.get('garden') or {}).get('model')
        if garden_model is not None and garden_model!=GROWTH_MODEL:raise ValueError('berry garden v2 is required')
        connect_pond_trail(self._host)
        self._append('implementation-change',{'operation':'connect-pond-trail','actor':actor,
            'previous_pack':previous,'pack_sha256':connected_town_pack_hash(),
            'garden_model_before':garden_model,'garden_model_after':garden_model,
            'scope':'connect the pond-bank walk without crossing water; preserve the current activity route and personal history'})

    def add_world_device(self, identity, *, label, function, type_id, delay=2, region, x, y, actor):
        if not nonempty(actor):raise ValueError('world additions require an attributed actor')
        self._room()
        specification=dict(label=label,function=function,type_id=type_id,delay=delay,region=region,x=x,y=y)
        self._host.add_world_device(identity,**specification)
        self._append('external-intervention',{'operation':'add-world-device','actor':actor,
            'target':identity,**specification})

    def configure_device(self, identity, *, function, type_id, actor, delay=2):
        if not nonempty(actor):
            raise ValueError('world changes require an attributed actor')
        self._room()
        self._host.configure_device(identity,function=function,type_id=type_id,delay=delay)
        self._append('external-intervention',{'actor':actor,'operation':'configure-device',
                     'target':identity,'function':function,'type_id':type_id,'delay':delay})

    def place(self, identity, x, *, actor, visible=True):
        if not nonempty(actor):
            raise ValueError('external changes require an attributed actor')
        self._room()
        self._host.place(identity, x, visible)
        self._append('external-intervention', {'actor': actor, 'operation': 'place',
                     'target': identity, 'x': x, 'visible': visible})

    def offer_practice_guidance(self, goal_id, *, additional_attempts, source):
        # Validate at the owning projection before appending durable information.
        self._mind.curriculum.validate_guidance(goal_id,additional_attempts,source)
        self._append('supplied-information',{'operation':'practice-guidance',
            'goal_id':goal_id,'additional_attempts':additional_attempts,'source':source,
            'classification':'advice-requiring-experiential-verification'})

    def adopt_reflective_trial(self, packet, response):
        from llm_reflection import validate_response
        if not supports(self._mind.version,'reflective_trials'):raise ValueError('reflective trials are not enabled')
        validate_response(response,packet)
        if (packet['identity']!=self.identity or packet['branch']['branch_id']!=self._lineage['branch_id']
                or type(packet['tick']) is not int or not 0<=packet['tick']<=self.time):
            raise ValueError('reflection belongs to a different individual, branch or future')
        if response['next_goal']['method']!='practice' or response.get('trial') is None:
            raise ValueError('reflection has no executable practice trial')
        request=next((item for item in self._mind.reflective_trials.requests
                      if item['request_id']==packet['request_id']),None)
        if request is None or request.get('purpose','analysis')!=packet.get('purpose','analysis'):
            raise ValueError('trial purpose differs from its durable reflection request')
        refs=response['next_goal']['evidence_ids']
        if not refs or any(i>=len(self._events) or self._events[i]['tick']>packet['tick'] for i in refs):
            raise ValueError('trial evidence does not belong to source history')
        payload={'operation':'adopt-reflective-trial','request_id':packet['request_id'],
            'source':'codex-oauth-reflection','purpose':packet.get('purpose','analysis'),'source_tick':packet['tick'],
            'plan':deepcopy(response['trial']),'reflection':deepcopy(response)}
        self._mind.reflective_trials.validate(payload)
        self._append('hypothesis',payload)

    def respond_to_investigation(self, goal_id, response, *, source):
        self._mind.curriculum.validate_investigation_response(goal_id,response,source)
        self._append('supplied-information',{'operation':'investigation-response',
            'goal_id':goal_id,'response':response,'source':source})

    def report_companion_availability(self, available):
        if not supports(self._mind.version,'shared_activity') or type(available) is not bool:
            raise ValueError('shared activity requires an enabled implementation and explicit availability')
        self._append('supplied-information',{'operation':'companion-availability','available':available,'source':'companion-person'})

    def respond_to_invitation(self, invitation_event, response):
        if not supports(self._mind.version,'shared_activity'):raise ValueError('shared activity is not enabled')
        self._mind.shared.validate_response(invitation_event,response)
        self._append('supplied-information',{'operation':'shared-activity-response','invitation_event':invitation_event,'response':response,'source':'companion-person'})

    def record_information(self, content, *, source, hypothesis=False):
        if not nonempty(content) or not nonempty(source) or type(hypothesis) is not bool:
            raise ValueError('information requires content, source and an explicit kind')
        self._append('hypothesis' if hypothesis else 'supplied-information',
                     {'content': content, 'source': source})

    def checkpoint_header(self):
        return json.loads(canonical({'schema':SCHEMA,'lineage':self._lineage,
            'host':prepared_snapshot(self._host),'event_capacity':self._capacity}))

    def snapshot(self):
        # Own the portable representation here: the underlying host includes
        # tuples, while JSON restore produces lists. Consumers receive one form.
        value=self.checkpoint_header()
        value['events']=json.loads(canonical(list(self._events)))
        return value

    @classmethod
    def restore(cls, data):
        """Resume exact durable state; wall-clock time never creates experience."""
        if not isinstance(data, dict) or data.get('schema') != SCHEMA:
            raise ValueError('expected a complete companion envelope')
        data = json.loads(canonical(data))
        return cls._restore_history(data,data.get('events'))

    @classmethod
    def _restore_history(cls,data,events):
        if not isinstance(data,dict) or data.get('schema')!=SCHEMA:
            raise ValueError('expected a complete companion header')
        lineage = data.get('lineage')
        if (not isinstance(lineage, dict) or
            any(not nonempty(lineage.get(k)) for k in ('individual_id', 'branch_id', 'purpose')) or
            lineage.get('context') not in ('research', 'test')):
            raise ValueError('invalid lineage')
        parent = lineage.get('parent')
        if parent is not None and (not isinstance(parent, dict) or
            any(not nonempty(parent.get(k)) for k in ('branch_id', 'checkpoint_sha256')) or
            parent['branch_id'] == lineage['branch_id'] or
            type(parent.get('tick')) is not int or parent['tick'] < 0):
            raise ValueError('invalid branch parent')
        capacity = data.get('event_capacity')
        if (type(capacity) is not int or capacity < 1 or not isinstance(events, (list,ArchivedHistory))
            or not events or len(events) > capacity):
            raise ValueError('invalid retained history')
        host = restore_prepared(data['host'])
        if host.identity != lineage['individual_id']:
            raise ValueError('host and lineage identities differ')
        obj = cls.__new__(cls)
        obj._host, obj._lineage = host, lineage
        obj._events, obj._capacity = events, capacity
        obj._memory = OutcomeRecall()
        obj._mind = DevelopmentalBrain()
        obj._development_enabled = False
        obj._llm_development_enabled = False
        obj._llm_dreams_enabled = False
        obj._llm_self_review_enabled = False
        obj._llm_self_review_revision = 0
        obj._recall_enabled = False
        added_devices=set()
        last_transition=None
        previous_tick = -1
        active_branch = None
        active_context = None
        experienced_ticks = 0
        allocated_capacity=None
        world_adoption=None
        garden_adoption=False
        nutrition_adoption=False
        garden_model=None
        home_region=None
        current_pack=None
        for i, event in enumerate(events):
            if (not isinstance(event, dict) or event.get('sequence') != i or
                type(event.get('sequence')) is not int or event.get('kind') not in KINDS or
                type(event.get('tick')) is not int or not previous_tick <= event['tick'] <= host.time or
                not nonempty(event.get('branch_id')) or event.get('context') not in ('research', 'test') or
                not isinstance(event.get('payload'), dict)):
                raise ValueError('invalid event provenance')
            if i == 0:
                if event['kind'] != 'inherited-preparation' or event['tick'] != 0:
                    raise ValueError('history must begin with inherited preparation')
                if event['payload'].get('receipt') != data['host']['receipt']:
                    raise ValueError('preparation history differs from host receipt')
                active_branch, active_context = event['branch_id'], event['context']
            elif event['kind'] == 'branch':
                if (event['payload'].get('parent_branch_id') != active_branch or
                    event['branch_id'] == active_branch or event['context'] != 'test'):
                    raise ValueError('branch does not extend retained history')
                active_branch, active_context = event['branch_id'], event['context']
                last_transition=event
            elif event['branch_id'] != active_branch or event['context'] != active_context:
                raise ValueError('unrecorded branch transition')
            if event['kind'] == 'experience':
                experienced_ticks += 1
                if event['payload'].get('time') != experienced_ticks:
                    raise ValueError('experience payload clock differs from history')
            if event['tick'] != experienced_ticks:
                raise ValueError('history omits or invents experienced ticks')
            previous_tick = event['tick']
            payload = event['payload']
            if payload.get('operation')=='extend-memory-budget':
                old,new=payload.get('previous_capacity'),payload.get('capacity')
                if (event['kind']!='external-intervention' or not nonempty(payload.get('actor')) or
                    type(old) is not int or type(new) is not int or old<1 or new<=old or i>old or
                    (allocated_capacity is not None and old!=allocated_capacity)):
                    raise ValueError('invalid memory budget extension history')
                allocated_capacity=new
            if allocated_capacity is not None and i>=allocated_capacity:
                raise ValueError('history exceeds its recorded memory budget')
            if event['kind'] == 'implementation-change' and payload.get('operation') == 'enable-recall':
                if payload.get('model') != RECALL_MODEL or not nonempty(payload.get('actor')):
                    raise ValueError('unknown recall implementation')
                obj._recall_enabled = True
            if payload.get('operation')=='set-home-town':
                from world_body import pack
                if event['kind']!='external-intervention' or not nonempty(payload.get('actor')) or payload.get('region') not in pack()['maps']:
                    raise ValueError('invalid home-town history')
                home_region=payload['region']
            if event['kind']=='implementation-change' and payload.get('operation')=='enable-world':
                from world_body import MODEL as WORLD_MODEL,pack_hash
                if world_adoption is not None or payload.get('model')!=WORLD_MODEL or payload.get('pack_sha256')!=pack_hash() or not nonempty(payload.get('actor')):
                    raise ValueError('invalid world adoption history')
                world_adoption=payload
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='open-home-interiors':
                from world_body import town_pack_hash
                if event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or payload.get('previous_pack')!=current_pack or payload.get('pack_sha256')!=town_pack_hash():raise ValueError('invalid town expansion history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='make-rural-home':
                from world_body import town_pack_hash,rural_pack_hash
                if event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or payload.get('previous_pack')!=current_pack or current_pack!=town_pack_hash() or payload.get('pack_sha256')!=rural_pack_hash():raise ValueError('invalid rural home history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='repair-rural-art':
                from world_body import rural_pack_hash,visual_pack_hash
                if event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or payload.get('previous_pack')!=current_pack or current_pack!=rural_pack_hash() or payload.get('pack_sha256')!=visual_pack_hash():raise ValueError('invalid visual repair history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='install-interactive-habitat-art':
                from world_body import visual_pack_hash,interactive_pack_hash
                if event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or payload.get('previous_pack')!=current_pack or current_pack!=visual_pack_hash() or payload.get('pack_sha256')!=interactive_pack_hash():raise ValueError('invalid interactive habitat art history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='align-town-paths':
                from world_body import interactive_pack_hash,path_aligned_pack_hash
                if (event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or
                    payload.get('previous_pack')!=current_pack or current_pack!=interactive_pack_hash() or
                    payload.get('pack_sha256')!=path_aligned_pack_hash()):
                    raise ValueError('invalid path alignment history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='install-town-canopy':
                from world_body import path_aligned_pack_hash,town_canopy_pack_hash
                if (event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or
                    payload.get('previous_pack')!=current_pack or current_pack!=path_aligned_pack_hash() or
                    payload.get('pack_sha256')!=town_canopy_pack_hash()):
                    raise ValueError('invalid town visual update history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='scope-town-world':
                from world_body import town_canopy_pack_hash,scoped_town_pack_hash
                if (event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or
                    payload.get('previous_pack')!=current_pack or current_pack!=town_canopy_pack_hash() or
                    payload.get('pack_sha256')!=scoped_town_pack_hash()):
                    raise ValueError('invalid town scope history')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='refine-town-layout':
                from world_body import scoped_town_pack_hash,natural_town_pack_hash
                from garden import MODEL as LEGACY_GARDEN_MODEL,GROWTH_MODEL
                if (event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or
                    payload.get('previous_pack')!=current_pack or current_pack!=scoped_town_pack_hash() or
                    payload.get('pack_sha256')!=natural_town_pack_hash()):
                    raise ValueError('invalid natural town layout history')
                before_model=payload.get('garden_model_before');after_model=payload.get('garden_model_after')
                if garden_adoption:
                    if garden_model!=LEGACY_GARDEN_MODEL or before_model!=garden_model or after_model!=GROWTH_MODEL:
                        raise ValueError('natural town update lacks its berry growth migration')
                    garden_model=after_model
                elif before_model is not None or after_model is not None:
                    raise ValueError('natural town update claims a missing garden migration')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='connect-pond-trail':
                from world_body import natural_town_pack_hash,connected_town_pack_hash
                from garden import GROWTH_MODEL
                if (event['kind']!='implementation-change' or not nonempty(payload.get('actor')) or
                    payload.get('previous_pack')!=current_pack or current_pack!=natural_town_pack_hash() or
                    payload.get('pack_sha256')!=connected_town_pack_hash()):
                    raise ValueError('invalid pond path update history')
                before_model=payload.get('garden_model_before');after_model=payload.get('garden_model_after')
                if garden_adoption:
                    if garden_model!=GROWTH_MODEL or before_model!=garden_model or after_model!=garden_model:
                        raise ValueError('pond path update changed the berry growth model')
                elif before_model is not None or after_model is not None:
                    raise ValueError('pond path update claims a missing garden migration')
                current_pack=payload['pack_sha256']
            if payload.get('operation')=='request-reflection':
                if event['kind']!='hypothesis':raise ValueError('reflection request is not an attributed hypothesis')
                purpose=payload.get('purpose','analysis')
                if purpose not in ('analysis','self-review','dream','development'):raise ValueError('unknown reflection purpose')
                if purpose=='development' and (not obj._llm_development_enabled or
                        not isinstance(payload.get('development_request'),dict)):
                    raise ValueError('development reflection lacks the adopted code-development capability or request')
                if purpose=='dream':
                    rest_event=payload.get('rest_event')
                    if (not obj._llm_dreams_enabled or type(rest_event) is not int or
                            not 0<=rest_event<i or payload.get('rest_tick')!=events[rest_event]['tick']):
                        raise ValueError('dream request lacks a prior attributed rest')
                    source=events[rest_event]
                    action=source.get('payload',{}).get('executed_action',{})
                    outcome=source.get('payload',{}).get('outcome',{})
                    if (source.get('kind')!='experience' or source.get('branch_id')!=event['branch_id'] or
                            action.get('action')!=0 or action.get('target') is not None or
                            outcome.get('status')!='rested' or not outcome.get('completed')):
                        raise ValueError('dream request source is not a completed rest experience')
            if payload.get('operation')=='enable-garden':
                from garden import model_for_pack
                if (garden_adoption or event['kind']!='implementation-change' or
                    not nonempty(payload.get('actor')) or payload.get('model')!=model_for_pack(current_pack)):
                    raise ValueError('invalid garden adoption history')
                garden_adoption=True
                garden_model=payload['model']
            if payload.get('operation')=='enable-berry-nutrition':
                from garden import NUTRITION_MODEL
                if nutrition_adoption or not garden_adoption or event['kind']!='implementation-change' or payload.get('model')!=NUTRITION_MODEL or not nonempty(payload.get('actor')):raise ValueError('invalid stored food adoption history')
                nutrition_adoption=True
            if payload.get('operation')=='add-world-device':
                target=payload.get('target')
                if (event['kind']!='external-intervention' or not nonempty(payload.get('actor')) or
                    not nonempty(target) or target in added_devices):raise ValueError('invalid device addition history')
                added_devices.add(target)
            if event['kind']=='implementation-change' and payload.get('operation')=='enable-relationship':
                raise ValueError('retired partner-selection checkpoint; use archived implementation to inspect it')
            if event['kind']=='implementation-change' and payload.get('operation')=='enable-development':
                if payload.get('model') not in SUPPORTED_MODELS or not nonempty(payload.get('actor')):
                    raise ValueError('unknown developmental implementation')
                obj._development_enabled=True
            if payload.get('operation')=='enable-llm-directed-development':
                if (event['kind']!='implementation-change' or obj._llm_development_enabled or
                        payload.get('model')!='llm-bounded-code-development-v1' or
                        not nonempty(payload.get('actor')) or not obj._development_enabled or
                        not supports(obj._mind.version,'reflective_trials')):
                    raise ValueError('invalid LLM-directed development adoption history')
                obj._llm_development_enabled=True
            if payload.get('operation')=='enable-rest-linked-reflective-dreams':
                if (event['kind']!='implementation-change' or obj._llm_dreams_enabled or
                        payload.get('model')!='llm-rest-linked-dream-v1' or
                        not nonempty(payload.get('actor')) or
                        not supports(obj._mind.version,'reflective_trials')):
                    raise ValueError('invalid reflective dream adoption history')
                obj._llm_dreams_enabled=True
            if payload.get('operation')=='enable-lived-self-review':
                if (event['kind']!='implementation-change' or obj._llm_self_review_enabled or
                        payload.get('model')!='llm-lived-self-review-v1' or
                        not nonempty(payload.get('actor')) or
                        not supports(obj._mind.version,'reflective_trials')):
                    raise ValueError('invalid lived self-review adoption history')
                obj._llm_self_review_enabled=True
                obj._llm_self_review_revision=1
            if payload.get('operation')=='improve-lived-self-review':
                if (event['kind']!='implementation-change' or not obj._llm_self_review_enabled or
                        obj._llm_self_review_revision!=1 or payload.get('model')!='llm-lived-self-review-v2' or
                        not nonempty(payload.get('actor'))):
                    raise ValueError('invalid self-review improvement history')
                obj._llm_self_review_revision=2
            obj._memory.observe(event)
            obj._mind.observe(event)
        from garden import plots
        from individual import BASE_OBJECTS
        expected_objects=BASE_OBJECTS|added_devices|(set(plots(current_pack)) if garden_adoption else set())
        if set(host.objects)!=expected_objects:raise ValueError('object additions differ from history')
        if ('nutrition' in (host.world or {}).get('garden',{}))!=nutrition_adoption:raise ValueError('stored food differs from adoption history')
        if ('garden' in (host.world or {}))!=garden_adoption:raise ValueError('garden differs from adoption history')
        if (host.world or {}).get('garden',{}).get('model')!=garden_model:raise ValueError('garden model differs from implementation history')
        if host.world and host.world['pack_sha256']!=current_pack:raise ValueError('map pack differs from adoption history')
        if (host.world or {}).get('home_region')!=home_region:raise ValueError('home town differs from history')
        if (host.world is not None)!=(world_adoption is not None):
            raise ValueError('world body differs from adoption history')
        if allocated_capacity is not None and allocated_capacity!=capacity:
            raise ValueError('memory budget header differs from allocation history')
        if experienced_ticks != host.time:
            raise ValueError('history does not reach host clock')
        if active_branch != lineage['branch_id'] or active_context != lineage['context']:
            raise ValueError('history does not match current branch')
        if parent is not None:
            if (last_transition is None or last_transition['tick'] != parent['tick'] or
                last_transition['payload'] != {'parent_branch_id': parent['branch_id'],
                    'parent_checkpoint_sha256': parent['checkpoint_sha256'], 'purpose': lineage['purpose']}):
                raise ValueError('branch receipt differs from lineage')
        elif last_transition is not None:
            raise ValueError('branch history lacks a parent')
        if obj._host.rest_enabled != supports(obj._mind.version,'rest'):
            raise ValueError('rest body and developmental implementation disagree')
        if obj._host.hold_enabled != supports(obj._mind.version,'recovery_investigation'):
            raise ValueError('hold body and developmental implementation disagree')
        return obj

    def fork(self, *, purpose):
        if not nonempty(purpose):
            raise ValueError('test branch requires a purpose')
        self._room()
        state = self.snapshot()
        child = self.restore(state)
        parent_branch = self._lineage['branch_id']
        source_digest = digest(state)
        child._lineage = {'individual_id': self.identity, 'branch_id': str(uuid.uuid4()),
                          'parent': {'branch_id': parent_branch,
                                     'checkpoint_sha256': source_digest, 'tick': self.time},
                          'context': 'test', 'purpose': purpose}
        child._append('branch', {'parent_branch_id': parent_branch,
                      'parent_checkpoint_sha256': source_digest, 'purpose': purpose})
        return child

    def save(self, path):
        # Exclusive creation preserves the prior checkpoint. The caller chooses
        # a new path for each durable version; no live checkpoint is overwritten.
        import os
        path = Path(path)
        encoded = canonical(self.snapshot()) + '\n'
        with path.open('x') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @classmethod
    def load(cls, path):
        return cls.restore(json.loads(Path(path).read_text()))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--new', action='store_true', help='create a separate research individual')
    source.add_argument('--resume', type=Path, help='continue an existing envelope')
    source.add_argument('--fork', type=Path, help='create an explicit test branch')
    parser.add_argument('--purpose', help='required for a test fork')
    parser.add_argument('--program', type=Path, default=Path(__file__).resolve().parents[2] /
                        'research/docking-station-20261103/resources/chichi-brain-program.json')
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--dream', action='store_true', help='record offline learned-model rehearsal')
    parser.add_argument('--learned-recall', action='store_true', help='adopt experience-derived sensory recall')
    parser.add_argument('--guidance-goal', help='answer a recorded practice-help request')
    parser.add_argument('--additional-attempts', type=int, help='bounded practice advice, one to eight attempts')
    parser.add_argument('--teacher', help='attributed source of the advice')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--steps', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True, help='new checkpoint path; never overwrites')
    args = parser.parse_args()
    supplied=(args.guidance_goal is not None,args.additional_attempts is not None,args.teacher is not None)
    if any(supplied) and not all(supplied):
        parser.error('guidance requires --guidance-goal, --additional-attempts and --teacher together')
    if args.steps < 0:
        parser.error('--steps must be nonnegative')
    if args.output.exists():
        parser.error('output already exists; choose a new checkpoint path')
    if args.fork and not args.purpose:
        parser.error('--fork requires --purpose')
    if args.new:
        companion = ContinuingCompanion(args.program, seed=args.seed)
    else:
        companion = ContinuingCompanion.load(args.resume or args.fork)
        if args.fork:
            companion = companion.fork(purpose=args.purpose)
    if args.learned_recall:
        companion.enable_recall(actor='cli-operator')
    if args.development:
        companion.enable_development(actor='cli-operator')
    if args.guidance_goal is not None:
        try:
            companion.offer_practice_guidance(args.guidance_goal,additional_attempts=args.additional_attempts,source=args.teacher)
        except ValueError as exc:
            parser.error(str(exc))
    if len(companion._events) + args.steps + int(args.dream) > companion._capacity:
        parser.error('requested steps exceed retained experience capacity')
    for _ in range(args.steps):
        companion.tick()
    if args.dream:
        companion.dream()
    companion.save(args.output)
    snapshot = companion.snapshot()
    print(json.dumps({'identity': companion.identity, 'lineage': snapshot['lineage'],
                      'tick': companion.time, 'retained_events': len(snapshot['events']),
                      'intention': companion.intention(), 'self_review':companion.self_review(),
                      'checkpoint': str(args.output), 'sha256': digest(snapshot),
                      'scope': 'research host continuity; no cognitive self-understanding claim'}))


if __name__ == '__main__':
    main()
