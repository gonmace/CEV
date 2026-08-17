"""Créditos por módulo: saldo, tope individual y consumo.

Reglas del sistema (ver el plan de negocio):

- **1 crédito = 1 entregable.** Los pasos intermedios del flujo (coherencia, parámetros,
  título, objetivo, alcance…) no cuestan; solo se cobra el que produce el resultado.
- El saldo se lleva **por módulo** (`accounts.permissions.MODULE_KEYS`), porque un cliente
  puede tener contratado Proyectos y no Servicios.
- Una cuenta **de empresa** consume de la bolsa compartida de su empresa, con un tope
  individual opcional. Una cuenta **personal** consume de su propia bolsa.
- El **superuser no consume** (mismo criterio que `permissions.has_capability`, que le da
  bypass: sus acciones son administrativas, no de cliente).

Todo pasa por `consumir()`, que descuenta de forma atómica. No descontar a mano en las
vistas: hacerlo fuera de la transacción abre la puerta a gastar el mismo crédito dos veces.
"""
from django.db import transaction
from django.db.models import Sum

from .models import BolsaCreditos, ConsumoCredito, TopeUsuario
from .permissions import get_user_empresa


class SinCreditos(Exception):
    """No se puede consumir: sin saldo en la bolsa o tope individual alcanzado.

    El mensaje va dirigido al usuario final, así que se puede mostrar tal cual."""


def _es_ilimitado(user):
    """El superuser no gasta créditos: su uso es administrativo, no de cliente."""
    return bool(user and user.is_authenticated and user.is_superuser)


def bolsa_de(user, modulo, crear=False):
    """La bolsa de la que consume `user` en ese módulo: la de su empresa si pertenece a
    una, la suya propia si es cuenta personal. Devuelve None si no existe y `crear=False`."""
    empresa = get_user_empresa(user)
    filtro = {'empresa': empresa} if empresa else {'usuario': user}
    if crear:
        bolsa, _ = BolsaCreditos.objects.get_or_create(
            modulo=modulo, defaults={'creditos': 0}, **filtro,
        )
        return bolsa
    return BolsaCreditos.objects.filter(modulo=modulo, **filtro).first()


def saldo(user, modulo):
    """Créditos disponibles en la bolsa que le aplica. None = ilimitado (superuser)."""
    if _es_ilimitado(user):
        return None
    bolsa = bolsa_de(user, modulo)
    return bolsa.creditos if bolsa else 0


def modulos_activos(user):
    """Módulos con saldo (créditos > 0, o ilimitado) que le aplican a `user` — su empresa
    si pertenece a una, su bolsa personal si no. Un módulo en 0 significa que esa
    empresa/cuenta solo tiene contratado el otro. Si los dos están en 0 no hay forma de
    descartar ninguno, así que se devuelven ambos."""
    from .permissions import MODULE_KEYS

    activos = [modulo for modulo in MODULE_KEYS if saldo(user, modulo) != 0]
    return activos or list(MODULE_KEYS)


def consumido_por(user, modulo):
    """Cuántos créditos lleva gastados este usuario en el módulo (para el tope individual)."""
    total = ConsumoCredito.objects.filter(usuario=user, modulo=modulo).aggregate(
        t=Sum('cantidad'))['t']
    return total or 0


def validar_tope(target, modulo, tope):
    """Mensaje de error si `tope` supera el saldo de la bolsa que le aplica a `target`
    en ese módulo; None si es válido.

    La regla: el tope REPARTE los créditos que hay, no promete créditos que la bolsa no
    tiene. Con el saldo en None (superuser, que no consume) no hay nada que validar."""
    maximo = saldo(target, modulo)
    if maximo is not None and tope > maximo:
        return (
            f'El tope ({tope}) no puede superar los créditos disponibles '
            f'del módulo ({maximo}).'
        )
    return None


def disponible(user, modulo):
    """Créditos que ESTE usuario puede gastar todavía. None = ilimitado (superuser).

    Es el número que se le muestra al usuario en los dashboards: la bolsa que le aplica,
    pero acotada por su tope individual si lo tiene — a quien tiene tope no le sirve ver
    el saldo completo de la empresa, porque no puede gastarlo."""
    if _es_ilimitado(user):
        return None
    bolsa = saldo(user, modulo)
    tope = tope_de(user, modulo)
    if tope is None:
        return bolsa
    return min(bolsa, max(0, tope - consumido_por(user, modulo)))


