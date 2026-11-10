#!/usr/bin/env python3
"""Lista de cotejo con ítems (SOLO VERSIÓN WEB).

Hace que el instrumento «Lista de cotejo» use el motor de rúbricas:
- Plantillas de escala: Sí/No · Hecho/A medias/No hecho · Conseguido/En proceso/No conseguido · Personalizada.
- Una lista de cotejo SIN ítems sigue funcionando como nota directa (compatibilidad total).
- Al calificar: botones con el nombre del nivel y «Marcar todos».

Uso (desde la carpeta de la web, después de regenerar index.html y aplicar el tutorial):
    python3 parches-web/aplicar-lista-cotejo.py
Es idempotente. Si el código de escritorio cambió y algún fragmento ya no coincide,
se detiene SIN modificar nada e indica qué fragmento falla.
"""
import pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / 'index.html'
SW = ROOT / 'sw.js'
MARK = '/* lista-cotejo (solo web) */'

HELPERS = MARK + r"""
const CHECKLIST_PRESETS={
 sino:{name:'Sí / No',levels:[{value:10,label:'Sí',description:''},{value:0,label:'No',description:''}]},
 hecho:{name:'Hecho / A medias / No hecho',levels:[{value:10,label:'Hecho',description:''},{value:5,label:'A medias',description:''},{value:0,label:'No hecho',description:''}]},
 logro:{name:'Conseguido / En proceso / No conseguido',levels:[{value:10,label:'Conseguido',description:''},{value:5,label:'En proceso',description:''},{value:0,label:'No conseguido',description:''}]}
};
let CK_CUSTOM=null;
function isChecklist(ac){return ac?.instrument==='checklist'}
// Instrumento que se configura con indicadores/ítems (muestra el editor).
function indicatorInstrument(ac){return ac?.instrument==='rubric'||isChecklist(ac)}
// Instrumento que CALCULA con indicadores. Una lista de cotejo sin ítems sigue siendo nota directa.
function usesIndicators(ac){return ac?.instrument==='rubric'||(isChecklist(ac)&&Array.isArray(ac.rubric?.rows)&&ac.rubric.rows.length>0)}
function checklistScaleOf(ac){const rows=ac?.rubric?.rows||[];if(!rows.length)return null;const key=r=>JSON.stringify(RubricContract.levels(r).map(l=>[l.value,l.label]));const first=key(rows[0]);return {levels:RubricContract.levels(rows[0]),uniform:rows.every(r=>key(r)===first)}}
function checklistLevelValue(v){return String(v).replace('.',',')}
function checklistScaleText(levels){return levels.map(l=>`${esc(l.label||'—')} (${checklistLevelValue(l.value)})`).join(' · ')}
function checklistHasScores(c,aid){return Object.entries(c.rubricScores||{}).some(([key,vals])=>key.split('|')[1]===aid&&Object.values(vals||{}).some(v=>v!==null&&v!==undefined&&v!==''))}
function checklistCriteriaWithoutItems(ac){const rows=ac.rubric?.rows||[];return ac.criteria.filter(code=>!rows.some(r=>r.criterion===code&&Number(r.weight??1)>0))}
function checklistHasDirectGrades(c,aid){return Object.keys(c.grades||{}).some(k=>k.split('|')[1]===aid)}
function checklistActions(aid){return `<button class="btn small" onclick="openRubricEditor(${jsArg(aid)})">Editar lista de cotejo</button>`}
function openChecklistEditor(aid){
 const c=course(),f=findActivity(c,aid);if(!f)return;const ac=f.ac,rows=ac.rubric?.rows||[],scale=checklistScaleOf(ac),scored=checklistHasScores(c,aid),missing=checklistCriteriaWithoutItems(ac);
 const presets=Object.entries(CHECKLIST_PRESETS).map(([key,p])=>`<button class="btn small" ${scored?'disabled':''} onclick="applyChecklistPreset(${jsArg(aid)},${jsArg(key)})">${esc(p.name)}</button>`).join('')+`<button class="btn small" ${scored?'disabled':''} onclick="ckCustomStart(${jsArg(aid)})">Personalizada…</button>`;
 const items=rows.map((r,i)=>`<div class="activity-edit"><div class="row"><input data-daily-input class="grow" aria-label="Ítem ${i+1}" value="${esc(r.label)}" onchange="rubEdit('${aid}',${i},'label',this.value)"><select aria-label="Criterio ítem ${i+1}" onchange="rubEdit('${aid}',${i},'criterion',this.value)"><option value="" ${!r.criterion?'selected':''}>Sin criterio asociado</option>${rubricAllowedCriteria(c,ac).map(cr=>`<option value="${esc(cr.code)}" ${r.criterion===cr.code?'selected':''}>${esc(criterionLabel(c,cr.code))}</option>`).join('')}</select><label class="tiny">Peso <input data-daily-input type="number" style="width:70px" min="0" step="any" aria-label="Peso ítem ${i+1}" value="${r.weight??1}" onchange="rubEdit('${aid}',${i},'weight',this.value)"></label><button type="button" class="btn small danger" onclick="rubDelete('${aid}',${i})">Borrar</button></div></div>`).join('');
 openModal(`<div class="row"><h2>Lista de cotejo · ${esc(ac.name)}</h2><button class="btn small right" onclick="closeModal();render()">Cerrar</button></div>
 ${ac.rubric?`<label>Nombre de la lista <input aria-label="Nombre de la lista de cotejo" value="${esc(ac.rubric.name||ac.name)}" onchange="editRubricName(${jsArg(aid)},this.value)"></label>`:''}
 <div class="card" style="margin:10px 0"><div><b>Escala</b>: ${scale?checklistScaleText(scale.levels):'<span class="muted">elige una escala para empezar.</span>'}</div>${scale&&!scale.uniform?'<div class="notice warn">Los ítems tienen escalas distintas. Si eliges una escala, todos los ítems pasan a usarla.</div>':''}<div class="toolbar">${presets}</div>${scored?'<div class="tiny muted">Ya hay alumnado evaluado con esta lista: la escala no se puede cambiar para no alterar sus notas.</div>':''}${CK_CUSTOM?.aid===aid?checklistCustomEditor():''}</div>
 ${rows.some(r=>!r.criterion||!ac.criteria.includes(r.criterion))?`<div class="notice warn">${rows.filter(r=>!r.criterion||!ac.criteria.includes(r.criterion)).length} ítem(s) sin criterio: no cuentan para ninguna nota. Elige su criterio en el desplegable.</div>`:''}
 ${rows.length&&missing.length?`<div class="notice warn">Falta al menos un ítem con peso para: ${missing.map(code=>esc(criterionLabel(c,code))).join(', ')}. Hasta completarlo, la actividad no se puede evaluar.</div>`:''}
 ${rows.length&&checklistHasDirectGrades(c,aid)?'<div class="notice">Esta actividad ya tenía notas directas. Se conservan y, en cada criterio, siguen contando hasta que marques algún ítem de ese criterio para esa persona.</div>':''}
 ${rows.length?'<div class="notice">Cada ítem se vincula a un criterio de la actividad. La nota de cada criterio es la media de sus ítems (ponderada por el peso).</div>':'<div class="notice">Mientras la lista no tenga ítems, la actividad se califica con nota directa.</div>'}
 <div id="rubRows">${items}</div>
 <div class="toolbar"><button class="btn primary" onclick="ckAdd(${jsArg(aid)})">+ Ítem</button><button class="btn small" onclick="openRubricBank(${jsArg(aid)})">Reutilizar del banco</button>${rows.length?`<button class="btn small" onclick="openSaveRubricBank(${jsArg(aid)})">Guardar en banco</button>`:''}</div>`)
}
async function applyChecklistScale(aid,levels){
 const c=course(),ac=findActivity(c,aid)?.ac;if(!ac||!isChecklist(ac))return {ok:false};
 let clean;try{if(levels.length<2)throw Error('La escala necesita al menos dos niveles.');clean=RubricContract.validateLevels(RubricContract.clone(levels))}catch(e){alert(e.message);return {ok:false,error:e.message}}
 if(checklistHasScores(c,aid)){alert('Esta lista de cotejo ya tiene alumnado evaluado. Para no alterar sus notas, la escala no se puede cambiar.');return {ok:false}}
 const result=await changeCourse(target=>{const a=findActivity(target,aid).ac;a.rubric=a.rubric||{rows:[]};if(!a.rubric.name)a.rubric.name=a.name;if(!a.rubric.rows.length)a.rubric.rows.push({id:uid('rub'),label:'Ítem 1',criterion:a.criteria[0]||'',weight:1,levels:[]});a.rubric.rows.forEach(r=>{r.levels=RubricContract.clone(clean)})},'aplicar la escala de la lista de cotejo');
 if(result.ok){CK_CUSTOM=null;render();openChecklistEditor(aid)}return result;
}
function applyChecklistPreset(aid,key){const p=CHECKLIST_PRESETS[key];if(!p)return Promise.resolve({ok:false});return applyChecklistScale(aid,p.levels)}
function ckCustomStart(aid){const ac=findActivity(course(),aid)?.ac;if(!ac)return;const s=checklistScaleOf(ac);CK_CUSTOM={aid,levels:RubricContract.clone(s?.levels||CHECKLIST_PRESETS.sino.levels).map(l=>({value:l.value,label:l.label||'',description:''}))};openChecklistEditor(aid)}
function checklistCustomEditor(){const d=CK_CUSTOM;return `<div class="card" style="margin-top:8px"><div class="tiny muted">Escribe el nombre de cada nivel y su puntuación (de 0 a 10, sin repetir).</div>${d.levels.map((l,i)=>`<div class="row" style="margin-top:6px"><input data-daily-input aria-label="Nombre del nivel ${i+1}" value="${esc(l.label)}" oninput="CK_CUSTOM.levels[${i}].label=this.value"><input data-daily-input type="number" min="0" max="10" step="any" style="width:80px" aria-label="Puntuación del nivel ${i+1}" value="${l.value??''}" oninput="CK_CUSTOM.levels[${i}].value=this.value.trim()===''?null:Number(this.value)"><button class="btn small danger" ${d.levels.length<=2?'disabled':''} onclick="ckCustomRemove(${i})">Quitar</button></div>`).join('')}<div class="toolbar"><button class="btn small" ${d.levels.length>=10?'disabled':''} onclick="ckCustomAdd()">+ Nivel</button><button class="btn small primary" onclick="ckCustomApply()">Aplicar escala</button><button class="btn small" onclick="ckCustomCancel()">Cancelar</button></div></div>`}
function ckCustomAdd(){const d=CK_CUSTOM;if(!d||d.levels.length>=10)return;let v=null;try{v=nextRubricLevelValue(d.levels.filter(l=>Number.isFinite(l.value)))}catch{}d.levels.push({value:v,label:'',description:''});openChecklistEditor(d.aid)}
function ckCustomRemove(i){const d=CK_CUSTOM;if(!d||d.levels.length<=2)return;d.levels.splice(i,1);openChecklistEditor(d.aid)}
function ckCustomCancel(){const aid=CK_CUSTOM?.aid;CK_CUSTOM=null;if(aid)openChecklistEditor(aid)}
function ckCustomApply(){const d=CK_CUSTOM;if(!d)return Promise.resolve({ok:false});if(d.levels.some(l=>!String(l.label||'').trim())){alert('Cada nivel necesita un nombre.');return Promise.resolve({ok:false})}if(d.levels.some(l=>typeof l.value!=='number'||!Number.isFinite(l.value)||l.value<0||l.value>10)){alert('Cada nivel necesita una puntuación entre 0 y 10.');return Promise.resolve({ok:false})}if(new Set(d.levels.map(l=>l.value)).size!==d.levels.length){alert('Dos niveles no pueden tener la misma puntuación.');return Promise.resolve({ok:false})}return applyChecklistScale(d.aid,d.levels.map(l=>({value:l.value,label:String(l.label).trim(),description:''})))}
function ckAdd(aid){const ac=findActivity(course(),aid)?.ac;if(!ac)return Promise.resolve({ok:false});ac.rubric=ac.rubric||{rows:[]};if(!ac.rubric.name)ac.rubric.name=ac.name;const base=ac.rubric.rows[0]?RubricContract.levels(ac.rubric.rows[0]):CHECKLIST_PRESETS.sino.levels;ac.rubric.rows.push({id:uid('rub'),label:'Ítem '+(ac.rubric.rows.length+1),criterion:ac.criteria[0]||'',weight:1,levels:RubricContract.clone(base)});const result=save();render();openChecklistEditor(aid);return result}
function checklistBulkBar(ac,stu,aid){if(!isChecklist(ac))return '';const s=checklistScaleOf(ac);if(!s||!s.uniform)return '';return `<div class="toolbar"><span class="tiny muted">Marcar todos los ítems:</span>${s.levels.map(l=>`<button class="btn small" onclick="setAllRubLevels(${jsArg(stu)},${jsArg(aid)},${l.value})">${esc(l.label||checklistLevelValue(l.value))}</button>`).join('')}</div>`}
function setAllRubLevels(stu,aid,val){const c=course(),ac=findActivity(c,aid)?.ac,rows=ac?.rubric?.rows||[];if(!ac||!isChecklist(ac)||!rows.length||!c.students.some(s=>s.id===stu)||!rows.every(r=>RubricContract.levels(r).some(l=>l.value===val))){alert('Nivel no válido para todos los ítems.');return Promise.resolve({ok:false})}const k=rubKey(stu,aid);rows.forEach(r=>{if(r.criterion&&ac.criteria.includes(r.criterion))delete c.grades[gradeKey(stu,aid,r.criterion)]});c.rubricScores[k]=c.rubricScores[k]||{};rows.forEach(r=>{c.rubricScores[k][r.id]=val});const result=save();openRubricEval(stu,aid);return result}
"""

