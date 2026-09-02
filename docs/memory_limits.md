# Limites honestos de memoria

Instanashelock intenta reducir exposicion de secretos en memoria, pero no promete algo que Python y Windows no puedan cumplir de forma verificable.

## Lo que si hacemos hoy

- La VMK y el diccionario de entries se limpian en `wipe_secrets()` al bloquear o cerrar la ventana principal.
- El borrado de bytes usa `ctypes.memset` y mutacion de `bytearray` como medida best-effort en CPython.
- El clipboard se limpia con TTL y solo si todavia contiene exactamente lo que copio la app.
- El auto-lock corta la sesion y reduce el tiempo de vida de secretos en la UI.
- La app evita logs runtime con plaintext, recovery codes, VMK o blobs cifrados.

## Lo que no podemos prometer honestamente

- No podemos garantizar borrado total de RAM en CPython.
- Las `str` de Python son inmutables; puede haber copias temporales fuera del buffer que tocamos.
- `tk.StringVar`, `tk.Entry`, serializacion JSON, librerias C y el propio interprete pueden crear copias transitorias que no controlamos.
- Windows puede paginar memoria a disco, volcar crash dumps, hibernar o dejar rastros fuera del proceso.
- Un debugger, un admin local o malware con acceso al proceso puede inspeccionar memoria mientras la app esta abierta.
- Copiar al clipboard nunca equivale a "one time paste"; otras apps pueden leerlo multiples veces mientras siga ahi.

## Lo que eso significa para v1

- Instanashelock ofrece higiene razonable de secretos en una app local Python, no hardening extremo estilo password manager nativo con componentes dedicados.
- El wipe actual debe leerse como `best-effort`, no como prueba de destruccion criptografica de todos los residuos en RAM.
- No afirmamos resistencia contra malware ya presente en el host, contra un usuario administrador o contra analisis forense avanzado de memoria.
- Compilar con Nuitka puede cambiar distribucion y ergonomia, pero no transforma por si solo este modelo de riesgo.

## Decisiones conscientes para este release

- No vamos a vender "memory safe" ni "RAM wipe garantizado".
- No metemos `VirtualLock` en v1 sin una evaluacion tecnica que justifique su costo/beneficio y sus limites reales.
- Priorizamos reducir tiempo de exposicion y evitar copias evitables antes que agregar claims imposibles de validar.

## Recomendaciones operativas

- Usa Instanashelock solo en un equipo que controles.
- Mantene cifrado de disco, usuario protegido y sistema operativo al dia.
- Bloquea la app cuando no la uses.
- Trata clipboard, pantalla y memoria del host como superficie sensible mientras el vault este abierto.

## Siguiente escalon realista

- Revisar si hay copias de secretos que podamos acortar en dialogs concretos.
- Evaluar `VirtualLock` como spike medido, documentando de antemano que no evita malware ni debug local.
- Llevar esta misma honestidad a la documentacion publica del release.
