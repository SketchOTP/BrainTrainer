"""Exclusive checkpoint owner; immutable history segments and atomic current state.

Portable envelopes remain the ContinuingCompanion contract. Only this owner reads
or writes the directory format. Archives are never pruned by normal saves.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid
from continuing_companion import ContinuingCompanion,SCHEMA,canonical,digest
from event_history import ArchivedHistory,SEGMENT_EVENTS

STORE_SCHEMA='creature-brain-segmented-habitat-v1'

def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def write_exclusive(path,data):
    with path.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())

class HabitatStore:
    def __init__(self,directory):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.current=self.directory/'current.json';self.previous=self.directory/'previous.json'
        self.history=self.directory/'history'
        self.lock=(self.directory/'individual.lock').open('a')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:
            self.lock.close();raise

    @staticmethod
    def read_checkpoint(path):
        path=Path(path);data=json.loads(path.read_text())
        if not isinstance(data,dict):raise ValueError('expected a checkpoint object')
        if data.get('schema')==SCHEMA:return ContinuingCompanion.restore(data)
        if data.get('schema')!=STORE_SCHEMA:raise ValueError('unknown habitat checkpoint format')
        state=data.get('companion');segments=data.get('segments')
        if not isinstance(state,dict) or not isinstance(segments,list) or not isinstance(state.get('events'),list):
            raise ValueError('invalid segmented checkpoint')
        count=data.get('event_count');capacity=state.get('event_capacity')
        if (type(count) is not int or type(capacity) is not int or not 1<=count<=capacity or
            len(segments)*SEGMENT_EVENTS+len(state['events'])!=count):
            raise ValueError('invalid history layout or capacity')
        history=ArchivedHistory(path.parent/'history',segments,state['events'],data.get('history_sha256'))
        return ContinuingCompanion._restore_history(state,history)

    def load(self,*,previous=False):
        return self.read_checkpoint(self.previous if previous else self.current)

    def export(self,path):
        self.load().save(path)

    def save(self,creature):
        state=creature.checkpoint_header();events=creature._events
        if isinstance(events,ArchivedHistory):events.verify_archives()
        if self.current.exists():
            prior=json.loads(self.current.read_text())
            if prior.get('schema')==SCHEMA:
                old_state=prior;old_count=len(prior['events']);old_digest=digest(prior['events'])
            elif prior.get('schema')==STORE_SCHEMA:
                old_state=prior['companion'];old_count=prior['event_count'];old_digest=prior['history_sha256']
            else:raise ValueError('cannot replace unknown checkpoint format')
            if (state['lineage']!=old_state['lineage'] or type(old_count) is not int or
                not 0<=old_count<=len(events) or
                (events.prefix_digest(old_count) if isinstance(events,ArchivedHistory) else digest(events[:old_count]))!=old_digest):
                raise ValueError('save would replace identity, branch or prior history')
        self.history.mkdir(exist_ok=True)
        attached=isinstance(events,ArchivedHistory) and events.directory==self.history.resolve()
        references=events.segments if attached else []
        for start in range(len(references)*SEGMENT_EVENTS,len(events)-SEGMENT_EVENTS+1,SEGMENT_EVENTS):
            raw=(canonical(events[start:start+SEGMENT_EVENTS])+'\n').encode()
            sha=hashlib.sha256(raw).hexdigest();file=self.history/f'{sha}.json'
            if file.exists():
                if file.read_bytes()!=raw:raise ValueError('existing history segment differs; preserve recovery evidence')
            else:
                temporary=self.history/f'.pending-{uuid.uuid4().hex}.json'
                write_exclusive(temporary,raw)
                os.link(temporary,file)
                temporary.unlink()
            references.append({'sha256':sha,'start':start,'count':SEGMENT_EVENTS})
        sync_directory(self.history)
        history_sha=digest(events);state['events']=events[len(references)*SEGMENT_EVENTS:]
        document={'schema':STORE_SCHEMA,'companion':state,'segments':references,
            'event_count':len(events),'history_sha256':history_sha}
        token=uuid.uuid4().hex;pending=self.directory/f'pending-{token}.json'
        write_exclusive(pending,(canonical(document)+'\n').encode())
        if self.current.exists():
            backup=self.directory/f'prior-{token}.json';os.link(self.current,backup);os.replace(backup,self.previous)
        os.replace(pending,self.current);sync_directory(self.directory)
        if attached:events.committed(references)
        else:creature._events=ArchivedHistory(self.history,references,state['events'],history_sha)

    def close(self):self.lock.close()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description='Export a segmented habitat checkpoint as a portable complete envelope.')
    p.add_argument('--checkpoint',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();HabitatStore.read_checkpoint(args.checkpoint).save(args.output)