# (descripción, texto original, texto nuevo, apariciones esperadas)
R = []
def rep(desc, old, new, count=1): R.append((desc, old, new, count))

# --- Helpers: se insertan justo antes de rubricActions (script rubric-ui) ---
rep('helpers',
    "function rubricActions(aid){return `<button class=\"btn small\" onclick=\"openRubricEditor(",
    HELPERS + "function rubricActions(aid){if(isChecklist(findActivity(course(),aid)?.ac))return checklistActions(aid);return `<button class=\"btn small\" onclick=\"openRubricEditor(")

# --- Contrato de programación (importar programación) ---
rep('programacion: rubric con checklist',
    "if(node.instrument?.rubric&&node.instrument.type!=='rubric')fail(p+'.instrument','una rúbrica requiere type rubric');",
    "if(node.instrument?.rubric&&node.instrument.type!=='rubric'&&node.instrument.type!=='checklist')fail(p+'.instrument','una rúbrica requiere type rubric o checklist');")
rep('programacion: aviso nota directa',
    "if(instrument&&instrument.type!=='rubric'&&instrument.type!=='direct')warnings.push(",
    "if(instrument&&instrument.type!=='rubric'&&instrument.type!=='direct'&&!(instrument.type==='checklist'&&instrument.rubric?.rows?.length))warnings.push(")

