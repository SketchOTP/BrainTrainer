"""Feed a default brain JSON frames on stdin and emit its choices on stdout.

The host owns sensors, action execution, feedback, time, and the saved file.
The program must be an owner-supplied, supported genome or normalized program.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from creature_brain import DefaultBrain


def parse_inputs(inputs):
    if inputs is None:
        return None
    if not isinstance(inputs, dict):
        raise ValueError('inputs must map lobe names to neuron inputs')
    result = {}
    for name, values in inputs.items():
        if not isinstance(values, dict):
            result[name] = values
            continue
        converted = {}
        for raw_index, value in values.items():
            index = int(raw_index)
            if str(index) != raw_index:
                raise ValueError(f'noncanonical neuron index {raw_index!r}')
            converted[index] = value
        result[name] = converted
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--program', type=Path, help='owner-supplied .gen or normalized program')
    source.add_argument('--restore', type=Path, help='saved brain checkpoint JSON')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--age-stage', type=int, default=3)
    parser.add_argument('--sex', choices=('female', 'male'), default='female')
    parser.add_argument('--save', type=Path, help='write a brain checkpoint after the last frame')
    args = parser.parse_args()
    if args.restore is not None:
        brain = DefaultBrain.from_dict(json.loads(args.restore.read_text()))
    else:
        brain = DefaultBrain.from_file(args.program, seed=args.seed,
                                       age_stage=args.age_stage, sex=args.sex)
    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        try:
            frame = json.loads(line)
            if not isinstance(frame, dict) or set(frame) - {'inputs', 'chemicals'}:
                raise ValueError('frame must contain only inputs and/or chemicals')
            # JSON object keys are strings; convert neuron indexes at this boundary.
            inputs = parse_inputs(frame.get('inputs'))
            result = brain.tick(inputs, frame.get('chemicals'))
            print(json.dumps(asdict(result), allow_nan=False), flush=True)
        except (AttributeError, TypeError, ValueError) as error:
            raise SystemExit(f'frame {line_number}: {error}') from error
    if args.save is not None:
        args.save.write_text(json.dumps(brain.to_dict(), allow_nan=False))


if __name__ == '__main__':
    main()
