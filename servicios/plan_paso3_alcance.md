# Plan Completo — Generación de Alcance (Paso 3)

## Análisis del catálogo (67 subcategorías, 8 categorías)

El campo `intencion` puede ser **múltiple** (ej: `"fabricación, recuperación"`, `"montaje, desmontaje"`).
Las 5 familias de tabla estándar cubren todos los casos:

| Familia | Intenciones | Columnas |
|---------|-------------|----------|
| **Actividades** | preventivo, correctivo, mantenimiento, ajuste, montaje, desmontaje, instalación, puesta en marcha, reparación, monitoreo, calibración, tratamiento | N° · Actividad · Descripción · Unidad · P.U. (Bs) |
| **Inspección** | predictivo | N° · Equipo/Sistema · Punto de Inspección · Parámetro · Frecuencia · Unidad |
| **Fabricación/Recuperación** | fabricación, recuperación | N° · Descripción del Ítem · Material / Proceso · Unidad · P.U. (Bs) |
| **Personal Técnico** | soporte técnico | Rol · Descripción de tareas · Jornada · Unidad · P.U. (Bs) |
| **Equipos/Suministros** | alquiler, suministro, adquisición, logística | N° · Descripción · Especificaciones Técnicas · Cant. · Unidad · P.U. (Bs) |

---

## ⚠️ Ajuste 1 — Multi-intención → Múltiples tablas

El catálogo usa `intencion` como string con comas: `"fabricación, recuperación"`.
Se parsea como array en el backend antes de enviarlo al webhook:

```python
intencion_raw = sub.get('intencion', '')
intenciones = [i.strip() for i in intencion_raw.split(',')]
```

Payload al webhook:
```json
{
  "intenciones": ["preventivo", "correctivo", "instalacion"],
  ...
}
```

El AI genera **una sección con su tabla por cada intención**, en el orden en que aparecen.

---

## ⚠️ Ajuste 2 — Bloques de texto además de tablas

Estructura completa esperada del alcance:

```markdown
## Alcance

[Párrafo introductorio técnico — 2 a 4 oraciones]

### [Nombre de la primera intención, ej: Mantenimiento Preventivo]
[tabla markdown]

### [Nombre de la segunda intención, ej: Mantenimiento Correctivo]
[tabla markdown]

### Condiciones Operativas          ← cuando aplique
[texto]

### Gestión de Repuestos            ← cuando aplique
[texto: quién provee, procedimiento]

### Requerimientos SSMA             ← cuando aplique
[texto]
```

---

## ⚠️ Ajuste 3 — Sin info suficiente = no generar tabla, preguntar

Regla explícita en el prompt:

> Si para una tabla no tienes suficiente información para completar al menos 3 filas con datos
> concretos y no genéricos: NO generes esa tabla. En su lugar, devuelve `tipo: "pregunta"`.

---

## ⚠️ Ajuste 4 — Limpieza de HTML (Function Node en n8n)

Después del HTTP Request, un nodo **Code** limpia el HTML:

```javascript
const text = $json.body
  .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
  .replace(/<style[\s\S]*?>[\s\S]*?<\/style>/gi, '')
  .replace(/<[^>]+>/g, '')
  .replace(/\s{2,}/g, ' ')
  .trim();

return [{ json: { contexto_web: text.slice(0, 8000) } }];
```

---

## ⚠️ Ajuste 5 — Historial limitado a últimas 4 entradas

En el JS del template:

```javascript
body: JSON.stringify({
  historial: historial.slice(-4),
  url_referencia,
  texto_referencia
})
```

---

## ⚠️ Ajuste 6 — Versionado del alcance en el modelo

```python
alcance_generado = models.TextField(blank=True, verbose_name="Alcance generado por IA")
alcance_editado  = models.TextField(blank=True, verbose_name="Alcance editado por usuario")
```

- `alcance_generado`: se guarda tal como llegó del AI, nunca se modifica después
- `alcance_editado`: lo que el usuario guarda (puede ser igual, editado o reescrito)
- En el resto del sistema siempre se usa `alcance_editado` (fallback a `alcance_generado` si vacío)

