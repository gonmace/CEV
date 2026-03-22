# Template de Word para Exportación

## Cómo usar un template personalizado

Para que los documentos Word exportados tengan encabezados y pies de página personalizados:

1. **Crea un archivo Word** con el nombre `template_especificaciones.docx`
2. **Colócalo en este directorio:** `esp_web/templates/word_templates/`
3. **Configura en el template:**
   - **Encabezado:** Agrega tu logo y texto en el encabezado del documento
   - **Pie de página:** Agrega texto y números de página en el pie de página
   - **Estilos:** Define los estilos que quieras usar (fuentes, tamaños, etc.)

## Placeholders disponibles en el encabezado

Puedes usar los siguientes placeholders en el encabezado del template y se reemplazarán automáticamente con los datos del proyecto:

- `<<PROYECTO>>` → Nombre del proyecto
- `<<SOLICITANTE>>` → Nombre del solicitante
- `<<SERVICIO>>` → Descripción del proyecto (o ubicación si no hay descripción)
- `<<REV>>` o `<<REV.>>` → Número de revisión (por defecto "1")
- `<<FECHA>>` → Fecha de creación del proyecto (formato: DD/MM/YYYY)

### Ejemplo de uso de placeholders

En el encabezado de tu template, puedes escribir:

```
PROYECTO: <<PROYECTO>>
SOLICITANTE: <<SOLICITANTE>>
SERVICIO: <<SERVICIO>>
REV.: <<REV>>  FECHA: <<FECHA>>
```

Y se reemplazará automáticamente con los datos reales del proyecto.

## Ejemplo de uso

1. Abre Microsoft Word
2. Crea un nuevo documento
3. Ve a **Insertar > Encabezado** y agrega tu logo y texto con los placeholders
4. Ve a **Insertar > Pie de página** y agrega texto (ej: "Página X de Y")
5. Guarda el archivo como `template_especificaciones.docx` en este directorio

## Notas importantes

- El template debe tener el nombre exacto: `template_especificaciones.docx`
- Los encabezados y pies de página del template se conservarán en los documentos exportados
- El contenido del proyecto se agregará al cuerpo del documento
- Los placeholders funcionan tanto en texto simple como en tablas del encabezado
- Si no existe el template, se creará un documento nuevo sin encabezados/pies de página

## Ubicación del template

```
esp_web/
  templates/
    word_templates/
      template_especificaciones.docx  ← Coloca tu template aquí
```

