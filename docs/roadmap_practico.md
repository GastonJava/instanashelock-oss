# Roadmap practico de Instanashelock

Documento vivo para llevar el proyecto desde "crypto bien pensada" a "app local robusta y publicable".

## Estado del snapshot pre-open-source

Este documento conserva el progreso tecnico de un ciclo interno de hardening.
Los identificadores privados de rama y commit se omiten deliberadamente. La
historia publica del proyecto comienza en el repositorio OSS.

Ya implementado en este snapshot:

- File locking real por vault para evitar escritura concurrente.
- Archivo temporal unico por operacion, no mas `passwords.vault.tmp` fijo.
- Backup sin silencios: si falla, ahora el guardado falla explicitamente.
- Guardado atomico endurecido para rutas reales, no solo para la ruta por defecto.
- Deteccion de vault desactualizado al guardar para evitar overwrite silencioso entre dos instancias.
- Recarga manual desde disco cuando hay conflicto de concurrencia, sin merge automatico.
- Parser mas defensivo: payload cifrado obligatorio, validacion de flags y validacion de longitudes del VMK envuelto.
- Errores tipados de storage y formato para que la UI no termine en crash ni en estados ambiguos.
- Manejo de error en UI para alta, edicion, borrado y regeneracion de recovery.
- Hardening Windows real: ruta canonica en `%LOCALAPPDATA%\\Instanashelock`, migracion legacy desde `%APPDATA%\\Vault`, ACLs con herramientas nativas y politica de archivos documentada.
- Politica de clipboard unificada: solo limpia contenido copiado por la app, tanto para passwords como para recovery codes.
- Modo `desactualizado` en UI: bloqueo de acciones de escritura hasta recargar, sin merge automatico.
- Suite ampliada de truncados y mutaciones del parser, con fuzzing basico automatizado y seed fija.
- Script de validacion local reproducible (`run_local_ci.ps1`) con tests, compile y chequeos basicos de higiene runtime.
- Inventario local de dependencias y SBOM basica en `docs/dependency_audit.md` y `docs/sbom_basic.json`.
- Auditoria automatizada de dependencias declaradas mediante `pip-audit`.
- Limites honestos de memoria documentados en `docs/memory_limits.md`.
- Checklist de release local en `docs/release_checklist.md`.
- Respaldo cifrado portable manual (export / restore) para disponibilidad local sin nube propia.
- Spike honesto de `VirtualLock` documentado en `docs/virtual_lock_spike.md`.

Verificacion actual:

- `75 passed` en test suite local.

## Objetivo de v1

Instanashelock v1 apunta a seguridad local robusta para un solo usuario en su propio equipo.

Eso significa:

- no corrupcion conocida del vault por doble instancia
- no perdida silenciosa de datos
- errores controlados y entendibles
- parser defensivo ante vaults malformados
- permisos locales razonables en Windows
- pruebas repetibles para integridad, recovery y concurrencia

Todavia no significa:

- sync o cloud
- multiusuario
- hardening extremo de memoria estilo 1Password
- auditoria externa
- garantias fuertes contra malware con acceso al proceso

## Decision de alcance actual

`Instanashelock v1` se cierra como `v1.0.0` para uso local serio.

Esto implica:

- no mezclar el rediseño grande de `2.0` dentro de esta linea
- no bloquear el cierre por firma de codigo ni publicacion
- dejar CI remota y escaneo remoto de advisories como trabajo futuro, no como bloqueo del uso local

## Etapa 1 - Nucleo local critico

Objetivo: que el vault no se rompa ni se pierda por fallos basicos.

Estado: `COMPLETADA` en este snapshot.

Hecho:

- lock de archivo por vault
- temp file unico por operacion
- backup explicito con error real si falla
- guardado atomico mas robusto
- manejo de segunda instancia con error claro
- rechazo de guardado si otra instancia cambio el vault en disco
- recarga manual explicita del vault desde disco cuando hay conflicto
- tests para lock y backup

