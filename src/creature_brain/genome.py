"""Bounded, read-only decoder for supplied dna3 brain configurations.

The binary layout is corroborated by archived CreatureLabs CDN format25 and
local genotype/GNO records. Values remain raw bytes; the runtime owns codon
range wrapping and expression. No game data is bundled with this module.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct


class GenomeError(ValueError):
    """Malformed or unsupported supplied genome."""


_HEADER = ('type', 'subtype', 'id', 'generation', 'switch_on_time', 'flags', 'mutability', 'variant')
# Known body sizes let the parser advance without treating arbitrary gene-like
# bytes inside a body as delimiters.
_SIZES = {(0,0):121,(0,1):5,(0,2):128,(1,0):8,(1,1):8,(1,2):9,
          (1,3):256,(1,4):2,(1,5):15,(2,0):13,(2,1):65,(2,2):3,
          (2,3):17,(2,4):9,(2,5):9,(2,6):2,(2,7):2,(2,8):11,(3,0):5}
_LOBE = ('lobe','update_time','x','y','width','height','red','green','blue',
         'winner_takes_all','tissue','init_rule_always','padding','init_rule','update_rule')
_TRACT = ('update_time','source_lobe','source_lower','source_upper','source_connections',
          'destination_lobe','destination_lower','destination_upper','destination_connections',
          'migrates','random_connections','source_variable','destination_variable',
          'init_rule_always','padding','init_rule','update_rule')
_INSTINCT = ('lobe0','cell0','lobe1','cell1','lobe2','cell2','action',
             'reinforcement_drive_index','reinforcement_amount')


def codon(value: int, lower: int, upper: int) -> int:
    """Native Genome::GetCodon00424c90 wraps out-of-range bytes, not clamps."""
    if type(value) is not int or not 0 <= value <= 255:
        raise GenomeError('a codon must be a byte')
    return value if lower <= value <= upper else value % (upper - lower + 1) + lower


def expressed(header: dict, age_stage: int, sex: str) -> bool:
    """Native00424d10 expression: organ age bypass and alternative sex flags.

    Variant0 is the native wildcard. A nonzero folded variant needs a selected
    creature variant, which this reference API does not currently provide.
    """
    flags = header['flags']
    age_matches = ((header['type'], header['subtype']) == (3, 0)
                   or header['switch_on_time'] <= age_stage)
    sex_flags = flags & 24
    sex_matches = (not sex_flags or (flags & 8 and sex == 'male')
                   or (flags & 16 and sex == 'female'))
    if not (age_matches and not flags & 0x20 and sex_matches):
        return False
    if codon(header['variant'], 0, 8):
        raise GenomeError('nonzero gene variant requires an explicitly qualified creature variant')
    return True


@dataclass(frozen=True)
class GenomeDefinition:
    records: tuple[dict, ...]
    source_sha256: str

    def to_dict(self) -> dict:
        return {'source_sha256': self.source_sha256, 'records': list(self.records)}


def _definition(data: dict, digest: str) -> GenomeDefinition:
    if not isinstance(data, dict) or not isinstance(data.get('records'), list):
        raise GenomeError('brain program requires a records array')
    if len(data['records']) > 100_000:
        raise GenomeError('too many genome records')
    selected = []
    for record in data['records']:
        if not isinstance(record, dict):
            raise GenomeError('gene records must be objects')
        if record.get('kind') not in ('brain_lobe', 'brain_tract', 'instinct'):
            continue
        header = record.get('header')
        if not isinstance(header, dict) or any(type(header.get(k)) is not int or not 0 <= header[k] <= 255 for k in _HEADER):
            raise GenomeError('gene header requires eight byte fields')
        fields = record.get('fields')
        if not isinstance(fields, dict):
            raise GenomeError('gene requires fields')
        # Detached JSON keeps caller-owned metadata out of the live configuration.
        fields = json.loads(json.dumps(fields, allow_nan=False))
        for name in ('init_rule', 'update_rule'):
            if record['kind'] == 'instinct':
                break
            rule = fields.get(name)
            if not isinstance(rule, dict) or not isinstance(rule.get('raw_hex'), str):
                raise GenomeError('rule requires48raw bytes')
            try:
                raw = bytes.fromhex(rule['raw_hex'])
            except ValueError as error:
                raise GenomeError('invalid rule hex') from error
            if len(raw) != 48:
                raise GenomeError('rule requires48raw bytes')
            fields[name] = {'raw_hex': raw.hex()}
        fields.pop('padding', None)
        selected.append({'kind': record['kind'], 'header': dict(header), 'fields': fields})
    if not selected:
        raise GenomeError('no brain records found')
    source = data.get('source_sha256', data.get('sha256', digest))
    if not isinstance(source, str) or len(source) != 64 or any(c not in '0123456789abcdef' for c in source):
        raise GenomeError('source digest must be lowercase SHA-256')
    return GenomeDefinition(tuple(selected), source)


def definition_from_dict(data: dict) -> GenomeDefinition:
    return _definition(data, hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest())


def load_genome(path: str | Path) -> GenomeDefinition:
    path = Path(path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise GenomeError('genome/configuration exceeds16MiB')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if raw[:4] != b'dna3':
        try:
            return _definition(json.loads(raw), digest)
        except (ValueError, TypeError, UnicodeDecodeError) as error:
            raise GenomeError(f'invalid supplied genome/configuration: {error}') from error
    records = []
    pos = 4
    while raw[pos:pos+4] != b'gend':
        if raw[pos:pos+4] != b'gene' or pos + 12 > len(raw):
            raise GenomeError(f'invalid gene header at byte{pos}')
        h = dict(zip(_HEADER, raw[pos+4:pos+12])); pos += 12
        size = _SIZES.get((h['type'], h['subtype']))
        if size is None or pos + size > len(raw):
            raise GenomeError(f'unknown or truncated gene at byte{pos}')
        key = h['type'], h['subtype']
        if key == (0,0):
            kind = 'brain_lobe'
            fields = dict(zip(_LOBE, struct.unpack_from('>4sHHH8B7s48s48s', raw, pos)))
        elif key == (0,2):
            kind = 'brain_tract'
            fields = dict(zip(_TRACT, struct.unpack_from('>H4s3H4s3H5B5s48s48s', raw, pos)))
        elif key == (2,5):
            kind = 'instinct'
            fields = dict(zip(_INSTINCT, raw[pos:pos+size]))
        else:
            pos += size
            continue
        for name, value in list(fields.items()):
            if name in ('init_rule', 'update_rule'):
                fields[name] = {'raw_hex': value.hex()}
            elif name in ('lobe', 'source_lobe', 'destination_lobe'):
                try: fields[name] = value.decode('ascii')
                except UnicodeDecodeError as error: raise GenomeError('non-ASCII lobe token') from error
        fields.pop('padding', None)
        records.append({'kind': kind, 'header': h, 'fields': fields})
        pos += size
    if any(raw[pos+4:]):
        raise GenomeError('nonzero bytes after genome end')
    return _definition({'records': records}, digest)
