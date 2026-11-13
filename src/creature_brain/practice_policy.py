"""Small executable policy boundary for evaluated self-directed revision.

The accepted language is one Python function returning one counter comparison, optionally with a threshold conditional on observed progress.
It has no calls, imports, attribute access, loops or host access. This is limited
program synthesis, not arbitrary source editing or general code intelligence.
"""
import ast
import hashlib


def source_for(counter='trials',limit=3):
    if counter not in ('trials','no_change_streak','progress_sensitive','observed_gap_sensitive') or type(limit) is not int or not 1<=limit<=32:
        raise ValueError('invalid practice policy specification')
    if counter=='observed_gap_sensitive':
        return f'def should_stop(trials, changes, no_change_streak, observed_gap):\n    return no_change_streak >= ((observed_gap + {limit} if observed_gap + {limit} < 32 else 32) if observed_gap > 0 else 3)\n'
    if counter=='progress_sensitive':
        return f'def should_stop(trials, changes, no_change_streak):\n    return no_change_streak >= ({limit} if changes > 0 else 3)\n'
    return f'def should_stop(trials, changes, no_change_streak):\n    return {counter} >= {limit}\n'


class PracticePolicy:
    def __init__(self,source=None):
        self.source=source_for() if source is None else source
        if not isinstance(self.source,str) or len(self.source)>512:
            raise ValueError('invalid policy source')
        try:tree=ast.parse(self.source)
        except SyntaxError as exc:raise ValueError('invalid policy syntax') from exc
        expected=None
        for counter in ('trials','no_change_streak','progress_sensitive','observed_gap_sensitive'):
            for limit in range(1,33):
                candidate=ast.parse(source_for(counter,limit))
                if ast.dump(tree)==ast.dump(candidate):expected=(counter,limit);break
            if expected:break
        if expected is None:
            raise ValueError('policy is outside the supported executable language')
        self.counter,self.limit=expected
        self.sha256=hashlib.sha256(self.source.encode()).hexdigest()
        namespace={'__builtins__':{}}
        exec(compile(tree,'<creature-practice-policy>','exec'),namespace)
        self._function=namespace['should_stop']

    def should_stop(self, *, trials, changes, no_change_streak, observed_gap=0):
        if any(type(x) is not int or x<0 for x in (trials,changes,no_change_streak,observed_gap)):
            raise ValueError('policy inputs must be nonnegative observed counts')
        if self.counter=='observed_gap_sensitive':return self._function(trials,changes,no_change_streak,observed_gap)
        return self._function(trials,changes,no_change_streak)

    def describe(self):
        return {'source':self.source,'sha256':self.sha256,'stopping_counter':self.counter,'limit':self.limit}