# --- Informe individualizado: lista sin ítems = nota directa ---
rep('informe: instrumento',
    "date:day,instrument:ac.instrument||'direct',",
    "date:day,instrument:(ac.instrument==='checklist'&&!ac.rubric?.rows?.length)?'direct':(ac.instrument||'direct'),")

# --- Banco / importación de rúbricas: permitir destino lista de cotejo ---
rep('banco: actividades destino',
    "const activities=allActivities(c).filter(x=>x.ac.instrument==='rubric');if(!activities.length){alert('Configura primero una actividad con instrumento Rúbrica en este curso.');return}",
    "const activities=allActivities(c).filter(x=>indicatorInstrument(x.ac));if(!activities.length){alert('Configura primero una actividad con instrumento Rúbrica o Lista de cotejo en este curso.');return}")
rep('banco: mapping',
    "if(aid&&(!ac||ac.instrument!=='rubric'))throw Error('Selecciona una actividad con instrumento Rúbrica.');",
    "if(aid&&(!ac||!indicatorInstrument(ac)))throw Error('Selecciona una actividad con instrumento Rúbrica o Lista de cotejo.');")
rep('banco: aplicar',
    "d.before!==dataFingerprint(APP)||ac.instrument!=='rubric')throw Error(",
    "d.before!==dataFingerprint(APP)||!indicatorInstrument(ac))throw Error(")

