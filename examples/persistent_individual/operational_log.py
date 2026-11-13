"""Small append-only local operational receipts; no claim about unobserved exits."""
import datetime
import json
import os
from pathlib import Path


def append_receipt(path, event, **fields):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'event':event,**fields}
    with path.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(payload,sort_keys=True,allow_nan=False)+'\n')
        stream.flush();os.fsync(stream.fileno())
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)
