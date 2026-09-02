# Roadmap aterrizado de Instanashelock 2.0

Documento vivo para preparar el rework grande de `Instanashelock 2.0` sin mezclarlo con el cierre operativo de `v1`.

## Regla madre de este documento

Este roadmap NO reemplaza el roadmap actual de `v1`.

`v1` sigue su curso normal hasta quedar cerrada tecnicamente como `v1.0.0` local estable. La firma/publicacion quedan diferidas fuera del alcance actual.

`v2` se planifica aparte para evitar:

- contaminar `v1` con rediseños grandes a mitad del cierre
- mezclar decisiones de UX con decisiones de seguridad y release
- abrir demasiados frentes al mismo tiempo
- romper una base ya usable por perseguir una vision mas ambiciosa antes de tiempo

## Vision de producto

`Instanashelock 2.0` apunta a convertirse en una version mucho mas profesional de la app:

- UX de escritorio mucho mas madura y estructurada
- layout multipanel moderno
- mejor jerarquia visual y navegacion
- base preparada para crecer por features sin rehacer todo otra vez
- mismo criterio de `security first` o mejor que `v1`

La idea no es copiar ciegamente otra app.

La idea es tomar como inspiracion una UX avanzada tipo password manager comercial y reconstruir Instanashelock sobre esa direccion, usando como base el core seguro que ya tenemos.

## Tesis central de ejecucion

El orden de trabajo para `v2` sera este:

1. Rehacer la arquitectura UX/UI.
2. Adaptar primero lo que YA funciona en la app actual a la nueva UX.
3. Cerrar un primer `v2` funcional local-first.
4. Recién despues agregar features nuevos, uno por uno.
5. No pasar al siguiente feature hasta cerrar bien el anterior.

Eso significa que el primer objetivo real de `v2` no es "tener todo".

Es tener:

- nueva shell visual
- nuevo flujo de navegacion
- mismo core seguro reutilizado
- mismas operaciones criticas funcionando
- cero humo

## Decisiones de producto ya tomadas

### 1. `v1` y `v2` viven separadas

- `v1` se cierra como producto util, local y serio
- `v2` nace como rework mayor
- no se mete el rediseño grande dentro de `v1`

### 2. `Security first` sigue siendo criterio rector

El rediseño no puede degradar:

- integridad del vault
- guardado atomico
- backups
- manejo de conflictos entre instancias
- recovery
- validacion defensiva del formato
- reglas operativas locales de seguridad

### 3. `v2` arranca como `local-first`

Al inicio NO se considera objetivo:

- nube
- sync entre dispositivos
- multiusuario
- cuentas online
- suscripciones
- telemetria invasiva

Si algun dia aparece cloud, sera una etapa aparte.

### 4. No cambiar a base de datos al inicio salvo necesidad real

Decision inicial:

- mantener el vault cifrado local como backend principal
- no migrar a SQLite en la primera fase del rework

Motivo:

- hoy el storage actual ya resuelve bien el caso local single-user
- agregar base de datos aumenta complejidad operativa y superficie a endurecer
- no necesitamos ese costo antes de validar la nueva UX y la nueva arquitectura de pantallas

Reevaluar solo si `v2` exige de verdad:

- consultas complejas
- tags o filtros avanzados de gran escala
- historial rico
- colas de sync
- multiples tipos de item con metadatos mas pesados

### 5. Politica de migracion: `v1` -> `v2` si, `v2` -> `v1` no

Decision tomada:

- `v2` debe poder importar o migrar vaults creados en `Instanashelock v1`
- no se promete compatibilidad de vuelta desde `v2` hacia `v1`
- no se congela el diseno interno de `v2` para seguir escribiendo en formato `v1`

Reglas de implementacion para esa migracion:

- la migracion debe ser local y offline
- requiere la master password correcta del vault `v1`
- el vault `v1` original no se destruye ni se sobreescribe durante el proceso
- `v2` crea su propio vault/estructura destino y copia los datos
- si la migracion falla, el vault `v1` debe quedar intacto
- los items de `v1` se importan primero como tipos equivalentes simples, por ejemplo `login/account`
- notas o campos heredados de `v1` deben preservarse aunque `v2` luego tenga modelos mas ricos

Alcance minimo prometido:

- importar cuentas/entries existentes de `v1`
- preservar username, password, servicio y notas
- conservar la posibilidad de seguir usando `v1` por separado si el usuario no quiere cortar todavia

