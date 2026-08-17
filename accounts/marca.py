"""Marca: de quién es, y cómo se aplica a los documentos que genera la app.

La marca es de la empresa (la comparte el equipo) o de la cuenta personal. Si no hay
ninguna configurada, se usan las plantillas por defecto del sistema: configurarla es
opcional y nadie queda bloqueado por no hacerlo.

Lo importante de este módulo es que la configuración **se aplique de verdad** al .docx
que se descarga; si no, sería una pantalla decorativa.
"""
import io
import zipfile

from django.core.files.base import ContentFile

from .models import Marca
from .permissions import get_user_empresa


def marca_de(user, crear=False):
    """La marca que le corresponde a `user`: la de su empresa, o la suya si es personal."""
    if not user or not user.is_authenticated:
        return None
    empresa = get_user_empresa(user)
    filtro = {'empresa': empresa} if empresa else {'usuario': user}
    if crear:
        marca, _ = Marca.objects.get_or_create(**filtro)
        return marca
    return Marca.objects.filter(**filtro).first()


def marca_propia(user, crear=False):
    """La fila Marca PROPIA del usuario, tenga empresa o no.

    Para una cuenta personal es la misma que devuelve `marca_de`. Para un usuario de
    empresa es donde viven sus ajustes personales (hoy: sus plantillas, que pisan a las
    de la empresa). La marca visual (logo, colores, datos) sigue siendo la de la empresa.
    """
    if not user or not user.is_authenticated:
        return None
    if crear:
        marca, _ = Marca.objects.get_or_create(usuario=user)
        return marca
    return Marca.objects.filter(usuario=user).first()


def plantilla_de(user, modulo, ruta_por_defecto):
    """La plantilla .docx a usar para `user`, por precedencia:

    1. La que subió el propio usuario (su override personal).
    2. La de su empresa — el default que define el Administrador (o la de su propia
       marca, si es cuenta personal).
    3. La del sistema (`ruta_por_defecto`).
    """
    propia = plantilla_para(marca_propia(user), modulo, None)
    if propia is not None:
        return propia
    return plantilla_para(marca_de(user), modulo, ruta_por_defecto)


def logo_de(user):
    """El logo a usar para `user`, con la misma precedencia que `plantilla_de`: el que
    subió el propio usuario, o si no el de su empresa (o el suyo, si es cuenta personal)."""
    propia = marca_propia(user)
    if propia and propia.logo:
        return propia.logo
    marca = marca_de(user)
    return marca.logo if marca and marca.logo else None


def puede_editar_marca(user):
    """Quién configura la marca.

    - Cuenta personal: la suya (es solo suya, nadie más la usa).
    - Cuenta de empresa: solo el Administrador. Un usuario cualquiera no debe poder
      cambiarle el logo a los documentos de toda la empresa.
    - Superuser: siempre.
    """
    from .permissions import is_company_admin

    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if get_user_empresa(user) is None:
        return True                      # personal: su marca, su decisión
    return is_company_admin(user)


def hex_a_rgb(color, defecto=(31, 41, 55)):
    """'#1f2937' → (31, 41, 55). Devuelve `defecto` si el valor no es un hex válido."""
    if not color:
        return defecto
    color = color.strip().lstrip('#')
    if len(color) != 6:
        return defecto
    try:
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return defecto


def plantilla_para(marca, modulo, ruta_por_defecto):
    """La plantilla .docx a usar: la propia de la marca si la subió, si no la del sistema.

    Devuelve algo que python-docx pueda abrir (una ruta o un file-like).
    """
    if marca:
        propia = marca.plantilla_proyectos if modulo == 'proyectos' else marca.plantilla_servicios
        if propia:
            try:
                return io.BytesIO(propia.read())
            except (OSError, ValueError):
                pass                      # el archivo se borró del disco: cae a la del sistema
    return ruta_por_defecto


def con_logo(fuente_docx, logo):
    """Sustituye el logo embebido del .docx por `logo` (ver `logo_de` para la precedencia).

    Las plantillas del sistema llevan su logo en `word/media/image1.png`. En vez de tocar el
    XML (frágil), se reescribe el ZIP cambiando ese único archivo por la imagen de la marca:
    el logo conserva la posición y el tamaño que tenía en la plantilla.

    Si no hay logo configurado, devuelve la fuente tal cual.
    """
    if not logo:
        return fuente_docx

    try:
        datos_logo = logo.read()
    except (OSError, ValueError):
        return fuente_docx

    if hasattr(fuente_docx, 'read'):
        fuente_docx.seek(0)
        original = fuente_docx.read()
    else:
        with open(fuente_docx, 'rb') as f:
            original = f.read()

    entrada = zipfile.ZipFile(io.BytesIO(original))
    if 'word/media/image1.png' not in entrada.namelist():
        return fuente_docx                # plantilla sin logo: no hay nada que sustituir

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as nuevo:
        for item in entrada.infolist():
            contenido = entrada.read(item.filename)
            if item.filename == 'word/media/image1.png':
                contenido = datos_logo
            nuevo.writestr(item, contenido)
    salida.seek(0)
    return salida


