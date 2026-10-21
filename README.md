# Nuestro Menú

Aplicación web para que dos personas del mismo hogar organicen los **almuerzos de lunes a domingo**. Comparten recetario, preferencias, menú semanal e historial.

Este directorio es el **repositorio de la app** (código, Docker y `render.yaml`). Vive dentro de `MISAPPS/` solo como carpeta local; el remoto de GitHub/Render debe apuntar aquí, no a MISAPPS.

Desde la carpeta MISAPPS:

```bash
cd nuestro_menu
```

No hay desayunos ni cenas en esta versión. Las recetas se introducen a mano; no hay importación de chats ni archivos de conversación.

## Arquitectura

Django 5.2 (plantillas + HTMX + API REST) y PostgreSQL. La lógica de negocio vive en servicios. El generador de menús es un módulo Python propio, sin APIs de IA.

Ver [docs/decisiones-tecnicas.md](docs/decisiones-tecnicas.md).

## Tecnologías

- Python 3.12 (3.11 también vale en local)
- Django 5.2 LTS, Django REST Framework
- PostgreSQL
- Gunicorn y WhiteNoise (producción)
- Docker Compose (desarrollo)
- PWA (manifest + service worker)

## Requisitos locales

- PostgreSQL (Postgres.app en macOS, o Docker)
- Python 3.11+
- Opcional: Docker Desktop

## Instalación con Postgres.app

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Ajusta `DATABASE_URL` en `.env`. Con Postgres.app suele ser:

```
DATABASE_URL=postgres://TU_USUARIO@localhost:5432/nuestro_menu
```

Crea la base y arranca:

```bash
createdb nuestro_menu
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre http://127.0.0.1:8000/

## Docker

```bash
cp .env.example .env
docker compose up --build
```

En Compose la base es `postgres://postgres:postgres@db:5432/nuestro_menu`.

### Comandos útiles

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py test
docker compose exec web python manage.py collectstatic --no-input
docker compose exec web python manage.py seed_dev
docker compose down
```

`seed_dev` solo funciona con `DEBUG=True`.

## Variables de entorno

Ver `.env.example`. Obligatorio en producción: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`. `DEBUG` debe ser `False`.

## Crear el hogar

1. La primera persona se registra y da nombre al hogar (por ejemplo, Allan).
2. En **Hogar** genera una invitación y copia el enlace.
3. La segunda persona abre el enlace y crea su cuenta (Naiara), o inicia sesión y acepta la invitación.

Cada receta, preferencia y menú queda aislado por hogar. No se pueden adivinar datos ajenos cambiando un UUID en la URL.

## Recetario y preferencias

Alta, edición, búsqueda, filtro por categoría, orden por nombre o fecha, archivo (sin borrar) y reactivación. Si el nombre coincide ignorando mayúsculas y espacios, se pide confirmación; no se fusionan recetas solas.

Las recetas evitadas por **cualquier** miembro no entran en el generador.

## Generador

Calcula puntuaciones (recencia, frecuencia en menús **aprobados**, favoritos y notas de ambos, variedad de categoría, similitud de nombres y un poco de azar). Prueba hasta 200 combinaciones y guarda la mejor como borrador, en una transacción. Si no hay siete recetas compatibles, no guarda nada.

Un menú aprobado no se sustituye sin confirmación. Regenerar una semana en borrador actualiza el mismo plan.

## PWA

En **Instalar** hay instrucciones para Android (Chrome) e iPhone (Safari → Añadir a pantalla de inicio). El service worker cachea CSS, JS e iconos. No cachea la API. Sin edición offline.

## API

Sesión + CSRF. Ejemplos:

- `GET/POST /api/recipes/`
- `GET/PATCH /api/recipes/{id}/`
- `GET /api/meal-plans/{week_start}/`
- `POST /api/meal-plans/{week_start}/generate/`
- `PATCH /api/meal-plans/{week_start}/entries/{day}/`
- `POST /api/meal-plans/{week_start}/approve/`
- `GET/POST /api/preferences/`
- `GET/PATCH /api/household/`
- `GET/POST /api/invitations/`

`week_start` y `day` van en formato `AAAA-MM-DD`. El lunes define la semana.

## Tests

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Copias de seguridad (sin coste)

Exportar:

```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission > backup.json
pg_dump "$DATABASE_URL" > backup.sql
```

Restaurar:

```bash
python manage.py loaddata backup.json
psql "$DATABASE_URL" < backup.sql
```

## Despliegue (preparado, no ejecutado)

Este repositorio incluye `render.yaml`, `build.sh`, `Procfile` y settings de producción. **No se ha desplegado** porque se eligió entorno solo local y porque Heroku no es gratuito.

Cuando se quiera un hosting a 0 €:

1. Crear cuenta en Render (plan Free, **sin** método de pago si quieres evitar cargos por ancho de banda extra).
2. Crear proyecto Neon Free y copiar la URL con *pooler*.
3. Crear un repositorio en GitHub **solo con el contenido de esta carpeta** (`nuestro_menu/`), no con toda MISAPPS.
4. Crear el web service Free y pegar `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
5. No crear Render Postgres Free (caduca a los 30 días).

Límites: el servicio se duerme, Neon también, y no hay correo SMTP en Render Free.

## Diagnóstico

- `/health/` debe devolver `{"status": "ok", "database": true}`.
- Si el generador falla, comprueba que hay al menos siete recetas activas y no evitadas, distintas de las de la semana anterior aprobada.
- Los secretos no deben ir al repositorio. No copies `.env`.