No objetivo:

- no hacer sincronizacion bidireccional entre `v1` y `v2`
- no hacer downgrade automatico desde `v2` hacia `v1`
- no atar la arquitectura de `v2` a limitaciones del formato viejo mas de lo necesario

## Base reutilizable desde `v1`

`Instanashelock 2.0` NO arranca de cero en lo sensible.

Se reaprovecha todo lo que ya esta bien:

- `crypto.py`
- `storage.py`
- `header.py`
- `recovery.py`
- `security.py`
- politica de clipboard
- autolock
- conflicto por fingerprint y recarga manual
- formato de vault endurecido
- tests del core y parser

En otras palabras:

- `v1` nos deja una buena base de seguridad
- `v2` reconstruye sobre esa base, no contra ella

## Objetivo del primer `v2` funcional

Antes de pensar en features nuevos, el primer hito real de `v2` sera:

"La app ya corre con el nuevo UX multipanel, usando el core seguro actual, y permite crear, desbloquear, listar, buscar, ver, crear, editar, borrar, bloquear y recargar sin perder las garantias de seguridad de `v1`."

Eso es el verdadero piso de `2.0`.

## No objetivos iniciales

Mientras no exista un `v2` base funcional, NO entrar en:

- cloud sync
- almacenamiento remoto
- extensiones de navegador
- autofill
- shared vaults
- organizacion por equipos
- biometria compleja
- importadores masivos de muchos formatos nuevos
- analytics
- sistema de pagos
- suscripcion

## Arquitectura UX objetivo

La direccion visual objetivo para `v2` es:

- sidebar izquierda persistente
- barra superior con busqueda, filtros y acciones globales
- panel intermedio para lista contextual de entradas
- panel principal para detalle o empty state
- mejor jerarquia tipografica
- mejor balance de espacios, densidad y estados
- dialogs mas consistentes con la app

La experiencia debe sentirse:

- mas pro
- mas clara
- mas ordenada
- mas escalable para crecer

Pero sin vender humo de "enterprise" antes de resolver bien lo basico.

## Etapa 0 - Preparacion sin mezclar con `v1`

Objetivo: dejar claro que `v2` es un frente aparte.

Entregables:

- roadmap separado de `v1`
- decisiones iniciales de arquitectura escritas
- spec del flujo de autenticacion en `docs/auth_flow_v2.md`
- arquitectura paralela en `docs/v2_architecture.md`
- lista de reutilizacion del core actual
- lista de no-objetivos para no dispersarnos

Criterio de salida:

"Podemos cerrar `v1` sin tocar su hoja de ruta, y cuando llegue el momento arrancar `v2` con una direccion clara."

## Etapa 1 - Shell nueva de aplicacion

Objetivo: construir la nueva carcasa visual sin meter todavia complejidad innecesaria.

Trabajo concreto:

- definir layout base multipanel
- definir barra lateral
- definir top bar
- definir panel de lista
- definir panel de detalle / empty state
- definir sistema base de espaciado, colores, estados y jerarquia
- definir comportamiento responsive dentro del desktop resize razonable

Debe existir aunque todavia haya datos mockeados o una adaptacion parcial.

Criterio de salida:

"La app ya tiene la nueva estructura visual y navegarla no se siente como la `v1` maquillada."

## Etapa 2 - Adaptacion del core actual al nuevo UX

Objetivo: conectar la shell nueva con la funcionalidad real ya existente.

Trabajo concreto:

- crear vault
- desbloquear vault
- listar entradas reales
- buscar entradas
- ver detalle de entrada
- crear entrada
- editar entrada
- borrar entrada
- copiar password
- bloquear vault
- recargar desde disco
- recovery y estados criticos minimos

Regla:

No agregar features nuevos aqui.

Solo trasladar y adaptar lo ya funcional a la nueva arquitectura UX.

Criterio de salida:

"La nueva app ya puede reemplazar a la `v1` en el flujo principal local, aunque todavia no tenga extras."

## Etapa 3 - Paridad de seguridad y estados criticos

Objetivo: garantizar que el rework visual no rompio los flujos delicados.

Trabajo concreto:

- modo desactualizado por conflicto
- errores de guardado claros
- vault corrupto vs password incorrecta
- recovery input
- regeneracion de recovery
- autolock
- borrado seguro best-effort en cierre/bloqueo
- dialogs destructivos consistentes

