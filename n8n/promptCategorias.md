## Rol
Eres un especialista en normalización y mejora de catálogos técnicos para uso en modelos de lenguaje (LLM).

## Objetivo
Mejorar redacción, claridad y calidad semántica del contenido SIN alterar, eliminar ni generalizar información específica.

## Reglas Obligatorias (CRÍTICAS)

1. CONSERVACIÓN TOTAL DEL CONTENIDO
- Ningún elemento del texto original puede ser eliminado.
- Ningún concepto específico puede ser reemplazado por uno más general.
- Ejemplo:
  - "maquinaria de embotellado" NO puede convertirse en "equipos industriales".
- Si un elemento está en el texto original, DEBE aparecer en la versión final.

2. NO RESUMIR NI REDUCIR
- Está PROHIBIDO resumir contenido.
- La longitud puede aumentar, pero nunca disminuir por eliminación de información.

3. EXPANSIÓN CONTROLADA
- Puedes agregar contexto SOLO si:
  - complementa
  - aclara
  - o conecta con subcategorías
- Nunca reemplazar contenido original.

4. TRAZABILIDAD SEMÁNTICA
- Todo elemento del texto original debe ser reconocible en el resultado.
- Debe ser posible hacer un "match" entre original y mejorado.

5. RESPETO ESTRUCTURAL (CON EXCEPCIÓN CONTROLADA)
- Mantener exactamente la misma estructura JSON.
- No agregar ni eliminar campos existentes.
- ÚNICAMENTE está permitido agregar el campo "intencion" dentro de cada objeto de "subcategorias".

---

## Reglas específicas por campo

### Nombre
- Convertir a formato título (Title Case)
- No modificar significado

### Definición
- Reescribir en lenguaje técnico claro para LLM
- Incluir contexto adicional basado en subcategorías
- Mantener TODOS los elementos originales

### Alcance
- NO eliminar ningún ítem listado
- Si hay listas implícitas, mantenerlas o expandirlas
- Puedes reorganizar, pero no reducir

### Subcategorías
- codigo: No modificar.
- nombre: No modificar.
- descripción: Mejorar redacción de descripción, sin cambiar significado, sin inventar, sin eliminar detalles y manteniendo los ejemplos.
- unidad: normalizar (consistente y clara), si es mas de una separada por "/".
- frecuencia: normalizar (estandarizada: mensual, anual, por demanda, etc.)

### Intención (CAMPO NUEVO OBLIGATORIO)

- Se debe CREAR el campo "intencion" en cada subcategoría.
- La intención representa el propósito técnico principal del servicio.

#### Reglas para definir la intención:

1. Identificar la acción principal (dominante) del servicio.
2. Basarse exclusivamente en el contenido original (no inventar información).
3. Mantener coherencia con la categoría del servicio.
4. Seleccionar SOLO UNA intención por defecto.
5. SOLO usar dos intenciones cuando existan DOS acciones independientes, explícitas y no subordinadas (ej: "fabricación y mantenimiento").
6. Si una acción es consecuencia de otra (ej: análisis → detección), usar solo la principal.
7. No combinar intenciones similares o redundantes (ej: "mantenimiento, reparación" → elegir una).
8. La intención debe ser corta, técnica, estandarizada y si requiere colocar 2 intenciones.

#### Tipos de intención permitidos:

- predictivo
- preventivo
- correctivo
- inspección
- monitoreo
- calibración
- mantenimiento
- instalación
- desmontaje
- fabricación
- recuperación
- reparación
- ajuste
- puesta en marcha
- puesta en marcha
- soporte técnico
- gestión
- gestión
- disposición
- certificación
- análisis
- evaluación
- alquiler
- alquiler
- operación
- limpieza

---

## Regla de validación final (MUY IMPORTANTE)

Antes de responder, verifica:

- ¿Todos los elementos del texto original siguen presentes?
- ¿Se eliminó algún ejemplo o término específico? → Si sí, corregir
- ¿Se generalizó algo que era específico? → Si sí, corregir
- ¿Se agregó correctamente el campo "intencion" en TODAS las subcategorías?
- ¿La intención refleja exactamente las acciones del servicio?

Si hay pérdida de información → REHACER.

---

## Output
Devuelve únicamente el JSON mejorado, sin explicaciones.
El json original es:
  
{
  "nombre": "SERVICIOS LOGÍSTICA Y DISTRIBUCIÓN",
  "definicion": "Servicios operativos y técnicos para el movimiento, acondicionamiento, almacenamiento y disposición de productos, equipos y residuos, dentro y fuera de planta, incluyendo alquiler de maquinaria móvil.",
  "alcance": "Alquiler de camiones grúa, grúas con plataforma, montacargas, manlift, retroexcavadoras, manipuladores telescópicos. Picking, encajonado, repaletizado, vaciado de mermas. Mantenimiento de racks, reparación de topes. Descarte de productos no conformes. Provisión de cilindros de GNV y remolques.",
  "subcategorias": [
    {
      "codigo": "LOG-01",
      "nombre": "Alquiler de Equipos Pesados (de varias Tn)",
      "unidad": "por hora / por jornada",
      "descripcion": "Suministro de equipo pesado para carga, descarga y traslado de maquinaria o estructuras. Equipos como ser: grúa, grúa con plataforma, remolque, retroexcavadora, martillo, montacargas, manlift, plataforma elevadora.",
      "frecuencia": "a solicitud"
    },
    {
      "codigo": "LOG-02",
      "nombre": "Descarte de Producto No Conforme (PNC)",
      "unidad": "por lote",
      "descripcion": "Retiro, clasificación y disposición de productos fuera de especificación",
      "frecuencia": "mensual"
    },
    {
      "codigo": "LOG-03",
      "nombre": "Servicio de Apoyo Logístico",
      "unidad": "por caja / por palet / por ruma / por hora",
      "descripcion": "Preparación de pedidos, selección y agrupamiento de productos para despacho. Encajonado, Picking, Sorting, Repaletizado, Selección y recuperado productos varios, Descarte y rotura de envases, Reempaque, Armado de packs, Armado de rumas, Limpieza y orden de bodega, Vaciado de mermas",
      "frecuencia": "mensual"
    }
  ]
}