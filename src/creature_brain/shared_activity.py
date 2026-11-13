"""One companion channel: grounded invitations, participation and quiet time.

Presence/participation are explicitly supplied reports, not biometric recognition.
Authored initial timing is adapted after a declined invitation. No partner ranking.
"""
from copy import deepcopy

class SharedActivity:
    def __init__(self):
        self.available_until=-1
        self.presence_event=None
        self.invitations=[]
        self.next_invitation_tick=0
        self.last_tick=0
        self.history_sensitive=False

    def available(self):return self.last_tick<self.available_until

    def observe(self,record,goals):
        payload=record['payload'];operation=payload.get('operation');self.last_tick=record['tick']
        if record['kind']=='supplied-information' and operation=='companion-availability':
            if type(payload.get('available')) is not bool or payload.get('source')!='companion-person':
                raise ValueError('invalid companion availability report')
            self.available_until=record['tick']+64 if payload['available'] else -1
            self.presence_event=record['sequence']
        elif record['kind']=='communication' and operation=='invite-shared-activity':
            if payload!=self.invitation(goals):raise ValueError('invitation does not match shared activity evidence')
            self.invitations.append({**deepcopy(payload),'event':record['sequence'],'status':'offered'})
            self.next_invitation_tick=record['tick']+32
        elif record['kind']=='supplied-information' and operation=='shared-activity-response':
            if payload.get('source')!='companion-person':raise ValueError('response requires the companion channel')
            invitation=self.validate_response(payload['invitation_event'],payload['response'])
            invitation.update(status='participating' if payload['response']=='join' else 'declined',response_event=record['sequence'])
            if payload['response']=='decline':
                prior=[]
                if self.history_sensitive:
                    for item in reversed(self.invitations):
                        if item['status']=='completed-with-reported-participation':break
                        if item['status']=='declined':prior.append(item['response_event'])
                delay=128*min(4,max(1,len(prior)))
                self.next_invitation_tick=record['tick']+delay
                if self.history_sensitive:
                    invitation['timing_review']={'decline_events':list(reversed(prior)),
                        'delay_ticks':delay,'basis':'reported-declines-since-last-completed-participation',
                        'unknown':'reason for declining; no preference or emotion inferred'}
        for invitation in self.invitations:
            if invitation['status'] not in ('offered','participating'):continue
            goal=next((g for g in goals if g['id']==invitation['goal_id']),None)
            if not self.available():invitation['status']='closed-person-unavailable'
            elif goal is None or goal['status']!='active':
                invitation['status']=('completed-with-reported-participation' if goal and goal['status']=='demonstrated-visible-effect' and invitation['status']=='participating' else 'closed-activity-ended')
                invitation['outcome_event']=record['sequence']

    def validate_response(self,event,response):
        if type(event) is not int or response not in ('join','decline'):
            raise ValueError('response must name an invitation and join or decline')
        invitation=next((i for i in self.invitations if i['event']==event),None)
        if invitation is None or invitation['status']!='offered' or not self.available():
            raise ValueError('invitation is no longer available')
        return invitation

    def invitation(self,goals):
        if not self.available() or self.last_tick<self.next_invitation_tick:return None
        if any(i['status'] in ('offered','participating') for i in self.invitations):return None
        for goal in goals:
            evidence=goal.get('practice_evidence')
            if (goal['status']!='active' or goal['objective']!='revisit-familiar-activity' or
                not evidence or evidence['teacher']!='companion-person' or
                any(i['goal_id']==goal['id'] for i in self.invitations)):continue
            return {'operation':'invite-shared-activity','goal_id':goal['id'],'target':goal['target'],
                'origin':'retained-successful-shared-teaching','presence_event':self.presence_event,
                'guidance_event':evidence['guidance_event'],'teaching_outcome_event':evidence['source_event'],
                'message':'I am returning to an activity your teaching helped me learn. Would you like to watch together?',
                'participation_basis':'person-reported availability; no presence recognition'}
        return None

    def review(self):
        return {'companion_available':self.available(),'shared_invitations':deepcopy(self.invitations),
            'next_invitation_tick':self.next_invitation_tick,
            'relationship_scope':'one reported companion channel; no partner selection or recognition'}