def tope_de(user, modulo):
    """Tope individual del usuario, o None si no tiene (puede gastar toda la bolsa)."""
    fila = TopeUsuario.objects.filter(usuario=user, modulo=modulo).first()
    return fila.tope if fila else None


def puede_consumir(user, modulo, cantidad=1):
    """(True, '') si puede generar; (False, motivo) si no. El motivo se muestra al usuario."""
    if _es_ilimitado(user):
        return True, ''
    if not user or not user.is_authenticated:
        return False, 'Necesitas iniciar sesión.'

    disponibles = saldo(user, modulo)
    if disponibles < cantidad:
        empresa = get_user_empresa(user)
        if empresa:
            return False, (
                f'La empresa {empresa.nombre} se quedó sin créditos en este módulo. '
                'Pide al administrador que recargue.'
            )
        return False, 'Te quedaste sin créditos en este módulo. Contacta al administrador para recargar.'

    tope = tope_de(user, modulo)
    if tope is not None and consumido_por(user, modulo) + cantidad > tope:
        return False, (
            f'Alcanzaste tu límite personal de {tope} créditos en este módulo, '
            'aunque la empresa todavía tenga saldo.'
        )
    return True, ''


@transaction.atomic
def consumir(user, modulo, referencia='', cantidad=1):
    """Descuenta créditos y registra el consumo. Lanza SinCreditos si no alcanza.

    El bloqueo de fila (`select_for_update`) es lo que impide que dos generaciones
    simultáneas gasten el mismo último crédito: la segunda espera a que la primera
    termine y entonces ve el saldo ya descontado.
    """
    if _es_ilimitado(user):
        return None

    empresa = get_user_empresa(user)
    filtro = {'empresa': empresa} if empresa else {'usuario': user}

    bolsa = (
        BolsaCreditos.objects.select_for_update()
        .filter(modulo=modulo, **filtro)
        .first()
    )
    if bolsa is None or bolsa.creditos < cantidad:
        _, motivo = puede_consumir(user, modulo, cantidad)
        raise SinCreditos(motivo or 'Sin créditos disponibles.')

    # El tope se revalida acá dentro, ya con la fila bloqueada: comprobarlo solo antes
    # dejaría pasar dos consumos simultáneos que juntos superan el límite.
    tope = tope_de(user, modulo)
    if tope is not None and consumido_por(user, modulo) + cantidad > tope:
        raise SinCreditos(
            f'Alcanzaste tu límite personal de {tope} créditos en este módulo.'
        )

    bolsa.creditos -= cantidad
    bolsa.save(update_fields=['creditos', 'actualizado'])

    return ConsumoCredito.objects.create(
        usuario=user, empresa=empresa, modulo=modulo,
        cantidad=cantidad, referencia=referencia,
    )


def revertir(user, modulo, referencia):
    """Deshace el último `consumir()` con esa `referencia` (p. ej. la IA respondió con
    error después de haber cobrado). Devuelve el crédito a la bolsa y borra el
    `ConsumoCredito` que dejó el cobro, para no dejar rastro de algo que no se entregó.

    No hace nada si no hay nada que revertir (superuser, o ya revertido antes).
    """
    if _es_ilimitado(user):
        return

    empresa = get_user_empresa(user)
    filtro = {'empresa': empresa} if empresa else {'usuario': user}

    with transaction.atomic():
        consumo = (
            ConsumoCredito.objects.select_for_update()
            .filter(modulo=modulo, referencia=referencia, usuario=user)
            .first()
        )
        if consumo is None:
            return
        bolsa = BolsaCreditos.objects.select_for_update().filter(modulo=modulo, **filtro).first()
        if bolsa is not None:
            bolsa.creditos += consumo.cantidad
            bolsa.save(update_fields=['creditos', 'actualizado'])
        consumo.delete()


def recargar(destino, modulo, cantidad):
    """Suma créditos a la bolsa de una Empresa o de un User. Devuelve la bolsa."""
    from .models import Empresa

    filtro = {'empresa': destino} if isinstance(destino, Empresa) else {'usuario': destino}
    with transaction.atomic():
        bolsa, _ = BolsaCreditos.objects.select_for_update().get_or_create(
            modulo=modulo, defaults={'creditos': 0}, **filtro,
        )
        bolsa.creditos += cantidad
        bolsa.save(update_fields=['creditos', 'actualizado'])
    return bolsa


