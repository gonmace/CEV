# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Constructor_EV (CEV)** — Django 5.1+ application for construction project management with AI-powered technical specification generation. All UI, models, and code are in **Spanish**.

## Architecture

### Apps

| App | URL prefix | Purpose |
|-----|-----------|---------|
| `home` | `/` | Landing page, sitemap |
| `proyectos` | `/proyectos/` | Core project + specification management |
| `servicios` | `/servicios/` | Service catalog (categories → subcategories → services) |
| `pliego_licitacion` | `/pliego/` | Multi-step AI specification generation workflow |
| `ubi_web` | `/ubicaciones/` | Geographic locations within projects |
| `theme` | — | Tailwind CSS compilation only |

### Database / Models

**Database table names:** `proyectos` app uses `main_*` prefix (e.g., `main_proyecto`, `main_especificacion`).

Key model relationships:
- `Proyecto` → `Especificacion` (1:N, ordered by `orden` field)
- `Especificacion` → `EspecificacionImagen` (1:N, auto-optimized to 1920px JPEG)
- `Proyecto` → `Ubicacion` (1:N via `ubi_web`)
- `Categoria` → `Subcategoria` → `Servicio` (3-level catalog in `servicios`)
- `EspecificacionTecnica` (in `pliego_licitacion`) links to `Proyecto`

Soft delete pattern: `activo` boolean + `fecha_eliminacion` timestamp — filter with `activo=True`.

Image optimization happens automatically on model save (Pillow, 1920px max, JPEG 85%).

### Frontend

- **Tailwind CSS v4 + DaisyUI v5** — custom themes `constructor` (light) and `constructor-dark`
- CSS source: `theme/static_src/src/styles.css` → compiled to `static/css/dist/styles.css`
- Compiled CSS is **not** auto-served in dev without running `tailwind start`
- Modal patterns used extensively (see `proyectos/templates/proyectos/modals/`)
- Font Awesome icons for sortable table headers

### Template Tags

Custom tags in `proyectos/templatetags/main_tags.py`:
- `sortable_header` — renders sortable table column headers with icons
- `user_avatar_color` — generates avatar color from user ID
- `get_item` — dict access in templates (`dict|get_item:key`)

### Document Export

- Word (`.docx`) export for projects: `proyectos` app, uses `python-docx`
- PDF export for locations: `ubi_web` app
- Content stored as Markdown in `contenido`/`resultado_markdown` fields, rendered with `markdown` library
