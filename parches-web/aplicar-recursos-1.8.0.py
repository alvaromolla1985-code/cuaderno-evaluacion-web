#!/usr/bin/env python3
"""Lleva a la versión web el «Material» de la versión de escritorio 1.8.0.

Uso, desde la carpeta de la versión web, indicando la carpeta del escritorio:
    python3 parches-web/aplicar-recursos-1.8.0.py RUTA/version-escritorio

Qué hace (idempotente: si ya está aplicado, lo actualiza sin duplicar):
- Sustituye calendar-ui.js por el de escritorio e inserta resource-model.js y resources-ui.js.
- Añade la validación del material (course.resources) a validateData y al código principal.
- Al duplicar una materia, conserva su material.
En la web no hay acceso a archivos del ordenador: el material funciona con enlaces (Drive,
OneDrive, Canva…) y notas. Los archivos y carpetas vinculados en escritorio se muestran como
«Solo escritorio» y se conservan en las copias.
Después ejecuta tutorial/aplicar-tutorial.py (renueva la ayuda y la caché de sw.js).
"""
import pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent
if len(sys.argv) != 2:
    sys.exit(__doc__)
desktop = pathlib.Path(sys.argv[1]) / 'src'
index = root / 'index.html'
html = index.read_bytes().decode('utf-8')
src = lambda name: (desktop / name).read_bytes().decode('utf-8')

def block(name, code):
    return f'<script>/* {name} */\n{code.strip()}\n</script>'

def replace_block(html, name, code):
    start = html.find(f'<script>/* {name} */')
    if start < 0:
        return None
    end = html.find('</script>', start) + len('</script>')
    return html[:start] + block(name, code) + html[end:]

def put_after(html, name, after, code):
    updated = replace_block(html, name, code)
    if updated is not None:
        return updated
    start = html.find(f'<script>/* {after} */')
    if start < 0:
        sys.exit(f'ERROR: no se encuentra el bloque {after}')
    end = html.find('</script>', start) + len('</script>')
    return html[:end] + '\n' + block(name, code) + html[end:]

def patch(html, old, new, label):
    if new in html:
        return html
    if html.count(old) != 1:
        sys.exit(f'ERROR: no se puede aplicar «{label}» (punto de inserción no encontrado o repetido)')
    return html.replace(old, new)

updated = replace_block(html, 'calendar-ui.js', src('calendar-ui.js'))
if updated is None:
    sys.exit('ERROR: no se encuentra calendar-ui.js en index.html')
html = put_after(updated, 'resource-model.js', 'calendar-model.js', src('resource-model.js'))
html = put_after(html, 'resources-ui.js', 'calendar-ui.js', src('resources-ui.js'))
html = patch(html, "    CalendarModel.validateEvaluations(c.evaluations, c);\n    ['grades',",
             "    CalendarModel.validateEvaluations(c.evaluations, c);\n    ResourceModel.validate(c.resources);\n    ['grades',", 'validateData')
html = patch(html, "    IndividualModel.validate(c);\n  }); return a;",
             "    IndividualModel.validate(c);ResourceModel.validate(c.resources);\n  }); return a;", 'normalizeApp')
html = patch(html, "    IndividualModel.validate(c);\n    try{validateStructure(c)}",
             "    IndividualModel.validate(c);\n    try{ResourceModel.validate(c.resources)}catch(e){check(false,p+'.resources',e.message)}\n    try{validateStructure(c)}", 'importación')
html = patch(html, " if(c.ui)for(const [key,map] of Object.entries({selectedSda:blockIds",
             " if(c.resources)c.resources=ResourceModel.remap(c.resources,[sessionIds,blockIds]);\n if(c.ui)for(const [key,map] of Object.entries({selectedSda:blockIds", 'duplicar materia')
index.write_bytes(html.encode('utf-8'))
print('Material 1.8.0 aplicado en index.html. Ejecuta ahora: python3 tutorial/aplicar-tutorial.py')