Criterio de salida alcanzado:

"Dos instancias no corrompen el vault, no pisan cambios silenciosamente y un fallo de guardado no deja al usuario enganado sobre su backup."

Nota UX/Security actual:

- por ahora existe boton de `Recargar` visible en la UI
- su comportamiento es manual y explicito; no hace merge automatico ni reintentos silenciosos
- puede refinarse mas adelante para mostrarse solo ante conflicto o integrarse mejor en la UX

## Etapa 2 - Robustez del formato y del parser

Objetivo: que un vault corrupto o manipulado no rompa la app de forma fea.

Estado: `COMPLETADA EN HARDENING TECNICO` en este snapshot.

Hecho:

- validacion de version soportada
- validacion de magic
- validacion de payload cifrado obligatorio
- validacion de `has_recovery`
- validacion de longitudes de blobs envueltos
- errores de formato tipados
- cobertura nueva para parser endurecido
- suite amplia de truncados de header para v1, v2 y v3
- mutaciones deterministicas sobre headers validos para comprobar fallo limpio
- fuzzing basico automatizado con seed fija sobre v1, v2 y v3

Pendiente dentro de esta etapa:

- separacion mas fina entre "vault corrupto" y "password incorrecta" en toda la UX

Criterio de salida alcanzado para parser:

"Un vault malformado ya no pasa silenciosamente, y el parser cae en errores tipados o parseo valido sin crashes raros ante truncados y mutaciones basicas."

## Etapa 3 - Seguridad local de Windows

Objetivo: proteger mejor el entorno Windows/local, no solo el cifrado.

Estado: `COMPLETADA` en este snapshot.

Hecho:

- ruta canonica `%LOCALAPPDATA%\\Instanashelock`
- migracion automatica desde `%APPDATA%\\Vault` para instalaciones legacy
- ACLs reales en Windows via herramientas nativas para carpeta y archivos sensibles
- temporales locales por operacion, sin uso de `%TEMP%` global para escrituras del vault
- clipboard policy unificada y consistente entre passwords y recovery codes
- verificacion estatica basica: sin `print(...)` ni `logging` runtime en la app
- manejo UX del estado desactualizado sin merge automatico

Criterio de salida:

"El vault no solo esta cifrado: tambien esta almacenado y manipulado de forma razonable para Windows."

## Etapa 4 - Secretos en memoria

Objetivo: reducir exposicion, sin vender humo.

Estado: `PARCIALMENTE INICIADA`.

Trabajo concreto:

- reducir copias innecesarias de secretos
- acortar vida util de referencias sensibles
- seguir usando limpieza best-effort solo donde sea verificable
- documentar limites reales de Python
- evaluar como spike opcional `VirtualLock` y su costo/beneficio

Ya hecho dentro de esta etapa:

- documento explicito de limites reales en `docs/memory_limits.md`
- claims de memoria acotados a best-effort en la documentacion principal
- evaluacion inicial de `VirtualLock` documentada como `NO-GO` para v1 inmediato

No hacer todavia:

- reescribir el core en Rust/C
- prometer borrado total de RAM

## Etapa 5 - Automatizacion, dependencias y evidencia

Objetivo: pasar de "creo que esta bien" a "puedo demostrar que aguanta".

Estado: `PARCIALMENTE INICIADA`.

Trabajo concreto:

- CI minima para ejecutar tests automaticamente
- dependency audit de `cryptography`, `argon2-cffi`, `pyperclip` y demas
- SBOM basica
- matriz de pruebas de integridad, recovery y concurrencia
- ampliar tests de corrupcion, truncado y restore

Entregables:

- workflow o script reproducible de tests
- reporte de dependencias
- checklist de release tecnica

Ya hecho dentro de esta etapa:

- script local reproducible `scripts/run_local_ci.ps1`
- reporte local `docs/dependency_audit.md`
- SBOM basica `docs/sbom_basic.json`
- auditoria reproducible de dependencias declaradas mediante `pip-audit`