# --- Motor de cálculo ---
rep('motor: puntuación por criterio',
    "function getRubricCriterionScore(c,stu,ac,crit){\n  if(ac.instrument!=='rubric'||!ac.rubric?.rows?.length)return null;",
    "function getRubricCriterionScore(c,stu,ac,crit){\n  if(!usesIndicators(ac)||!ac.rubric?.rows?.length)return null;")
rep('motor: validación actividad',
    " // The existing contract uses direct grades for every non-rubric instrument.\n if(ac.instrument!=='rubric')return '';",
    " // Nota directa para todo instrumento sin indicadores (incluida la lista de cotejo sin ítems).\n if(!usesIndicators(ac))return '';")
rep('motor: mensaje niveles',
    "catch{return 'Rúbrica con niveles no utilizables'}",
    "catch{return isChecklist(ac)?'Lista de cotejo con niveles no utilizables':'Rúbrica con niveles no utilizables'}")
rep('motor: mensaje criterios',
    "return 'Rúbrica sin indicadores ponderados para todos sus criterios';",
    "return isChecklist(ac)?'Lista de cotejo sin ítems con peso para todos sus criterios':'Rúbrica sin indicadores ponderados para todos sus criterios';")

# --- Evaluar ---
rep('evaluar: completar alumno',
    " if(f.ac.instrument==='rubric'&&!evaluationActivityIssue(c,f.ac)){openRubricEval(",
    " if(usesIndicators(f.ac)&&!evaluationActivityIssue(c,f.ac)){openRubricEval(")