def fijar(destino, modulo, cantidad):
    """Deja la bolsa EXACTAMENTE en `cantidad` (no suma). Devuelve la bolsa.

    Es lo que usa el editor de la empresa: ahí se escribe el saldo que debe quedar, que es
    más natural que calcular mentalmente cuánto hay que sumar para llegar a él.
    """
    from .models import Empresa

    filtro = {'empresa': destino} if isinstance(destino, Empresa) else {'usuario': destino}
    with transaction.atomic():
        bolsa, _ = BolsaCreditos.objects.select_for_update().get_or_create(
            modulo=modulo, defaults={'creditos': 0}, **filtro,
        )
        bolsa.creditos = max(0, cantidad)
        bolsa.save(update_fields=['creditos', 'actualizado'])
    return bolsa


def resumen_creditos(user):
    """[{key, label, saldo, tope, consumido}] por módulo — para dashboards y fichas."""
    from .permissions import MODULES

    filas = []
    for key, label in MODULES:
        filas.append({
            'key': key,
            'label': label,
            'saldo': saldo(user, key),          # None = ilimitado (superuser)
            'tope': tope_de(user, key),
            'consumido': consumido_por(user, key),
        })
    return filas


def anotar_creditos(users):
    """Cuelga `user.creditos` en cada usuario de la lista, para la tabla de cuentas.

    Igual que `permissions.anotar_modulos`: resuelve toda la página en 3 queries (bolsas,
    topes y consumos agregados) en vez de llamar a saldo()/tope_de()/consumido_por() por
    usuario y módulo, que sería un N+1 por celda.

    Cada entrada: {key, label, saldo, tope, consumido, ilimitado}.
    """
    from .permissions import MODULES

    users = list(users)
    if not users:
        return users

    empresas = {
        u.pk: getattr(getattr(u, 'profile', None), 'empresa', None) for u in users
    }
    ids_empresa = {e.pk for e in empresas.values() if e}

    bolsas_empresa = {
        (b.empresa_id, b.modulo): b.creditos
        for b in BolsaCreditos.objects.filter(empresa_id__in=ids_empresa)
    }
    bolsas_usuario = {
        (b.usuario_id, b.modulo): b.creditos
        for b in BolsaCreditos.objects.filter(usuario__in=users)
    }
    topes = {
        (t.usuario_id, t.modulo): t.tope
        for t in TopeUsuario.objects.filter(usuario__in=users)
    }
    consumos = {
        (c['usuario'], c['modulo']): c['total']
        for c in ConsumoCredito.objects.filter(usuario__in=users)
        .values('usuario', 'modulo').annotate(total=Sum('cantidad'))
    }

    for user in users:
        empresa = empresas[user.pk]
        user.creditos = []
        for key, label in MODULES:
            if empresa:
                disponible = bolsas_empresa.get((empresa.pk, key), 0)
            else:
                disponible = bolsas_usuario.get((user.pk, key), 0)
            user.creditos.append({
                'key': key,
                'label': label,
                'saldo': disponible,
                'tope': topes.get((user.pk, key)),
                'consumido': consumos.get((user.pk, key), 0),
                'ilimitado': user.is_superuser,
            })

        # Si la lista ya pasó por permissions.anotar_modulos, se fusionan ambas en una sola
        # estructura: el template pinta el toggle y su consumo en la misma celda, y Django
        # no sabe recorrer dos listas en paralelo.
        modulos = getattr(user, 'modulos', None)
        if modulos:
            por_key = {c['key']: c for c in user.creditos}
            for m in modulos:
                m.update({
                    k: v for k, v in por_key.get(m['key'], {}).items()
                    if k in ('saldo', 'tope', 'consumido', 'ilimitado')
                })
    return users


def totales_en_circulacion():
    """{modulo: créditos} sumando todas las bolsas — para la barra de resumen."""
    return {
        fila['modulo']: fila['total']
        for fila in BolsaCreditos.objects.values('modulo').annotate(total=Sum('creditos'))
    }


def equipo_de(user):
    """{'usados': n, 'contratados': n} de la empresa del usuario, o None si es personal.

    Los dashboards muestran esto en la tarjeta "Usuarios". Una cuenta personal no tiene
    equipo, así que devuelve None y la tarjeta directamente no se pinta — antes se
    mostraba el total de usuarios de TODA la plataforma, que además filtraba a una empresa
    cuántos clientes tiene el sistema.
    """
    empresa = get_user_empresa(user)
    if empresa is None:
        return None
    return {
        'usados': empresa.usuarios_activos,
        'contratados': empresa.max_usuarios,
        'nombre': empresa.nombre,
    }
