# -*- coding: utf-8 -*-
import re, glob, os

SRC = '/workspace/.extract/txt'
DST = '/workspace/docs/requirements/by_bp/enriched'
os.makedirs(DST, exist_ok=True)

SEC_RE = re.compile(r'^#{1,3}\s*(\d+)\.\s*[^\n]*$', re.M)

def split_sections(text):
    ms = list(SEC_RE.finditer(text))
    if not ms:
        return text, []
    pre = text[:ms[0].start()]
    secs = []
    for i, m in enumerate(ms):
        num = int(m.group(1))
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        secs.append((num, text[m.start():end]))
    merged = []
    for num, body in secs:
        if merged and num == merged[-1][0]:
            merged[-1] = (merged[-1][0], merged[-1][1] + '\n' + body)
        elif merged and num < merged[-1][0] and merged[-1][0] >= 10:
            merged[-1] = (merged[-1][0], merged[-1][1] + '\n' + body)
        else:
            merged.append((num, body))
    return pre, merged

def get_sec(secs, n):
    return '\n'.join(b for num, b in secs if num == n)

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

stats = {}
for src in sorted(glob.glob(os.path.join(SRC, '*.txt'))):
    name = re.sub(r"\.md$", "", os.path.basename(src)[:-4])
    raw = open(src, encoding='utf-8', errors='replace').read()
    pre, secs = split_sections(raw)
    s = {n: get_sec(secs, n) for n in range(1, 13)}

    user_reqs, funcs, goals, proc = [], [], [], []
    for t in re.findall(r'(?:^[ \t]*\|[^\n]*\|[^\n]*\n)+', s[5], re.M):
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

    def clean(lst):
        out = []
        for x in lst:
            x = re.sub(r'\s+', ' ', x).strip(' ;•-\u2022')
            if x and x.lower() not in ('отсутствует', 'нет', '-', '—', 'не изменяются', 'не изменяется'):
                out.append(x)
        return out

    user_reqs, funcs, goals, proc = map(clean, (user_reqs, funcs, goals, proc))

    header = (f"# {name}\n\n"
              f"> **Слой А** — структурированная карточка требований (по Вигерсу). "
              f"**Слой B** — исходные артефакты. **Слой C** — полный оригинал без сокращений.\n"
              f"> Источник: `.extract/txt/{name}.txt` • Объём оригинала: {len(raw)} симв.\n\n---\n\n"
              f"## Слой А. Структурированная карточка\n\n")

    A = []
    def sec_block(title, body, missing):
        A.append(f"### {title}\n\n{body if body else '_' + missing + '_'}\n")

    sec_block("A.1 Термины и сокращения этой постановки", strip_head(s[1], 1), "Раздел 1 отсутствует в источнике.")
    sec_block("A.2 Подсистемы", strip_head(s[2], 2), "Не указано.")
    sec_block("A.3 Компоненты (объекты доработки)", strip_head(s[3], 3), "Не указано.")
    sec_block("A.4 Цель и концепция решения", strip_head(s[4], 4), "Не указано.")

    if goals or proc:
        blk = "### A.5 Бизнес-цели и автоматизируемые процессы (из таблицы п.5)\n\n"
        blk += "\n".join(f"- 🎯 {x}" for x in dict.fromkeys(goals))
        if proc:
            blk += "\n\nАвтоматизируемые процессы: " + "; ".join(dict.fromkeys(proc))
        A.append(blk + "\n")
    if user_reqs:
        A.append("### A.6 Пользовательские требования (User Stories, дословно из п.5)\n\n" +
                 "\n".join(f"- **УТ:** {x}" for x in dict.fromkeys(user_reqs)) + "\n")
    if funcs:
        A.append("### A.7 Функции системы (дословно из п.5)\n\n" +
                 "\n".join(f"- **ФС:** {x}" for x in dict.fromkeys(funcs)) + "\n")

    if s[5]:
        A.append("### A.7.1 Раздел 5 «Требования к результату» полностью (дословно)\n\n" + strip_head(s[5], 5) + "\n")

    sec_block("A.8 Автоматизация бизнес-процессов / варианты использования (п.6)", strip_head(s[6], 6), "Раздел отсутствует в источнике.")
    sec_block("A.9 Пользовательский сценарий и алгоритмы (п.7)", strip_head(s[7], 7), "Раздел отсутствует в источнике.")
    sec_block("A.10 Функции системы (п.8, дословно)", strip_head(s[8], 8), "Раздел отсутствует в источнике.")
    sec_block("A.11 Требования к данным (п.9, дословно)", strip_head(s[9], 9), "Раздел отсутствует в источнике.")
    sec_block("A.12 Внешние системы (п.10, дословно)", strip_head(s[10], 10), "Раздел отсутствует в источнике.")
    sec_block("A.13 Прочие задачи (п.11, дословно)", strip_head(s[11], 11), "Раздел отсутствует в источнике.")
    sec_block("A.14 Критерии приёмки (п.12, дословно)", strip_head(s[12], 12), "Раздел отсутствует в источнике.")

    marks = re.findall(r'[^\n]*(?:противореч|несостык|уточнить|TBD)[^\n]*', raw, re.I)
    marks = [m.strip() for m in marks if not m.strip().startswith('#')]
    if marks:
        A.append("### A.15 Помеченные вопросы/неясности внутри самой постановки\n\n" +
                 "\n".join(f"- ❓ {m}" for m in dict.fromkeys(marks)) + "\n")

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
    extra_secs = [(n, b) for n, b in secs if n > 12]
    for n, b in extra_secs:
        B.append(f"### B.{n} Нестандартный раздел {n} оригинала\n\n{b.strip()}\n")
    if not bp_body and not extra_secs:
        B.append("_Дополнительных артефактов вне нумерованных разделов нет._\n")

    V = ("\n## Слой C. Полный оригинал (без сокращений)\n\n<details>\n"
         f"<summary>Показать оригинал ({len(raw)} симв.)</summary>\n\n{raw}\n\n</details>\n")

    doc = header + "\n".join(A) + "".join(B) + V
    safe = name.replace('/', '_')
    with open(os.path.join(DST, safe + '.md'), 'w', encoding='utf-8') as f:
        f.write(doc)
    stats[name] = (len(raw), len(set(user_reqs)), len(set(funcs)))

tot = sum(v[0] for v in stats.values())
print('files:', len(stats), 'total chars:', tot)
print('UT total:', sum(v[1] for v in stats.values()), 'FS total:', sum(v[2] for v in stats.values()))
small = [k for k, v in stats.items() if v[1] + v[2] == 0]
print('no parsed UT/FS (only layer C preserved):', len(small))
for k in small: print(' -', k)
