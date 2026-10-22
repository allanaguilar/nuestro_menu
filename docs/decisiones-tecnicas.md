# Decisiones técnicas del MVP

## Alojamiento y coste

Heroku no se usa: el plan Eco y Postgres Essential tienen coste mensual. El presupuesto es 0 €.

La combinación prevista para un despliegue futuro (no ejecutado en este MVP) es:

- Render Free para la aplicación web.
- Neon Free para PostgreSQL persistente.

No se usa Render Postgres Free porque caduca a los 30 días y puede borrar datos.

Límites a asumir si se despliega así:

- Render suspende el servicio tras unos 15 minutos sin tráfico. El siguiente visitante espera alrededor de un minuto.
- 750 horas de instancia gratis al mes.
- Neon escala a cero a los 5 minutos. Los datos no se borran por inactividad.
- 1 GB de almacenamiento y 100 CU-hora de cómputo al mes en Neon Free.
- No hay disponibilidad permanente ni correo SMTP saliente en Render Free (puertos 25/465/587 bloqueados).

## Base de datos

PostgreSQL es obligatorio. No hay SQLite ni en desarrollo ni en producción. En local se puede usar Postgres.app o el servicio `db` de Docker Compose.

## Autenticación e invitaciones

La segunda persona entra con un enlace de invitación de un solo uso y caducidad de 7 días. No se envía correo porque el plan gratuito de Render no permite SMTP. La recuperación de contraseña está cableada a las vistas de Django y a un backend de correo configurable (consola por defecto).

## Historial de comidas

El generador trata los menús **aprobados** como aproximación de lo que se ha comido. No hay confirmación real de que el plato se sirvió. Esta limitación está reflejada en la interfaz del historial.

## Generador

Algoritmo propio en Python. Evalúa hasta 200 combinaciones, con semilla opcional para pruebas. Restricciones duras al generar: recetas activas del hogar, no evitadas por ningún miembro, siete distintas, exclusión de la semana anterior aprobada. Si no hay siete compatibles, no se guarda nada. Un cambio manual sí puede repetir un plato en la misma semana.

## PWA

El service worker cachea solo estáticos y la página `/offline/`. Las respuestas de la API y las páginas privadas no se guardan en caché compartida. No hay edición offline.

## Fuera de alcance

- Importación de chats de WhatsApp o archivos CSV. Sí hay pegado de lista en Recetario.
- Desayunos y cenas.
- Despliegue real en este momento (solo local, a petición).
