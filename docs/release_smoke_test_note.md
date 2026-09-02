# Release Smoke Test Note

Registro de la validacion manual de la build candidata local.

Completar solo despues de ejecutar cada prueba. No usar esta nota para marcar trabajo no realizado.

Registro historico pre-open-source: documenta un hito interno y no una release
publica. Los identificadores privados de rama, commit y maquina se omiten.

## Metadata

- Fecha: 2026-04-06
- Contexto fuente: snapshot interno pre-open-source
- Ejecutable probado: `dist\instanashelock.dist\instanashelock.exe`
- Instalador probado: `dist\Instanashelock_Setup_1.0.0.exe`
- Entorno: Windows aislado; detalles del host omitidos
- Resultado general: `OK`

## Build y contexto

- `.\scripts\ci.ps1` usado como baseline antes del smoke test: `SI`
- `iscc` disponible en el entorno de prueba: `SI`
- El icono original del proyecto estaba presente al momento de la build: `SI`
- Observaciones de contexto:
  - Baseline tecnico regenerado el `2026-04-06`; la salida local dependiente de maquina no forma parte del snapshot OSS.
  - Build candidata presente en `dist\instanashelock.dist\instanashelock.exe`.
  - Timestamp del ejecutable base del smoke manual: `2026-04-06 14:24:42`.
  - Instalador local presente en `dist\Instanashelock_Setup_1.0.0.exe`.
  - Instalacion y desinstalacion silenciosa verificadas en `dist\install_smoke`.
  - Launcher aislado disponible en `.\scripts\launch_release_smoke.ps1`.
  - Sesion aislada actual: `dist\smoke_session`.
  - Vault canonico de esta pasada: `dist\smoke_session\LOCALAPPDATA\Instanashelock\passwords.vault`.
  - Vault legacy de prueba: `dist\smoke_session\APPDATA\Vault\passwords.vault`.

## Smoke tests ejecutados

### 1. Crear vault nuevo y reabrirlo

- Estado: `OK`
- Nota:
  - Vault nuevo creado en la sesion aislada `dist\smoke_session`.
  - Verificado en disco `dist\smoke_session\LOCALAPPDATA\Instanashelock\passwords.vault`.
  - Backup inicial presente como `passwords.vault.bak`.
  - Validacion tecnica local: desencripta correctamente con `example-only-password-do-not-use`, `has_recovery=True`, `entries=0`.
  - Reapertura manual del `.exe` confirmada sobre la misma sesion con `example-only-password-do-not-use`.

### 2. Agregar, editar y borrar una entry

- Estado: `OK`
- Nota:
  - Entrada de prueba creada manualmente, editada y luego eliminada en la sesion aislada.
  - Verificacion tecnica posterior: el vault vuelve a `entries=0`.
  - Backup local sigue presente despues del ciclo de escritura.

### 3. Copiar password y verificar limpieza de clipboard a 30s

- Estado: `OK`
- Nota:
  - Copia inicial verificada manualmente sobre una entry temporal.
  - A los 30 segundos, el clipboard ya no conservaba la password copiada por la app.
  - Observacion UX: el texto pequeno de ayuda queda visible, pero no muestra countdown vivo para el copiado normal; seria mejor exponer un timer decreciente claro hasta `0`.

### 4. Probar recovery codes y limpieza de clipboard a 60s

- Estado: `OK`
- Nota:
  - Copia inicial de recovery codes verificada manualmente desde el dialogo de `Recovery`.
  - El countdown de `60s` baja en vivo correctamente.
  - A los 60 segundos, el clipboard ya no conservaba los recovery codes copiados por la app.
  - Hallazgo UX adicional: si el usuario entra al flujo `Recuperar vault` pero no recuerda sus recovery keys, no existe un camino explicito tipo `Olvidaste tus recovery codes`.
  - Estado actual observado: el usuario puede cancelar el dialogo de ingreso, pero para llegar al reset visible desde unlock hoy necesita agotar intentos de recovery.
  - Esto no bloquea la seguridad del vault, pero si genera friccion y puede empujar al usuario a probar codigos basura solo para destrabar el flujo.

### 5. Abrir dos instancias y verificar modo `desactualizado`

- Estado: `OK`
- Nota:
  - Conflicto reproducido con dos instancias sobre la misma sesion aislada.
  - La segunda ventana entra en modo `desactualizado` al intentar una escritura sobre un vault ya modificado por la primera.
  - Verificado manualmente: `+ Nueva entrada` queda deshabilitado, `Recovery` queda deshabilitado y `Recargar` pasa a estado visual de alerta.
  - Verificado manualmente: despues de `Recargar`, la ventana vuelve a quedar usable y muestra el estado actualizado del vault.
  - Decision UX mantenida: no se agrega polling ni refresco silencioso; la deteccion en intento de escritura y la recarga manual siguen siendo el comportamiento deseado para evitar merges ambiguos.

