# VirtualLock spike honesto

Objetivo: evaluar si `VirtualLock` mejora de forma material la proteccion de secretos en Instanashelock v1 sin caer en claims exagerados.

## Resumen ejecutivo

Decision actual: `NO-GO` para implementarlo ya en v1.

Motivo corto:

- `VirtualLock` puede ayudar a que algunas paginas no se paginen mientras estan bloqueadas.
- No arregla el problema principal de Instanashelock hoy: la app sigue usando `str`, `tk.StringVar`, widgets Tk, JSON y buffers temporales que pueden crear copias fuera de cualquier region bloqueada.
- Meterlo ahora daria mas complejidad que seguridad verificable.

## Lo que VirtualLock si hace

- Pide a Windows que mantenga paginas comprometidas en RAM mientras esten bloqueadas.
- Evita que esas paginas bloqueadas se escriban al pagefile mientras el lock siga activo.
- Requiere paginas comprometidas y un rango alineado a pagina.

## Lo que VirtualLock no hace

- No evita que haya otras copias del secreto en memoria.
- No protege contra malware, debugger, admin local ni lectura del proceso mientras esta vivo.
- No protege contenido ya copiado al clipboard.
- No garantiza nada sobre strings inmutables de Python o buffers internos de Tk.
- No es un "memory safe mode".

## Limites tecnicos relevantes para Instanashelock

- El limite de paginas bloqueables depende del working set minimo del proceso y Windows lo mantiene intencionalmente chico.
- Si se quieren bloquear mas paginas puede hacer falta tocar `SetProcessWorkingSetSize`, lo que complica permisos y costo operativo.
- Un uso agresivo puede degradar el sistema bajo presion de memoria.
- La app hoy no centraliza secretos en buffers mutables dedicados; por lo tanto no hay un unico lugar util para bloquear.

## Lectura aplicada a nuestro codigo actual

Hoy los secretos pasan por:

- `str` de Python para master password y entry passwords
- `tk.Entry` y `tk.StringVar`
- serializacion JSON
- blobs de `bytes`
- clipboard

Aunque bloquearamos algunos `bytes` con `VirtualLock`, seguirian existiendo copias potenciales en otras capas. Eso reduce mucho la ganancia real para v1.

## Cuando si tendria sentido retomarlo

- Si migramos secretos de flujo critico a `bytearray` o buffers dedicados controlados por nosotros.
- Si podemos encapsular el material sensible en regiones pequenas y bien delimitadas.
- Si definimos un ciclo de vida claro: alloc -> lock -> uso corto -> wipe -> unlock.
- Si agregamos pruebas/telemetria local que demuestren que el lock realmente se aplica a las paginas elegidas.

## Spike tecnico recomendado mas adelante

Un spike razonable seria de laboratorio, no de producto final:

1. Reservar un buffer mutable chico solo para una key derivada o una VMK.
2. Alinear y bloquear ese rango con `ctypes` + `VirtualLock`.
3. Verificar el estado via `QueryWorkingSetEx`.
4. Limpiar, desbloquear y medir fallos.
5. Documentar costo, complejidad y cobertura real.

## Criterio de entrada para v1

Solo considerar inclusion en v1 si se cumplen todas:

- existe un buffer sensible acotado y mutable
- el lock es verificable y estable
- no rompe UX ni compatibilidad
- el beneficio supera claramente la complejidad
- la documentacion sigue diciendo `best-effort`, no seguridad absoluta

## Conclusion actual

`VirtualLock` es interesante como spike tecnico posterior, pero hoy no cambia lo suficiente el modelo de riesgo real de Instanashelock como para justificar meterlo en v1.

La mejor inversion inmediata sigue siendo:

- minimizar copias evitables
- acortar tiempo de vida de secretos
- mantener claims honestos
- fortalecer release/CI/evidencia

## Fuentes tecnicas primarias

- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtuallock
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualunlock
- https://learn.microsoft.com/nl-nl/windows/win32/api/memoryapi/nf-memoryapi-setprocessworkingsetsize
- https://learn.microsoft.com/en-us/windows/desktop/Memory/working-set
- https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-queryworkingsetex
