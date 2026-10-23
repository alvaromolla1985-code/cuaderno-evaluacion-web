#!/usr/bin/env python3
"""Inserta (o actualiza) el tutorial web y la ayuda contextual en index.html.

Uso, desde la carpeta de la versión web:
    python3 tutorial/aplicar-tutorial.py

Úsalo SIEMPRE después de regenerar index.html desde la versión de escritorio:
la regeneración sustituye index.html y borraría el tutorial.
Es idempotente: si el bloque ya existe, lo reemplaza; no lo duplica.
También renueva el nombre de caché de sw.js para que los dispositivos reciban la versión nueva.
"""
import pathlib, re, sys, time

root = pathlib.Path(__file__).resolve().parent.parent
index = root / 'index.html'
START, END = '<!-- TUTORIAL-WEB:INICIO -->', '<!-- TUTORIAL-WEB:FIN -->'
block = (root / 'tutorial' / 'tutorial-web.html').read_bytes().decode('utf-8').strip()
ayuda = root / 'tutorial' / 'ayuda-contextual.part.html'
if ayuda.exists():  # ayuda por pestaña e importación, dentro del mismo bloque
    block = block.replace(END, ayuda.read_bytes().decode('utf-8').strip() + '\n' + END)
html = index.read_bytes().decode('utf-8')

if START in html:
    html = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: block, html, count=1, flags=re.S)
    action = 'actualizado'
else:
    pos = html.rfind('</body>')
    if pos < 0:
        sys.exit('ERROR: no se encuentra </body> en index.html')
    html = html[:pos] + block + '\n' + html[pos:]
    action = 'insertado'
index.write_bytes(html.encode('utf-8'))

sw = root / 'sw.js'
if sw.exists():
    text = sw.read_bytes().decode('utf-8')
    new = re.sub(r"const CACHE = '([^']*?)(?:-tut\d+)?';", lambda m: f"const CACHE = '{m.group(1)}-tut{int(time.time())}';", text, count=1)
    sw.write_bytes(new.encode('utf-8'))

print(f'Tutorial {action} en {index.name}.')