### 6. Corromper `passwords.vault` y validar restore desde `.bak`

- Estado: `OK`
- Nota:
  - `passwords.vault` principal fue corrompido intencionalmente en la sesion aislada.
  - La UI detecto el vault danado y ofrecio `Intentar abrir backup local`.
  - Restore manual desde `.bak` confirmado con exito.
  - El vault volvio a abrir con `example-only-password-do-not-use`.
  - Resultado esperado: el backup restaurado contenia una version anterior del vault, por eso reabrio con `1` entry en lugar de las `2` que existian en el principal mas reciente.

### 7. Validar migracion legacy `%APPDATA%\Vault` -> `%LOCALAPPDATA%\Instanashelock`

- Estado: `OK`
- Nota:
  - Escenario de prueba preparado con un vault valido en la ruta legacy `%APPDATA%\Vault` y sin vault previo en `%LOCALAPPDATA%\Instanashelock`.
  - Al iniciar la app, el vault y su backup fueron migrados a `%LOCALAPPDATA%\Instanashelock`.
  - Verificacion tecnica: el vault migrado abre correctamente con `example-only-password-do-not-use` y conserva los datos esperados.
  - Importante: desde la UI la migracion puede verse "igual que siempre" porque el contenido no cambia; lo que cambia es la ubicacion fisica del vault en disco.
  - Hallazgo original del smoke manual: quedo `passwords.vault.lock` en la carpeta legacy.
  - Seguimiento posterior: el cleanup de ese `.lock` ya fue corregido en codigo y cubierto por `tests/test_storage.py`.

## Evidencia guardada

- Salida de `.\scripts\ci.ps1`: corrida local completada; el log dependiente de maquina no se exporto al snapshot OSS
- `docs/dependency_audit.md`: actualizado `SI`
- Snapshot manual de advisories: generado durante el hito privado; retirado del paquete OSS en favor de `pip-audit` reproducible
- `docs/sbom_basic.json`: actualizado `SI`
- Capturas o notas adicionales:
  - Smoke tests `1` a `7` completados sobre `dist\smoke_session`.
  - El bloque manual de validacion local queda cubierto.
  - Instalador Inno Setup compilado y verificado localmente.
  - Follow-up tecnico del `2026-04-06`: cleanup del `.lock` legacy implementado, `68 passed` en CI y build/installer regenerados.
  - Validacion interactiva adicional completada en Windows; las capturas temporales locales no forman parte del snapshot OSS.
  - Hallazgo en esa validacion: la build previa abria una consola/Windows Terminal al lanzar la app.
  - Seguimiento posterior: `packaging\nuitka_flags.txt` ahora usa `--windows-console-mode=disable`; artefactos regenerados.
  - Follow-up funcional del `2026-04-07`: el flujo `Opciones avanzadas` con `Desinstalar app` / `Destruir vault y datos` quedo validado funcionalmente en `dev smoke`.
  - Seguimiento post-build del `2026-04-07`: artefactos regenerados.
  - Verificacion corta post-build: instalacion silenciosa OK en `dist\install_smoke` y arranque breve del binario instalado OK.
  - Follow-up post-renaming del `2026-04-07`: `.\scripts\ci.ps1` volvio a quedar en verde con `71 passed`.
  - Artefactos renombrados regenerados tras el cambio de marca a `Instanashelock`.
  - Smoke corto release verificado: arranque OK de `dist\instanashelock.dist\instanashelock.exe` en sesion aislada y carpeta canonica creada en `dist\smoke_session\LOCALAPPDATA\Instanashelock`.
  - Instalacion/desinstalacion silenciosa post-renaming verificada sobre una build funcional equivalente en `dist\install_smoke\Instanashelock`.
  - Salvedad abierta: la deuda restante de ese flujo es UX/UI visual del modal y dialogs; no se observo fallo funcional.
  - Cierre administrativo del `2026-04-07`: versionado alineado a `v1.0.0`, `75 passed` en CI, ejecutable regenerado (`instanashelock.exe` `2026-04-07 17:48:13`), instalador recompilado (`Instanashelock_Setup_1.0.0.exe` `2026-04-07 17:48:53`) y smoke corto del `.exe` OK en sesion aislada.

## Bloqueos abiertos despues del smoke test

- Bloqueo 1: Sigue pendiente una pasada visual de UX/UI para el modal `Opciones avanzadas` y la confirmacion de destruccion de vault.
- Decision de alcance actual: firma de codigo y publicacion quedan diferidas hasta que exista una via gratuita realista.
- Decision recomendada: mantener esa deuda como polish de frontend, no como bloqueo funcional del release local.

## Cierre

- Esta build puede considerarse `hito local`: `SI`
- Esta build puede considerarse `release candidata`: `SI (local, sin firma de codigo)`
- Proximo paso: usar `Instanashelock v1.0.0` como build local estable y abrir `2.0` solo cuando decidamos arrancar el rework.