---

## ⚠️ Ajuste 7 — Validación de formato en el backend

```python
alcance_raw = request.POST.get('alcance', '').strip()
tiene_header = '## alcance' in alcance_raw.lower()
tiene_tabla  = '|' in alcance_raw

if not tiene_header or not tiene_tabla:
    messages.warning(request, 'El alcance no tiene el formato esperado. Revísalo antes de guardar.')

servicio.alcance_generado = servicio.alcance_generado or alcance_raw  # solo primera vez
servicio.alcance_editado  = alcance_raw
servicio.save(update_fields=['alcance_generado', 'alcance_editado'])
```

---

## Flujo de preguntas (máx. 2 en toda la conversación)

| Familia | Pregunta 1 | Pregunta 2 |
|---------|-----------|-----------|
| Actividades | ¿Equipos o sistemas sobre los que se realizará el servicio? | ¿Actividades principales a incluir? |
| Inspección | ¿Equipos o puntos de inspección específicos? | ¿Parámetros o anomalías que se monitorean? |
| Fabricación/Recuperación | ¿Tipo de piezas o componentes? | ¿Materiales o procesos relevantes? |
| Personal Técnico | ¿Tipo de personal y régimen de trabajo? | ¿Actividades principales que ejecutará? |
| Equipos/Suministros | ¿Equipos o materiales a adquirir/alquilar? | ¿Especificaciones técnicas mínimas? |

---

## Referencia técnica — dos opciones excluyentes

```
📋 Información de referencia del equipo/servicio (opcional)

  [ 🔗 Pegar enlace ]   [ 📄 Pegar texto ]
```

- **Enlace** → n8n: HTTP Request → Code (limpia HTML) → `contexto_web`
- **Texto pegado** → n8n: va directo como `contexto_web`
- **Ninguno** → AI trabaja solo con título/descripción/objetivo/historial

Payload:
```json
{
  "historial": [...],
  "url_referencia": "https://...",
  "texto_referencia": "..."
}
```

---

## Paso 1 — Modelo (`servicios/models.py`)

```python
alcance_generado = models.TextField(blank=True, verbose_name="Alcance generado por IA")
alcance_editado  = models.TextField(blank=True, verbose_name="Alcance editado por usuario")
```

Crear y aplicar migración.

---

## Paso 2 — URLs (`servicios/urls.py`)

```python
path('<int:servicio_id>/alcance/',         views.paso3_alcance_view,   name='paso3_alcance'),
path('<int:servicio_id>/alcance/generar/', views.generar_alcance_ajax, name='generar_alcance_ajax'),
```

---

## Paso 3 — Vistas (`servicios/views.py`)

**Constante:**
```python
N8N_WEBHOOK_SER_ALCANCE_URL = 'https://n8n.magoreal.com/webhook/ser-alcance'
```

**Cambiar redirect en `paso2_objetivo_view`:**
```python
return redirect('servicios:paso3_alcance', servicio_id=servicio.id)
```

**`paso3_alcance_view`:**
- GET → renderiza template
- POST → valida formato, guarda `alcance_generado` (solo primera vez) y `alcance_editado`,
  redirige a `ver_servicio`

**`generar_alcance_ajax`:**
- Busca `intencion` de la subcategoría en el catálogo activo
- Parsea como lista: `[i.strip() for i in intencion_raw.split(',')]`
- Envía al webhook con `intenciones`, `historial`, `url_referencia`, `texto_referencia`

---

## Paso 4 — Template `paso3_alcance.html`

- Badge "3", título "Alcance del Servicio", subtítulo `{{ servicio.titulo }}`
- Card `shadow-xl`, breadcrumb: Inicio › Servicios › Nuevo Servicio › Alcance
- AI Spinner overlay idéntico al paso2
- Toggle referencia técnica: tab "Enlace" / tab "Pegar texto"
- 4 bloques: spinner, pregunta, resultado (textarea editable), error
- Botón único: "Guardar y continuar"
- JS: `historial.slice(-4)` en cada llamada

