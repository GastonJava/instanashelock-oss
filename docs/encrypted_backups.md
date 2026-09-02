# Respaldos cifrados portables

Instanashelock v1 permite exportar una copia portable del vault cifrado. El archivo no contiene datos en claro y sigue requiriendo la master password correcta para abrirse.

## Como usarlo

- Desbloquea tu vault y abre `Opciones` > `Exportar respaldo cifrado`.
- Guarda el archivo `.instanashelock-backup` en un lugar bajo tu control.
- Para recuperarlo en otra instalacion o en un equipo nuevo, usa `Restaurar respaldo cifrado` desde la pantalla inicial.

## Buenas practicas

- Trata el archivo exportado como sensible aunque este cifrado.
- Instanashelock no lo sube, sincroniza ni elimina por ti.
- Si lo guardas en Google Drive, Dropbox o una nube similar, protege esa cuenta con MFA.
- Conserva los recovery codes aparte del respaldo; no los guardes en la misma carpeta.
- Despues de importar, el archivo fuente sigue intacto; borralo manualmente solo si era temporal.
- La resistencia del respaldo depende de la fuerza real de tu master password.
