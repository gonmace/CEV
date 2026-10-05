# Workflows n8n versionados

Exports de los workflows de n8n que usa CEV. `docker-compose.yml` monta esta
carpeta en el contenedor de n8n (solo lectura) y `make n8n-import`
(`docker/n8n-import.sh`) los importa con `n8n import:workflow --separate`.

| Archivo | Workflow en n8n | Webhook |
|---|---|---|
| `EspTec_01coherencia.json` … `EspTec_07final.json` | Flujo de especificaciones técnicas | `coherencia`, `parametros`, `titulo`, `adicionales`, `final` |
| `Ubicacion_sitio.json` | `ubicacion_proyecto` | `ubicacion` |
| `Objetivo_proyecto.json` | `objetivo_proyecto` | `objetivo` |

## Importar / actualizar `ubicacion` y `objetivo`

1. **Backup**: antes de importar, exporta desde la UI de n8n el workflow
   `ubicacion` actual (Download), porque la importación con el mismo id
   (`LnC8ex7bFjCF1PTv`) lo sobrescribe en el servidor.
2. Importa: `make n8n-import`, o en la UI de n8n → Workflows → *Import from File*
   con cada JSON.
3. Abre cada workflow importado y verifica que la credencial "OpenAi account"
   quedó resuelta en el nodo del modelo (si el id de la credencial difiere en tu
   instancia, selecciónala de nuevo a mano).
4. Activa ambos workflows (toggle *Active*).
5. Smoke test:

```bash
curl -sS -X POST "$N8N_BASE_URL/webhook/objetivo" -H 'Content-Type: application/json' \
  -d '{"proyecto_nombre":"Tinglado escolar","solicitante":"GAM Tarija","ubicacion":"Tarija","descripcion":"Construcción de tinglado de 20x30 m sobre cancha existente."}'

curl -sS -X POST "$N8N_BASE_URL/webhook/ubicacion" -H 'Content-Type: application/json' \
  -d '{"nombre":"Cancha central","ciudad":"Tarija","coordenadas_texto":"-21.535000, -64.729700","latitud":-21.535,"longitud":-64.7297,"proyecto_nombre":"Tinglado escolar","ruta":{"vias":"Av. Panamericana","distancia":"4,2 km","duracion":"12 min","resumen":"El acceso al sitio se realiza desde el centro de Tarija por Av. Panamericana."},"tiene_ruta":true}'
```

Se espera `{"output":"..."}`. Para `ubicacion`, el output debe empezar con `###`
(sin H1, sin preámbulo conversacional, sin Plus Codes).

6. Cuando se haga el rollout de Header Auth, incluye los nodos webhook de estos
   dos workflows (ver `docs/activar-auth-webhooks-n8n.md`).