rep('evaluar: foco desde cuaderno',
    "?.focus();if(f.ac.instrument==='rubric'){const row=f.ac.rubric.rows.findIndex(",
    "?.focus();if(usesIndicators(f.ac)){const row=f.ac.rubric.rows.findIndex(")
rep('evaluar: badge',
    "<span class=\"badge ${ac.instrument==='rubric'?'rubric':''}\">",
    "<span class=\"badge ${usesIndicators(ac)?'rubric':''}\">")
rep('evaluar: celda de la tabla',
    "     if(ac.instrument==='rubric')return `<td><button class=\"btn small\" onclick=\"openRubricEval('${st.id}','${ac.id}')\">Rúbrica</button>",
    "     if(usesIndicators(ac))return `<td><button class=\"btn small\" onclick=\"openRubricEval('${st.id}','${ac.id}')\">${isChecklist(ac)?'Lista':'Rúbrica'}</button>")
rep('evaluar: acciones',
    "${ac.instrument==='rubric'?'<div class=\"toolbar\">'+rubricActions(ac.id)+'</div>':''}",
    "${indicatorInstrument(ac)?'<div class=\"toolbar\">'+rubricActions(ac.id)+'</div>':''}")
rep('trazabilidad',
    "function rubricTraceHtml(c,stu,ac,crit){\n if(ac.instrument!=='rubric'||!ac.rubric?.rows?.length)return'';",
    "function rubricTraceHtml(c,stu,ac,crit){\n if(!usesIndicators(ac)||!ac.rubric?.rows?.length)return'';")
rep('trazabilidad: título',
    "<div class=\"tiny muted\"><b>Desglose de la rúbrica</b></div>",
    "<div class=\"tiny muted\"><b>${isChecklist(ac)?'Desglose de la lista de cotejo':'Desglose de la rúbrica'}</b></div>")
rep('revisión: indicadores huérfanos',
    "const orphan=x.ac.instrument==='rubric'&&Array.isArray(",
    "const orphan=usesIndicators(x.ac)&&Array.isArray(")

# --- Estructura ---
rep('estructura: acciones',
    " ${ac.instrument==='rubric'?`${rubricActions(ac.id)}`:''}",
    " ${indicatorInstrument(ac)?`${rubricActions(ac.id)}`:''}")
rep('estructura: abrir editor al elegir lista',
    "const result=save();if(k==='instrument')render();return result}",
    "const result=save();if(k==='instrument'){render();if(v==='checklist'&&!ac.rubric?.rows?.length)openChecklistEditor(aid)}return result}")
rep('editor: despacho',
    "function openRubricEditor(aid){\n const c=course(),f=findActivity(c,aid),ac=f.ac;",
    "function openRubricEditor(aid){\n if(isChecklist(findActivity(course(),aid)?.ac))return openChecklistEditor(aid);\n const c=course(),f=findActivity(c,aid),ac=f.ac;")
