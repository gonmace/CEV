# Activar Header Auth en los webhooks de n8n

Los 14 webhooks de producción están hoy sin autenticación: cualquiera que conozca la URL
puede dispararlos y quemar créditos de OpenAI sin pasar por el sistema de créditos de la
app. Ya está preparado el lado Django (header `X-N8N-Webhook-Token` en cada llamada
saliente a n8n — ver `core/settings.py`: `N8N_WEBHOOK_TOKEN`/`N8N_WEBHOOK_TOKEN_HEADER`)
y la credencial del lado n8n (`httpHeaderAuth`, nombre "CEV Django webhook token", id
`DLxkeqekA0LPoKjb`).

**Falta el último paso — activar `authentication: headerAuth` en los 14 nodos Webhook —
y NO debe hacerse hasta que el Django con este código esté desplegado en el VPS con
`N8N_WEBHOOK_TOKEN` en su `.env`.** Activarlo antes corta la generación de pliegos y
servicios en producción (401 en cada llamada).

## 1. Desplegar

1. Desplegar el commit que agrega `N8N_WEBHOOK_TOKEN` (`core/settings.py`,
   `pliego_licitacion/views.py`, `servicios/views.py`, `ubi_web/views.py`).
2. Agregar al `.env` del VPS: `N8N_WEBHOOK_TOKEN=<el valor que quedó en tu .env local
   y en la credencial de n8n>`.
3. Reiniciar el contenedor `django`.

## 2. Verificar que hoy sigue abierto (antes de activar nada)

```bash
curl -sS -X POST https://cev-n8n.magoreal.com/webhook/coherencia \
  -H 'Content-Type: application/json' -d '{}'
```

## 3. Activar los 14 nodos

Con las herramientas MCP de n8n (`mcp__cev-n8n__n8n_update_partial_workflow`), para
cada fila de esta tabla:

| Workflow ID | Workflow | Nodo |
|---|---|---|
| `K4Q1d6am3nw5hDol` | EspTec_01coherencia | `1` |
| `FBkAgL2qVgN6a5W2` | EspTec_02-04parametros | `parametros` |
| `7jKzUdByuUj9KMJx` | EspTec_05ajustar_titulo | `3` |
| `t5ECNpZHiE7AAl3q` | EspTec_06adicionales | `adicionales` |
| `aOUWeB6FkVHPWa5R` | EspTec_07final | `final` |
| `Boutet2dokkoMKbM` | EspSer_01coherencia | `1` |
| `IopKSotVuEvIFZhL` | EspSer_02objetivo | `1` |
| `3HL8w1k4iZafgs9M` | EspSer_03-1_clasificar | `Webhook Clasificador` |
| `DeFl3MaClWsFBRHB` | EspSer_03-3_estructur | `Webhook Alcance` |
| `N3OF1eGpOOtQ9AAL` | EspSer_04_+secciones | `Webhook Secciones` |
| `PYavEwJJfEDPELOE` | EspSer_03-2_Equipos | `Webhook Extractor` |
| `PYavEwJJfEDPELOE` | EspSer_03-2_Equipos | `Webhook Ajustar` |
| `PYavEwJJfEDPELOE` | EspSer_03-2_Equipos | `Webhook PDF Vision` |
| `LnC8ex7bFjCF1PTv` | ubicacion | `1` |

Operación (probada con `validateOnly: true` el 17-ago-2026, no aplicada):

```json
{
  "id": "<Workflow ID>",
  "operations": [{
    "type": "updateNode",
    "nodeName": "<Nodo>",
    "updates": {
      "parameters.authentication": "headerAuth",
      "credentials.httpHeaderAuth": {"id": "DLxkeqekA0LPoKjb", "name": "CEV Django webhook token"}
    }
  }]
}
```

`EspSer_03-2_Equipos` tiene 3 webhooks: se pueden actualizar los 3 nodos en una sola
llamada con 3 operaciones en el array.

## 4. Verificar después de activar

```bash
# Sin header: debe dar 403 ahora
curl -sS -o /dev/null -w '%{http_code}\n' -X POST \
  https://cev-n8n.magoreal.com/webhook/coherencia \
  -H 'Content-Type: application/json' -d '{}'

# Con header: debe funcionar igual que antes
curl -sS -X POST https://cev-n8n.magoreal.com/webhook/coherencia \
  -H 'Content-Type: application/json' \
  -H "X-N8N-Webhook-Token: $N8N_WEBHOOK_TOKEN" -d '{}'
```

Y probar el flujo completo (pliego pasos 1→8, una especificación de servicio) desde la
app en producción con una cuenta real, revisando que no aparezcan 502/500 nuevos.