---

## Paso 5 — n8n workflow `EspSer_03alcance`

**Nodos:**
```
Webhook
  → Set (formatea contexto)
  → If (url_referencia no vacío)
      → [sí] HTTP Request → Code (limpia HTML, slice 8000)
      → [no] If (texto_referencia no vacío)
                → [sí] Set (contexto_web = texto_referencia)
                → [no] Set (contexto_web = "")
  → Merge
  → AI Agent (system prompt multi-intención)
  → Structured Output Parser
  → Respond to Webhook
```

**System prompt** (en `parameters.options.systemMessage`):
```
Eres un asistente especializado en generar el ALCANCE para pliegos de licitación bolivianos.

DATOS QUE RECIBES:
- titulo, descripcion, objetivo del servicio
- intenciones: array con los tipos de trabajo (ej: ["preventivo", "correctivo"])
- historial: últimas interacciones (máx. 4)
- contexto_web: ficha técnica o texto pegado por el usuario (puede estar vacío)

REGLA MULTI-TABLA:
Genera UNA sección con su tabla por cada intención del array.
Usa la tabla estándar correspondiente:
- predictivo → [N° | Equipo/Sistema | Punto de Inspección | Parámetro | Frecuencia | Unidad]
- preventivo, correctivo, mantenimiento, instalación, ajuste, montaje, desmontaje,
  calibración, reparación, monitoreo, tratamiento, puesta en marcha
  → [N° | Actividad | Descripción | Unidad | P.U. (Bs)]
- fabricación, recuperación → [N° | Descripción del Ítem | Material/Proceso | Unidad | P.U. (Bs)]
- soporte técnico → [Rol | Descripción de tareas | Jornada | Unidad | P.U. (Bs)]
- alquiler, suministro, adquisición, logística
  → [N° | Descripción | Especificaciones Técnicas | Cant. | Unidad | P.U. (Bs)]

REGLA DE CALIDAD:
Si para una tabla no tienes información suficiente para completar AL MENOS 3 filas con datos
concretos y específicos (no genéricos): NO generes esa tabla. Devuelve tipo "pregunta".

PREGUNTAS: máximo 2 en toda la conversación.
Solo pregunta si la información no está en título/descripción/objetivo Y no está en el historial.
Si contexto_web tiene datos, úsalos para rellenar filas — no inventes especificaciones.
Deja "—" en columnas de precio (P.U.) — el usuario las completa después.

BLOQUES ADICIONALES (incluir cuando aplique):
- ### Condiciones Operativas
- ### Gestión de Repuestos
- ### Requerimientos SSMA

FORMATO DE SALIDA (markdown):
## Alcance
[Párrafo introductorio técnico, 2-4 oraciones]

### [Nombre legible de la intención]
[tabla markdown]

### [Siguiente intención si existe]
[tabla markdown]

[Secciones adicionales si aplican]
```

**Structured Output Parser schema:**
```json
{
  "tipo":     { "type": "string", "enum": ["pregunta", "alcance"] },
  "pregunta": { "type": "string" },
  "alcance":  { "type": "string" }
}
```

---

## 💡 Mejoras Pro (siguiente iteración)

| Mejora | Descripción |
|--------|-------------|
| Motor de bloques | Bloques reutilizables por tag insertados automáticamente por n8n según categoría |
| Auto-tags | El AI devuelve `tags: ["refrigeración", "preventivo"]` para filtrado futuro |
| Pre-fill desde catálogo | n8n inyecta equipos del catálogo como filas base para que el AI solo ajuste |
| Modo copiar pliego | Pegar PDF/texto completo → generar alcance estructurado |

---

## Orden de ejecución

| # | Tarea |
|---|-------|
| 1 | Modelo: `alcance_generado` + `alcance_editado` + migración |
| 2 | n8n: crear workflow `EspSer_03alcance` |
| 3 | `views.py`: constante + vistas + cambiar redirect de paso2 |
| 4 | `urls.py`: agregar las 2 rutas |
| 5 | Template: `paso3_alcance.html` |
