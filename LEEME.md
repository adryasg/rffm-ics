# Partidos RFFM -> calendario .ics

1. Crea en github.com un repositorio **público** (p. ej. `rffm-ics`) y sube todo el contenido de esta carpeta (Add file > Upload files; incluye la carpeta oculta `.github`).
2. Edita `config.json`: pon el nombre del equipo tal como sale en la RFFM y la URL del calendario de su grupo.
3. Settings > Pages > Source: "Deploy from a branch", rama `main`, carpeta `/docs`.
4. Actions > "Actualizar partidos RFFM" > Run workflow. Se repite solo cada 6 horas.
5. Tu calendario queda en `https://TU_USUARIO.github.io/rffm-ics/partidos.ics`.
