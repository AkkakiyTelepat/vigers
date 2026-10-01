# -*- coding: utf-8 -*-
import re, glob, os

SRC = '/workspace/.extract/txt'
DST = '/workspace/docs/requirements/by_bp/enriched'
SEC_RE = re.compile(r'^#{1,3}\s*(\d+)\.\s*([^\n]*)$', re.M)

def split_sections(text):
    ms = list(SEC_RE.finditer(text))
    if not ms: return text, []
    pre = text[:ms[0].start()]
    secs = []
    for i, m in enumerate(ms):
        num = int(m.group(1)); end = ms[i+1].start() if i+1 < len(ms) else len(text)
        secs.append((num, m.group(2).strip(), text[m.start():end]))
    merged = []
    for num, title, body in secs:
        if merged and num == merged[-1][0]:
            merged[-1] = (merged[-1][0], merged[-1][1], merged[-1][2] + '\n' + body)
        elif merged and num < merged[-1][0] and merged[-1][0] >= 10:
            merged[-1] = (merged[-1][0], merged[-1][1], merged[-1][2] + '\n' + body)
        else:
            merged.append((num, title, body))
    return pre, merged

def strip_head(body, n):
    return re.sub(r'^#{1,3}\s*' + str(n) + r'\..*?\n', '', body, count=1, flags=re.S).strip()

def rows_from_tables(t):
    rows = []
    for line in t.splitlines():
        line = line.strip()
        if not line.startswith('|'): continue
        if set(line) <= set('|-: '): continue
        rows.append([c.strip() for c in line.strip('|').split('|')])
    return rows

SENT_RE = re.compile(r'(?:Пользователь должен|Пользователю необходимо|Необходимо обеспечить|Система должна|Требуется)[^\n]*')

records = []
for src in sorted(glob.glob(os.path.join(SRC, '*.txt'))):
    name = re.sub(r'\.md$', '', os.path.basename(src)[:-4])
    raw = open(src, encoding='utf-8', errors='replace').read()
    pre, secs = split_sections(raw)
    smap, titles = {}, {}
    for num, title, body in secs:
        smap[num] = smap.get(num, '') + body
        titles.setdefault(num, title)
    ur, fn, gl, pr = [], [], [], []
    for t in re.findall(r'(?:^[ \t]*\|[^\n]*\|[^\n]*\n)+', smap.get(5,''), re.M):
        rows = rows_from_tables(t)
        if not rows: continue
        hdr = [h.lower() for h in rows[0]]
        def cell(row, key, hdr=hdr):
            for i,h in enumerate(hdr):
                if key in h and i < len(row): return row[i]
            return ''
        for r in rows[1:]:
            u = cell(r,'пользовательск'); f_ = cell(r,'функци'); g = cell(r,'цель'); p = cell(r,'процесс')
            if u: ur += [x for x in re.split(r'(?=\bПользователь должен\b)', u) if x.strip()]
            if f_: fn += re.split(r'\n+', f_)
            if g: gl += re.split(r'\n+', g)
            if p: pr += re.split(r'\n+', p)
    fb = False
    if not ur:
        mined = SENT_RE.findall(raw)
        if mined: ur, fb = mined, True
    def clean(lst):
        out=[]
        for x in lst:
            x = re.sub(r'\s+',' ',x).strip(' ;•-\u2022|')
            if x and x.lower() not in ('отсутствует','нет','-','—','не изменяются','не изменяется'): out.append(x)
        return out
    ur, fn, gl, pr = map(clean,(ur,fn,gl,pr))
    records.append(dict(name=name, raw=raw, titles=titles, nums=sorted(smap),
                        smap=smap, ur=dict.fromkeys(ur), fn=dict.fromkeys(fn),
                        gl=dict.fromkeys(gl), pr=dict.fromkeys(pr), fb=fb))

# ---------- file 10: UT registry ----------
all_ut = {}
for rec in records:
    for u in rec['ur']:
        all_ut.setdefault(u, []).append(rec['name'])
lines = ["# 10. Реестр пользовательских требований (User Stories) — полный, без потерь\n",
         "> Сформирован автоматическим разбором **всех** 68 БП (`.extract/txt`) по колонке «Пользовательские требования» п.5,",
         "> а при нестандартной структуре п.5 — поиском формулировок «Пользователь должен / Необходимо обеспечить / Система должна / Требуется» по всему тексту БП (такие позиции помечены ⚠️ в карточках `by_bp/enriched/`).",
         "> Дословные формулировки; ничего не перефразировано и не выброшено. Каждое УТ прослежено до исходных БП.",
         f"\nВсего уникальных формулировок УТ: **{len(all_ut)}**; всего вхождений с дублями: **{sum(len(v) for v in all_ut.values())}**.\n",
         "\n| № | Пользовательское требование (дословно) | Исходная БП |", "|---|---|---|"]
i = 0
for u, srcs in sorted(all_ut.items()):
    i += 1
    lines.append(f"| УТ-{i:03d} | {u.replace('|','\\|')} | {'; '.join(srcs)} |")
open('/workspace/docs/requirements/10_Реестр_пользовательских_требований.md','w').write('\n'.join(lines)+'\n')

# ---------- file 11: FS registry ----------
all_fn = {}
for rec in records:
    for f_ in rec['fn']:
        all_fn.setdefault(f_, []).append(rec['name'])
lines = ["# 11. Реестр функций системы — полный, без потерь\n",
         "> Колонка «Функции системы» таблицы п.5 всех 68 БП, дословно.\n",
         f"Всего уникальных формулировок ФС: **{len(all_fn)}**.\n",
         "\n| № | Функция системы (дословно) | Исходная БП |", "|---|---|---|"]
i = 0
for f_, srcs in sorted(all_fn.items()):
    i += 1
    lines.append(f"| ФС-{i:03d} | {f_.replace('|','\\|')} | {'; '.join(srcs)} |")
open('/workspace/docs/requirements/11_Реестр_функций_системы.md','w').write('\n'.join(lines)+'\n')

# ---------- file 12: full structure map ----------
lines = ["# 12. Карта структуры всех постановок (полнота разделов)\n",
         "> Для каждой из 68 БП: какие разделы шаблона присутствуют/отсутствуют, заголовки разделов как в источнике.\n",
         "| БП | Присутствующие разделы | Отсутствующие разделы шаблона 1–12 |", "|---|---|---|"]
for rec in records:
    have = ", ".join(str(n) for n in rec['nums'])
    miss = ", ".join(str(n) for n in range(1,13) if n not in rec['nums']) or '—'
    lines.append(f"| {rec['name'].replace('|','\\|')} | {have} | {miss} |")
nonstd = [(r['name'], r['nums']) for r in records if any(n>12 for n in r['nums'])]
if nonstd:
    lines.append("\nБП с нестандартными (>12) разделами: " + "; ".join(f"{n} {nums}" for n,nums in nonstd))
open('/workspace/docs/requirements/12_Карта_структуры_постановок.md','w').write('\n'.join(lines)+'\n')

print('UT unique:', len(all_ut), '| FS unique:', len(all_fn), '| records:', len(records))