def insertar_logo(doc, logo, ancho_cm=2.0):
    """Reemplaza el marcador de texto `<<LOGO>>` (encabezados y body) por la imagen de
    marca, con `ancho_cm` de ancho y la altura proporcional (conserva su proporción
    original).

    Si no hay logo configurado (o no se puede leer), el marcador se borra igual: no debe
    quedar un `<<LOGO>>` suelto en el documento solo porque el usuario no cargó logo.

    Es un mecanismo aparte de `con_logo`: ese sustituye una imagen ya embebida en la
    plantilla (conserva la posición/tamaño que tenía ahí); este sirve para plantillas que,
    como el resto de los datos, marcan dónde va el logo con texto `<<LOGO>>` en vez de
    incrustar una imagen editable a mano.
    """
    datos_logo = None
    if logo:
        try:
            logo.seek(0)
            datos_logo = logo.read() or None
        except (OSError, ValueError):
            datos_logo = None

    from docx.shared import Cm

    ancho = Cm(ancho_cm)

    def procesar(container):
        for para in container.paragraphs:
            texto = ''.join(r.text for r in para.runs)
            if '<<LOGO>>' not in texto:
                continue
            texto = texto.replace('<<LOGO>>', '')
            for run in para.runs:
                run.text = ''
            run = para.runs[0] if para.runs else para.add_run()
            run.text = texto
            if datos_logo:
                run.add_picture(io.BytesIO(datos_logo), width=ancho)
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    procesar(cell)

    for section in doc.sections:
        procesar(section.header)
    procesar(doc)
    return doc


def aplicar_colores(doc, marca):
    """Tiñe los títulos del documento con los colores de la marca.

    Se hace sobre los ESTILOS ('Heading 1'…'Heading 4'), no recorriendo los párrafos: así
    afecta a todos los títulos del documento —incluidos los que se generen después— sin
    tener que tocar el exportador, que son 1000 líneas.
    """
    if not marca:
        return doc

    from docx.shared import RGBColor

    primario = RGBColor(*hex_a_rgb(marca.color_primario))
    secundario = RGBColor(*hex_a_rgb(marca.color_secundario, defecto=(107, 114, 128)))

    for nivel in (1, 2, 3, 4):
        try:
            estilo = doc.styles[f'Heading {nivel}']
        except KeyError:
            continue
        # Los dos primeros niveles son los títulos de sección (color principal); del 3 en
        # adelante son subtítulos, que van en el secundario.
        estilo.font.color.rgb = primario if nivel <= 2 else secundario
    return doc


def reemplazar_placeholders(doc, placeholders, placeholders_body=None):
    """Reemplaza marcadores `<<...>>` en los encabezados y en el body de `doc`.

    Recorre párrafos y tablas (incluidas celdas anidadas). El body puede llevar un dict
    distinto al de los encabezados — por ejemplo, para poner el nombre en MAYÚSCULAS solo
    ahí — pasando `placeholders_body`; si no se indica, usa el mismo dict que el header.

    Importante para quien arma la plantilla .docx: el reemplazo colapsa todos los runs
    del párrafo en el primero, así que un marcador y su etiqueta deben ir en párrafos
    separados si tienen formato distinto (si comparten párrafo, el valor sale con el
    formato del primer run de la etiqueta).
    """
    def reemplazar_en_parrafo(para, ph_map):
        texto_completo = ''.join(r.text for r in para.runs)
        if not any(ph in texto_completo for ph in ph_map):
            return
        for ph, val in ph_map.items():
            texto_completo = texto_completo.replace(ph, val)
        for run in para.runs:
            run.text = ''
        if para.runs:
            para.runs[0].text = texto_completo
        else:
            para.add_run(texto_completo)

    def reemplazar_en_contenedor(container, ph_map):
        for para in container.paragraphs:
            reemplazar_en_parrafo(para, ph_map)
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    reemplazar_en_contenedor(cell, ph_map)

    for section in doc.sections:
        reemplazar_en_contenedor(section.header, placeholders)
    reemplazar_en_contenedor(doc, placeholders_body if placeholders_body is not None else placeholders)
    return doc


def placeholders_de(marca):
    """Los placeholders de marca para el .docx. Vacíos si no hay marca configurada, así el
    documento nunca muestra un `<<EMPRESA>>` suelto."""
    if not marca:
        return {
            '<<EMPRESA>>': '', '<<NIT>>': '', '<<DIRECCION>>': '',
            '<<TELEFONO>>': '', '<<WEB>>': '', '<<PIE>>': '',
        }
    return {
        '<<EMPRESA>>': marca.nombre(),
        '<<NIT>>': marca.identificacion_fiscal,
        '<<DIRECCION>>': marca.direccion,
        '<<TELEFONO>>': marca.telefono,
        '<<WEB>>': marca.sitio_web,
        '<<PIE>>': marca.pie_pagina,
    }


# Códigos del <select name="tipo_contrato"> de los modales de exportación (proyectos y
# servicios) → texto legible para el <<TIPO_CONTRATO>> del .docx. Mismos nombres que
# muestran esos selects, para que lo que se elige y lo que se lee en el documento coincidan.
TIPOS_CONTRATO = {
    'CO': 'Contrato de Obra (CO)',
    'SPOT': 'Compra Spot (SPOT)',
    'NCM': 'Nuevo Contrato Marco (NCM)',
    'PFA': 'Precio Fijo con Ajuste Económico (PFA)',
    'PFI': 'Precio Fijo con Incentivo (PFI)',
    'CRF': 'Costo Reembolsable + Honorario Fijo (CRF)',
    'TYM': 'Tiempo y Materiales (TYM)',
}


def tipo_contrato_label(tipo_contrato):
    """El texto a mostrar en <<TIPO_CONTRATO>>: la etiqueta del código si es uno de los
    predefinidos, o el texto tal cual si es el que escribió el usuario en "Personalizado"."""
    return TIPOS_CONTRATO.get(tipo_contrato, tipo_contrato)


def guardar_vista_previa(marca, documento):
    """Guarda un .docx de muestra generado con la marca (para el botón de vista previa)."""
    buffer = io.BytesIO()
    documento.save(buffer)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f'muestra_{marca.pk}.docx')
