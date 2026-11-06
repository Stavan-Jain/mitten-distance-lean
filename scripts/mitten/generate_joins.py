#!/usr/bin/env python3
"""Emit shared-block join certificates; all facts are rechecked in Lean."""
import argparse
from collections import defaultdict
from pathlib import Path
import json


def generate(data: Path, output: Path) -> None:
    census = json.loads(data.read_text())
    for side in ('X', 'Z'):
        tables = []
        for i in (0, 1):
            g = defaultdict(list)
            for u, w, t in census[f'{side}{i}']['sols']:
                if u or w or t:
                    assert 0 <= u < 2**30 and 0 <= w < 2**30 and 0 <= t < 2**30
                    g[t].append(u | w << 30 | t << 60)
            for values in g.values():
                values.sort()
            tables.append(g)
        keys = sorted(tables[0].keys() | tables[1].keys())
        lines = [
            '/-',
            'GENERATED FILE — DO NOT HAND-EDIT',
            'Generator: mitten-distance-lean:scripts/mitten/generate_joins.py',
            'Input: scripts/mitten/inputs/m4_triples.json',
            'Regenerate: python3 scripts/mitten/generate.py',
            '  --root /path/to/mitten-distance-lean --force',
            'All flattening, ordering, and join checks are kernel verified.',
            '-/',
            '',
            'import MittenDistance.M150.FloorData',
            'import MittenDistance.M150.GroupedJoin',
            '',
            'namespace Quantum.Stabilizer.Homological.LP.M150',
            '',
            'set_option maxRecDepth 65536',
            '',
            '/-- The two censuses grouped by their common shared-block mask. -/',
            f'def joinBuckets{side} : List JoinBucket := [',
        ]
        for j, key in enumerate(keys):
            lines.append(f'  ⟨{key},')
            for i in (0, 1):
                values = tables[i].get(key, [])
                suffix = ',' if i == 0 else ('⟩,' if j+1 < len(keys) else '⟩]')
                if not values:
                    lines.append('    []' + suffix)
                else:
                    for start in range(0, len(values), 2):
                        prefix = '    [' if start == 0 else '     '
                        part = ', '.join(map(str, values[start:start+2]))
                        end = ']' + suffix if start+2 >= len(values) else ','
                        lines.append(prefix + part + end)
        lines += [
            '',
            '/-- Grouping preserves the first census exactly. -/',
            f'private theorem joinLeft{side} : joinLeft joinBuckets{side} = cls{side}0 := by',
            '  decide +kernel',
            '',
            '/-- Grouping preserves the second census exactly. -/',
            f'private theorem joinRight{side} : joinRight joinBuckets{side} = cls{side}1 := by',
            '  decide +kernel',
            '',
            '/-- Every compatible low-weight pair joins to a generator row. -/',
            f'private theorem joinBuckets{side}_checked :',
            f'    checkJoinBuckets rows{side}pk 0 joinBuckets{side} = true := by',
            '  decide +kernel',
            '',
            '/-- The complete join is certified through shared-block grouping. -/',
            f'theorem checkJoin_{side} : checkJoin cls{side}0 cls{side}1 rows{side}pk = true := by',
            f'  rw [← joinLeft{side}, ← joinRight{side}]',
            f'  exact checkJoin_of_buckets rows{side}pk joinBuckets{side} joinBuckets{side}_checked',
            '',
            f'#print axioms checkJoin_{side}',
            '',
            'end Quantum.Stabilizer.Homological.LP.M150',
            '',
        ]
        p = output / f'Join{side}.lean'
        p.write_text('\n'.join(lines))
        print(f'{side}: {len(keys)} buckets; wrote {p}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if not args.force and any((args.out / f'Join{s}.lean').exists() for s in ('X', 'Z')):
        parser.error('generated joins already exist; pass --force to regenerate')
    args.out.mkdir(parents=True, exist_ok=True)
    generate(args.data, args.out)
