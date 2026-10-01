# -*- coding: utf-8 -*-
import re, glob, os

SRC = '/workspace/.extract/txt'
DST = '/workspace/docs/requirements/by_bp/enriched'
os.makedirs(DST, exist_ok=True)

SEC_RE = re.compile(r'^#{1,3}\s*(\d+)\.\s*([^\n]*)$', re.M)

def split_sections(text):
    ms = list(SEC_RE.finditer(text))
    if not ms:
        return text, []
    pre = text[:ms[0].start()]
    secs = []
    for i, m in enumerate(ms):
        num = int(m.group(1))
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
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
        if not line.startswith('|'):
            continue
        if set(line) <= set('|-: '):
            continue
        rows.append([c.strip() for c in line.strip('|').split('|')])
    return rows

SENT_RE = re.compile(r'(?:Пользователь должен|Пользователю необходимо|Необходимо обеспечить|Система должна|Требуется|Требование:)[^\n]*')

stats = {}
for src in sorted(glob.glob(os.path.join(SRC, '*.txt'))):
    name = re.sub(r'\.md$', '', os.path.basename(src)[:-4])
    raw = open(src, encoding='utf-8', errors='replace').read()
    pre, secs = split_sections(raw)
    smap = {}
    titles = {}
    for num, title, body in secs:
        smap[num] = smap.get(num, '') + body
        titles.setdefault(num, title)

    user_reqs, funcs, goals, proc = [], [], [], []
    s5 = smap.get(5, '')
    for t in re.findall(r'(?:^[ \t]*\|[^\n]*\|[^\n]*\n)+', s5, re.M):
        rows = rows_from_tables(t)
        if not rows:
            continue
        hdr = [h.lower() for h in rows[0]]
        def cell(row, key, hdr=hdr):
            for i, h in enumerate(hdr):
                if key in h and i < len(row):
                    return row[i]
            return ''
        for r in rows[1:]:
            ur = cell(r, 'пользовательск')
            fn = cell(r, 'функци')
            pr = cell(r, 'цель')
            pc = cell(r, 'процесс')
            if ur:
                user_reqs += [x for x in re.split(r'(?=\bПользователь должен\b)', ur) if x.strip()]
            if fn:
                funcs += re.split(r'\n+', fn)
            if pr:
                goals += re.split(r'\n+', pr)
            if pc:
                proc += re.split(r'\n+', pc)

    # fallback: sentence-level requirement mining across whole doc
    fallback_used = False
    if not user_reqs:
        mined = SENT_RE.findall(raw)
        if mined:
            user_reqs = mined
            fallback_used = True

    def clean(lst):
        out = []
        for x in lst:
            x = re.sub(r'\s+', ' ', x).strip(' ;•-\u2022|')
            if x and x.lower() not in ('отсутствует', 'нет', '-', '—', 'не изменяются', 'не изменяется'):
                out.append(x)
        return out

    user_reqs, funcs, goals, proc = map(clean, (user_reqs, funcs, goals, proc))

    header = (f"# {name}\n\n"
              f"> **Слой А** — структурированная карточка требований (по Вигерсу). "
              f"**Слой B** — исходные артефакты. **Слой C** — полный оригинал без сокращений.\n"
              f"> Источник: `.extract/txt/{os.path.basename(src)}` • Объём оригинала: {len(raw)} симв.\n\n---\n\n"
              f"## Слой А. Структурированная карточка\n\n")

    A = []
    def sec_block(title, body, missing):
        A.append(f"### {title}\n\n{body if body else '_' + missing + '_'}\n")

    sec_block("A.1 Термины и сокращения этой постановки", strip_head(smap.get(1,''), 1), "Раздел 1 отсутствует в источнике.")
    sec_block("A.2 Подсистемы", strip_head(smap.get(2,''), 2), "Не указано.")
    sec_block("A.3 Компоненты (объекты доработки)", strip_head(smap.get(3,''), 3), "Не указано.")
    sec_block("A.4 Цель и концепция решения", strip_head(smap.get(4,''), 4), "Не указано.")

    if goals or proc:
        blk = "### A.5 Бизнес-цели и автоматизируемые процессы (из таблицы п.5)\n\n"
        blk += "\n".join(f"- 🎯 {x}" for x in dict.fromkeys(goals))
        if proc:
            blk += "\n\nАвтоматизируемые процессы: " + "; ".join(dict.fromkeys(proc))
        A.append(blk + "\n")
    if user_reqs:
        note = "\n> ⚠️ Извлечено поиском формулировок требований по всему тексту (таблица п.5 заполнена иначе).\n" if fallback_used else ""
        A.append("### A.6 Пользовательские требования (User Stories)" + note + "\n\n" +
                 "\n".join(f"- **УТ:** {x}" for x in dict.fromkeys(user_reqs)) + "\n")
    if funcs:
        A.append("### A.7 Функции системы (дословно из п.5)\n\n" +
                 "\n".join(f"- **ФС:** {x}" for x in dict.fromkeys(funcs)) + "\n")

    if s5:
        A.append("### A.7.1 Раздел 5 «Требования к результату» полностью (дословно)\n\n" + strip_head(s5, 5) + "\n")

    sec_block("A.8 Автоматизация бизнес-процессов / варианты использования (п.6)", strip_head(smap.get(6,''), 6), "Раздел отсутствует в источнике.")
    sec_block("A.9 Пользовательский сценарий и алгоритмы (п.7)", strip_head(smap.get(7,''), 7), "Раздел отсутствует в источнике.")
    sec_block("A.10 Функции системы (п.8, дословно)", strip_head(smap.get(8,''), 8), "Раздел отсутствует в источнике.")
    sec_block("A.11 Требования к данным (п.9, дословно)", strip_head(smap.get(9,''), 9), "Раздел отсутствует в источнике.")
    sec_block("A.12 Внешние системы (п.10, дословно)", strip_head(smap.get(10,''), 10), "Раздел отсутствует в источнике.")
    sec_block("A.13 Прочие задачи (п.11, дословно)", strip_head(smap.get(11,''), 11), "Раздел отсутствует в источнике.")
    sec_block("A.14 Критерии приёмки (п.12, дословно)", strip_head(smap.get(12,''), 12), "Раздел отсутствует в источнике.")

    marks = re.findall(r'[^\n]*(?:противореч|несостык|уточнить|TBD)[^\n]*', raw, re.I)
    marks = [m.strip() for m in marks if not m.strip().startswith('#')]
    if marks:
        A.append("### A.15 Помеченные вопросы/неясности внутри самой постановки\n\n" +
                 "\n".join(f"- ❓ {m}" for m in dict.fromkeys(marks)) + "\n")

    # Non-standard structure notice
    nums = sorted(smap)
    std = set(range(1, 13))
    nonstd = [n for n in nums if n not in std]
    missing_std = [n for n in range(1, 13) if n not in smap]
    titles_list = "\n".join(f"{n}. {titles[n]}" for n in nums)
    notes = ["### A.16 Особенности структуры источника\n",
             f"- Разделы, присутствующие в БП: `{titles_list}`"]
    if missing_std:
        notes.append(f"- Отсутствуют разделы стандартного шаблона: {missing_std} — факт неполноты постановки.")
    if nonstd:
        notes.append(f"- Нестандартная нумерация: разделы {nonstd} вынесены в слой B дословно.")
    if raw.count('# 5.') and 'Критери' in smap.get(5, ''):
        notes.append("- ❗ В данной БП раздел 5 озаглавлен как «Критерии приемки» (отклонение от шаблона, где п.5 — «Требования к результату», а п.12 — критерии приёмки).")
    A.append("\n".join(notes) + "\n")

    B = ["\n## Слой B. Исходные артефакты (вне нумерованных разделов)\n"]
    body_pre = []
    started = False
    for l in pre.splitlines():
        ls = l.strip()
        if not started and (ls.startswith('#') or ls.startswith('-') or ls in ('{}', '') or ls.startswith('>')):
            continue
        started = True
        body_pre.append(l)
    bp_body = '\n'.join(body_pre).strip()
    if bp_body:
        B.append(f"### B.1 Текст до раздела 1 (кроме заголовка и оглавления)\n\n{bp_body}\n")
    for n, b in [(num, body) for num, t_, body in secs if num > 12]:
        B.append(f"### B.{n} Нестандартный раздел {n} оригинала\n\n{b.strip()}\n")
    if not bp_body and not [1 for num, _, _ in secs if num > 12]:
        B.append("_Дополнительных артефактов вне нумерованных разделов нет._\n")

    V = ("\n## Слой C. Полный оригинал (без сокращений)\n\n<details>\n"
         f"<summary>Показать оригинал ({len(raw)} симв.)</summary>\n\n{raw}\n\n</details>\n")

    doc = header + "\n".join(A) + "".join(B) + V
    safe = name.replace('/', '_')
    with open(os.path.join(DST, safe + '.md'), 'w', encoding='utf-8') as f:
        f.write(doc)
    stats[name] = (len(raw), len(set(user_reqs)), len(set(funcs)))

print('files:', len(stats))
print('UT total:', sum(v[1] for v in stats.values()), 'FS total:', sum(v[2] for v in stats.values()))
small = [k for k, v in stats.items() if v[1] == 0]
print('zero UT:', len(small))
for k in small: print(' -', k)
