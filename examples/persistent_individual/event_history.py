"""Append-only history with one verified archive block resident at a time."""
from collections.abc import Sequence
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

SEGMENT_EVENTS=128

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False)

def digest(value):
    if isinstance(value,ArchivedHistory):return value.history_digest()
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def history_hash(events):
    result=hashlib.sha256(b'[')
    for i,event in enumerate(events):
        if i:result.update(b',')
        result.update(canonical(event).encode())
    return result

def finished_hash(value):
    copy=value.copy();copy.update(b']');return copy.hexdigest()

class ArchivedHistory(Sequence):
    def __init__(self,directory,segments,tail,expected_digest):
        self.directory=Path(directory).resolve()
        self._segments=deepcopy(segments);self._tail=deepcopy(tail)
        self._verified={};self._cached_index=None;self._cached_records=[]
        self.validate_references(self._segments)
        if not isinstance(tail,list) or len(tail)>=SEGMENT_EVENTS:raise ValueError('history tail was not segmented')
        self._hash=history_hash(self)
        if self.history_digest()!=expected_digest:raise ValueError('complete history digest differs')
        self._committed_count=len(self);self._committed_digest=expected_digest

    @staticmethod
    def validate_references(segments):
        for i,segment in enumerate(segments):
            if (not isinstance(segment,dict) or set(segment)!={'sha256','start','count'} or
                type(segment['start']) is not int or segment['start']!=i*SEGMENT_EVENTS or
                type(segment['count']) is not int or segment['count']!=SEGMENT_EVENTS or
                not isinstance(segment['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',segment['sha256'])):
                raise ValueError('invalid history segment reference')

    @property
    def archived_count(self):return len(self._segments)*SEGMENT_EVENTS

    @property
    def segments(self):return deepcopy(self._segments)

    @property
    def resident_events(self):return len(self._tail)+len(self._cached_records)

    def __len__(self):return self.archived_count+len(self._tail)

    def _file_status(self,index):
        file=self.directory/f"{self._segments[index]['sha256']}.json"
        try:stat=file.stat()
        except FileNotFoundError as exc:raise ValueError('required history segment is missing') from exc
        return file,(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)

    def _read(self,index):
        file,status=self._file_status(index)
        if index==self._cached_index and self._verified.get(index)==status:return self._cached_records
        raw=file.read_bytes();segment=self._segments[index]
        if hashlib.sha256(raw).hexdigest()!=segment['sha256']:raise ValueError('history segment digest differs')
        records=json.loads(raw)
        if not isinstance(records,list) or len(records)!=SEGMENT_EVENTS:raise ValueError('history segment count differs')
        self._verified[index]=status;self._cached_index=index;self._cached_records=records
        return records

    def verify_archives(self):
        for i in range(len(self._segments)):
            _,status=self._file_status(i)
            if self._verified.get(i)!=status:self._read(i)

    def __getitem__(self,index):
        if isinstance(index,slice):return [self[i] for i in range(*index.indices(len(self)))]
        if index<0:index+=len(self)
        if not 0<=index<len(self):raise IndexError(index)
        if index<self.archived_count:
            value=self._read(index//SEGMENT_EVENTS)[index%SEGMENT_EVENTS]
        else:value=self._tail[index-self.archived_count]
        # A caller can inspect an event but cannot silently mutate retained history.
        return deepcopy(value)

    def append(self,event):
        encoded=canonical(event)
        if not isinstance(event,dict) or event.get('sequence')!=len(self):raise ValueError('event does not extend history')
        if len(self):self._hash.update(b',')
        self._hash.update(encoded.encode());self._tail.append(json.loads(encoded))

    def history_digest(self):return finished_hash(self._hash)

    def prefix_digest(self,count):
        if count==len(self):return self.history_digest()
        if count==self._committed_count:return self._committed_digest
        return finished_hash(history_hash(self[i] for i in range(count)))

    def committed(self,segments):
        self.validate_references(segments)
        old=len(self._segments)
        if segments[:old]!=self._segments or len(segments)*SEGMENT_EVENTS>len(self):raise ValueError('archive does not extend history')
        previous=self._segments
        self._segments=deepcopy(segments)
        try:
            for i in range(old,len(segments)):
                offset=(i-old)*SEGMENT_EVENTS
                if self._read(i)!=self._tail[offset:offset+SEGMENT_EVENTS]:raise ValueError('published history differs from memory')
        except BaseException:
            self._segments=previous;self._cached_index=None;self._cached_records=[]
            self._verified={i:value for i,value in self._verified.items() if i<old}
            raise
        self._tail=self._tail[(len(segments)-old)*SEGMENT_EVENTS:]
        self._committed_count=len(self);self._committed_digest=self.history_digest()
