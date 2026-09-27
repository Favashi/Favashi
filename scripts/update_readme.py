#!/usr/bin/env python3
"""Actualiza las secciones automáticas del README (entre <!-- AUTO:x --> y <!-- /AUTO:x -->).

Solo usa datos públicos y la biblioteca estándar:
- Cifras del catálogo de Escriba de la Marca: función pública `landing_showcase` de su Supabase
  (la misma que usa la portada; la URL y la clave publicable se leen de js/config.js del propio repositorio).
- Últimas versiones: releases de GitHub de escribadelamarca y osr-manager.
- Tests: suma de los plan(N) de pgTAP y número de test() de Playwright en escribadelamarca.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

OWNER = 'Favashi'
RAW = f'https://raw.githubusercontent.com/{OWNER}/escribadelamarca/main'
README = os.path.join(os.path.dirname(__file__), '..', 'README.md')


def get(url, data=None, headers=None):
    h = {'User-Agent': 'favashi-profile-bot', **(headers or {})}
    token = os.environ.get('GITHUB_TOKEN')
    if token and 'api.github.com' in url:
        h['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def showcase():
    cfg = get(f'{RAW}/js/config.js')
    url = re.search(r"SUPABASE_URL\s*=\s*'([^']+)'", cfg).group(1)
    key = re.search(r"SUPABASE_ANON_KEY\s*=\s*'([^']+)'", cfg).group(1)
    body = get(f'{url}/rest/v1/rpc/landing_showcase', data=b'{}',
               headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    return json.loads(body)


def test_count():
    files = json.loads(get(f'https://api.github.com/repos/{OWNER}/escribadelamarca/contents/supabase/tests/database'))
    pgtap = sum(int(m) for f in files if f['name'].endswith('.sql')
                for m in re.findall(r'plan\((\d+)\)', get(f['download_url'])))
    e2e = len(re.findall(r'^\s*test\(', get(f'{RAW}/tests/e2e/app.spec.js'), re.M))
    return pgtap + e2e


def latest(repo, name):
    r = json.loads(get(f'https://api.github.com/repos/{OWNER}/{repo}/releases/latest'))
    note = next((l.strip(' -*') for l in (r.get('body') or '').splitlines() if l.strip()), '')
    note = re.sub(r'\s+', ' ', note)
    if note.lower().startswith(name.lower()):   # «OSR Manager v0.4.0. Ver CHANGELOG…»: no aporta nada
        note = ''
    note = note if len(note) <= 140 else note[:137].rstrip() + '…'
    return f'- **{name} [{r["tag_name"]}]({r["html_url"]})**' + (f' · {note}' if note else '')


def num(n):
    return f'{int(n):,}'.replace(',', '.')


def replace(text, key, value):
    pattern = re.compile(rf'(<!-- AUTO:{key} -->)(.*?)(<!-- /AUTO:{key} -->)', re.S)
    if not pattern.search(text):
        sys.exit(f'Falta el marcador AUTO:{key} en el README')
    return pattern.sub(lambda m: m.group(1) + value + m.group(3), text)


def main():
    text = open(README, encoding='utf-8').read()
    before = text
    s = showcase()
    tests = test_count()
    stats = '\n'.join([
        '', '| | |', '|---|---|',
        f'| Publicaciones en el catálogo de Escriba | {num(s["publications"])} |',
        f'| Autores de la Marca catalogados | {num(s["authors"])} |',
        f'| Aventuras en el buscador | {num(s["adventures"])} |',
        f'| Libros registrados por los usuarios | {num(s["books_cataloged"])} |',
        f'| Tests en CI de Escriba | {num(tests)} |',
        '| Coste de infraestructura | 0 € |', ''])
    now = '\n' + latest('escribadelamarca', 'Escriba de la Marca') + '\n' + latest('osr-manager', 'OSR Manager') + '\n'
    text = replace(text, 'stats', stats)
    text = replace(text, 'now', now)
    text = replace(text, 'tests', num(tests))
    # La fecha solo cambia si cambia algo más (así no hay un commit diario vacío)
    if text != before:
        text = replace(text, 'date', datetime.date.today().isoformat())
        open(README, 'w', encoding='utf-8').write(text)
        print('README actualizado')
    else:
        print('Sin cambios')


if __name__ == '__main__':
    main()