rep('editor: borrar ítem',
    "askConfirm('Borrar indicador de rúbrica',`Se borrará el indicador «${row.label}»",
    "askConfirm(isChecklist(ac)?'Borrar ítem de la lista de cotejo':'Borrar indicador de rúbrica',`Se borrará ${isChecklist(ac)?'el ítem':'el indicador'} «${row.label}»")

# --- Calificar con la ventana de ítems ---
rep('calificar: botón de nivel',
    "><b>${String(l.value).replace('.',',')}</b>${l.label?`<div>${esc(l.label)}</div>`:''}<div class=\"tiny\">${esc(l.description)}</div></button>",
    ">${isChecklist(ac)&&l.label?`<b>${esc(l.label)}</b><div class=\"tiny\">${String(l.value).replace('.',',')}</div>`:`<b>${String(l.value).replace('.',',')}</b>${l.label?`<div>${esc(l.label)}</div>`:''}<div class=\"tiny\">${esc(l.description)}</div>`}</button>")
rep('calificar: ítem sin criterio',
    "<b>${esc(r.label)}</b><span class=\"pill\">${esc(criterionLabel(c,r.criterion))}</span>",
    "<b>${esc(r.label)}</b>${r.criterion&&ac.criteria.includes(r.criterion)?`<span class=\"pill\">${esc(criterionLabel(c,r.criterion))}</span>`:'<span class=\"pill\" style=\"background:#fef3c7;color:#92400e\">Sin criterio: no cuenta</span>'}")
rep('calificar: marcar todos',
    "<div style=\"margin:10px 0\">${scores}</div>${rows||",
    "<div style=\"margin:10px 0\">${scores}</div>${checklistBulkBar(ac,stuid,aid)}${rows||")
rep('calificar: sustituye nota directa',
    " if(ac.instrument==='rubric'&&indicator.criterion&&ac.criteria.includes(indicator.criterion))delete c.grades[",
    " if(usesIndicators(ac)&&indicator.criterion&&ac.criteria.includes(indicator.criterion))delete c.grades[")

# --- Ayuda contextual (también en tutorial/ayuda-contextual.part.html) ---
HELP = [
    ("'Si la actividad usa rúbrica, ábrela y marca el nivel de cada indicador: la nota se calcula sola.',",
     "'Si la actividad usa rúbrica o lista de cotejo con ítems, ábrela y marca el nivel de cada indicador o ítem: la nota se calcula sola. En la lista de cotejo puedes usar «Marcar todos los ítems».',"),
    ("y el instrumento (nota directa o rúbrica).',",
     "y el instrumento (nota directa, rúbrica o lista de cotejo; en la lista eliges una escala —Sí/No, Hecho/A medias/No hecho, Conseguido/En proceso/No conseguido o personalizada— y añades ítems vinculados a criterios).',"),
]
for old, new in HELP: rep('ayuda: ' + old[:30], old, new)


def main():
    text = INDEX.read_text(encoding='utf-8')
    if MARK in text:
        print('La lista de cotejo ya estaba aplicada. No se cambia nada.')
        return
    for desc, old, new, count in R:
        n = text.count(old)
        if n != count:
            sys.exit(f'ERROR: el fragmento «{desc}» aparece {n} veces (se esperaban {count}). No se ha modificado nada.')
        text = text.replace(old, new)
    INDEX.write_text(text, encoding='utf-8')
    part = ROOT / 'tutorial' / 'ayuda-contextual.part.html'
    if part.exists():
        p = part.read_text(encoding='utf-8')
        for old, new in HELP: p = p.replace(old, new)
        part.write_text(p, encoding='utf-8')
    sw = SW.read_text(encoding='utf-8')
    sw = re.sub(r"const CACHE = '([^']*?)(?:-cotejo\d+)?';", lambda m: f"const CACHE = '{m.group(1)}-cotejo{int(time.time())}';", sw, count=1)
    SW.write_text(sw, encoding='utf-8')
    print(f'Lista de cotejo aplicada ({len(R)} cambios). Caché de sw.js renovada.')

if __name__ == '__main__':
    main()
