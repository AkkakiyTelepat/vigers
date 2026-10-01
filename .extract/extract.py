#!/usr/bin/env python3
"""Extract text from Confluence-exported .doc (MHTML) files to markdown-ish text."""
import os, re, quopri
from bs4 import BeautifulSoup

SRC = "/workspace"
OUT = "/workspace/.extract/txt"
os.makedirs(OUT, exist_ok=True)

def extract_html(raw: bytes) -> str:
    text = raw.decode('utf-8', errors='replace')
    parts = re.split(r'------=_Part_[^\r\n]*\r?\n?', text)
    html_chunks = []
    for p in parts[1:]:
        header_end = p.find('\n\n')
        headers = p[:header_end]
        body = p[header_end:]
        if 'text/html' in headers:
            try:
                body = quopri.decodestring(body.encode('utf-8', errors='surrogateescape')).decode('utf-8', errors='replace')
            except Exception:
                pass
            html_chunks.append(body)
    return "\n".join(html_chunks) if html_chunks else text

def clean_name(fn):
    n = fn.replace('+', ' ')
    n = re.sub(r'\.doc$', '', n)
    return n

def render_table(t):
    rows = []
    for tr in t.find_all('tr'):
        cells = [c.get_text(' ', strip=True).replace('\n', ' ') for c in tr.find_all(['td', 'th'])]
        if cells:
            rows.append(cells)
    if not rows:
        return ''
    ncols = max(len(r) for r in rows)
    out_lines = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * ncols]
    for r in rows[1:]:
        r = r + [''] * (ncols - len(r))
        out_lines.append('| ' + ' | '.join(r) + ' |')
    return '\n'.join(out_lines)

for fn in sorted(os.listdir(SRC)):
    path = os.path.join(SRC, fn)
    if not os.path.isfile(path) or not fn.endswith('.doc'):
        continue
    raw = open(path, 'rb').read()
    html = extract_html(raw)
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['style', 'script', 'head']):
        tag.decompose()
    lines = []

    def process_block(el):
        name = el.name
        if name == 'table':
            lines.append('\n' + render_table(el) + '\n')
            return
        if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            lvl = int(name[1])
            txt = el.get_text(' ', strip=True)
            if txt:
                lines.append('#' * lvl + ' ' + txt + '\n')
            return
        if name in ('ul', 'ol'):
            for i, li in enumerate(el.find_all('li', recursive=False), 1):
                marker = '-' if name == 'ul' else f'{i}.'
                txt = li.get_text(' ', strip=True)
                lines.append(f'{marker} {txt}')
            lines.append('')
            return
        if name in ('div', 'body', None) or name in ('span',):
            kids = list(el.find_all(recursive=False))
            if kids:
                for ch in kids:
                    process_block(ch)
                return
            txt = el.get_text(' ', strip=True) if hasattr(el, 'get_text') else str(el).strip()
            if txt:
                lines.append(txt + '\n')
            return
        txt = el.get_text(' ', strip=True)
        if txt:
            lines.append(txt + '\n')

    body = soup.body or soup
    top = list(body.find_all(recursive=False))
    if top:
        for ch in top:
            process_block(ch)
    else:
        lines.append(body.get_text('\n', strip=True))

    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    outfn = clean_name(fn) + '.md.txt'
    with open(os.path.join(OUT, outfn), 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"{fn}: {len(result)} chars")