Pendiente dentro de esta etapa:

- llevar este flujo a CI remota en el repo actual
- incorporar escaneo remoto automatizado con `pip-audit` o equivalente
- completar checklist de release tecnica
- decidir si el spike de `VirtualLock` cambia algo del diseno antes de release

## Etapa 6 - Preparacion para publicar

Objetivo: sumar distribucion sin confundirla con seguridad local.

Estado: `PARCIALMENTE COMPLETADA`.

Para Store o distribucion seria hay que agregar explicitamente:

- firma de codigo
- empaquetado limpio
- MSIX si el objetivo real es Microsoft Store
- politica de privacidad publicada
- flujo de instalacion y desinstalacion
- changelog y checklist de release

Avance actual:

- existe checklist de release local
- ya pudimos generar una standalone local con Nuitka
- el instalador real se genero con Inno Setup (`iscc`) en el entorno interno de validacion pre-OSS
- el icono original del proyecto ya esta integrado en la build local
- smoke tests manuales locales `1` a `7` ya quedaron completos y documentados
- instalacion/desinstalacion silenciosa local ya fue verificada en `dist\\install_smoke`
- el flujo nuevo `Opciones avanzadas` / `Destruir vault y datos` ya quedo validado funcionalmente
- queda una deuda UX/UI visual en ese flujo, pero no una brecha funcional

Importante:

Esta etapa no reemplaza las anteriores. Solo agrega confianza de distribucion.

## Etapa 7 - Nivel premium

Objetivo: confianza superior, no necesaria para un primer release.

Mas adelante:

- auditoria externa
- proceso de disclosure
- bug bounty
- hardening mayor de memoria
- posible core sensible fuera de Python

## Checklist actualizado

### Ya en verde

- [x] no hay race condition conocida por temp file fijo
- [x] no hay backup silencioso
- [x] no hay overwrite silencioso conocido por instancia desactualizada
- [x] hay recarga manual segura ante conflicto de concurrencia
- [x] hay tests de concurrencia basicos
- [x] hay tests de backup fallido
- [x] el parser rechaza varios vaults malformados limpiamente
- [x] hay truncados sistematicos y mutaciones basicas automatizadas para el parser
- [x] la UI no crashea ante fallos de guardado mas obvios
- [x] ACLs reales de Windows revisadas para la ruta administrada por la app
- [x] logs revisados para fuga obvia de secretos
- [x] politica completa de temporales y clipboard cerrada
- [x] CI minima local reproducible
- [x] inventario local de dependencias
- [x] SBOM basica
- [x] build local con icono
- [x] instalador local compilable
- [x] verificacion corta post-build del instalador y binario instalado

### Pendiente no bloqueante dentro de `v1`

- [x] documentacion honesta de limites de memoria
- [x] checklist de release local
- [ ] separar mejor en UX "vault corrupto" vs "password incorrecta"
- [ ] polish visual del flujo `Opciones avanzadas` y dialogs destructivos

### Diferido fuera del alcance actual

- CI remota
- escaneo remoto automatizado de advisories de dependencias
- firma de codigo / publicacion real

## Orden practico desde este punto

Si seguimos desde donde estamos ahora, el orden recomendable es:

1. Mantener el checklist de release local y la evidencia sincronizados despues de cada rebuild importante.
2. Usar `Instanashelock v1.0.0` como build local estable sin meter rediseños grandes.
3. Si mas adelante cambia la arquitectura de buffers, reabrir el spike de `VirtualLock`.
4. Reservar `Instanashelock 2.0` para el rework de UX y expansion funcional.

## Nota de criterio

La prioridad sigue igual que al principio: primero integridad real del vault, despues robustez del parser, despues hardening del sistema operativo, y al final distribucion.

Ese orden sigue dando el mayor salto de seguridad real por esfuerzo invertido.