Esto no es polish.

Es parte del piso minimo serio de `v2`.

Criterio de salida:

"Los flujos de error y seguridad de `v2` no son peores que los de `v1`."

## Etapa 4 - Sistema de tipos de entrada y navegacion real

Objetivo: pasar del vault simple a una base mejor organizada.

Primera expansion razonable:

- cuentas
- notas seguras
- tarjetas
- documentos o adjuntos solo si la arquitectura ya lo tolera

Trabajo concreto:

- categorias visibles en sidebar
- contador por categoria
- filtros reales
- recientes
- empty states por contexto
- detalle contextual por tipo de item

Importante:

No meter todos los tipos a la vez si eso rompe el avance.

Se puede cerrar primero:

- cuentas
- notas
- tarjetas

y dejar documentos para una etapa posterior si hace falta.

Criterio de salida:

"La informacion ya no vive como una lista plana unica; existe una navegacion mas rica y coherente."

## Etapa 5 - Busqueda, detalle y flujo diario pro

Objetivo: mejorar el uso diario hasta que la app se sienta realmente madura.

Trabajo concreto:

- busqueda mas rapida y clara
- seleccion persistente
- detalle lateral o central bien resuelto
- acciones visibles sin ruido
- mejor empty state
- mejores estados de hover, focus y seleccion
- accesos rapidos de teclado utiles
- feedback visual claro al copiar o guardar

Criterio de salida:

"Usar `v2` todos los dias ya se siente agradable y serio, no solo funcional."

## Etapa 6 - Features nuevos, uno por uno

Objetivo: crecer sin volver a desordenar la app.

Regla absoluta:

Cada feature nuevo entra como mini-proyecto con:

- alcance definido
- criterio de salida
- riesgos de seguridad
- tests
- cierre antes de pasar al siguiente

Posibles candidatos para esta etapa:

- favoritos
- tags
- auditoria de passwords debiles o repetidas
- historial de modificacion por item
- passkeys si algun dia entran de verdad
- import/export mas serio
- adjuntos

No decidir ahora el orden final de todos.

Se decidiran uno a uno cuando la base ya exista.

## Etapa 7 - Revaluacion de storage y nube

Objetivo: decidir con datos reales, no por ansiedad arquitectonica.

Preguntas que habilitan esta etapa:

- el vault actual ya se quedo corto de verdad?
- necesitamos consultas mas ricas de las que el modelo actual tolera?
- necesitamos sync real?
- necesitamos metadatos o volumen que justifiquen DB?

Solo si la respuesta es claramente si, evaluar:

- SQLite local
- indices locales
- metadatos separados del blob principal
- arquitectura de sync posterior

Importante:

Cloud y SQLite no son lo mismo.

Se puede tener:

- vault local sin DB
- vault local con DB
- sync con backend remoto

Cada una es una decision distinta.

Criterio de salida:

"La decision de storage deja de ser especulativa y pasa a estar justificada por necesidades reales de `v2`."

## Reglas de ejecucion para no perdernos

### Regla 1

No mezclar cierre de `v1` con construccion de `v2`.

### Regla 2

No agregar features nuevos mientras la nueva shell todavia no soporte bien lo que ya existe.

### Regla 3

No cambiar storage por intuicion o moda.

### Regla 4

No abrir cinco frentes en paralelo dentro de `v2`.

### Regla 5

Cada salto de complejidad debe venir despues de un piso estable.

### Regla 6

Si una decision de UX empeora claridad o seguridad, gana seguridad.

## Definicion de exito para `Instanashelock 2.0`

`Instanashelock 2.0` sera un exito si logra esto:

- se siente como una app claramente superior en UX a `v1`
- mantiene o mejora las garantias reales de seguridad local
- reutiliza inteligentemente el core ya confiable
- puede crecer por capas sin obligar a otro rework total enseguida
- deja de verse como un vault simple y pasa a sentirse como una plataforma local seria

## Nota final de criterio

El objetivo de este roadmap no es prometer todo ahora.

Es evitar que el entusiasmo por el rediseño nos haga perder el orden.

Primero se cierra `v1`.

Despues se arranca `v2` con una base clara:

- nueva UX
- mismo criterio de seguridad
- sin humo
- feature por feature
- cimiento por cimiento
