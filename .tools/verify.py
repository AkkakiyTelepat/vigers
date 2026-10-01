# -*- coding: utf-8 -*-
import re, glob, os

SRC = '/workspace/.extract/txt'
DST = '/workspace/docs/requirements/by_bp/enriched'

def norm(t):
    # collapse all whitespace for robust containment check
    return re.sub(r'\s+', '', t)

bad = []
for src in sorted(glob.glob(os.path.join(SRC, '*.txt'))):
    name = re.sub(r'\.md$', '', os.path.basename(src)[:-4])
    raw = open(src, encoding='utf-8', errors='replace').read()
    dst_file = os.path.join(DST, name + '.md')
    if not os.path.exists(dst_file):
        bad.append((name, 'MISSING FILE'))
        continue
    doc = open(dst_file, encoding='utf-8').read()
    ndoc, nraw = norm(doc), norm(raw)
    if nraw not in ndoc:
        # find first divergence to report size of loss
        bad.append((name, f'LAYER C INCOMPLETE (src {len(nraw)} norm chars)'))
print('checked:', len(glob.glob(os.path.join(SRC,'*.txt'))))
print('problems:', len(bad))
for b in bad: print(' -', *b)
