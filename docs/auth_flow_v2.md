# Auth Flow V2

Documento de referencia para el flujo de autenticacion de `Instanashelock 2.0`.

No describe toda la app. Solo cubre los flujos de acceso al vault:

- unlock de vault existente
- forgot main password
- create vault / first run
- recovery, restore y reset local
- placeholder de `Windows Hello` para futuro quick unlock

## Objetivo

Definir un flujo de autenticacion visualmente fuerte, coherente con `security first` y compatible con la migracion de `v1` hacia `v2`.

La meta no es solo que se vea mejor que `v1`.

La meta es que el acceso al vault se sienta:

- mas claro
- mas profesional
- mas privado
- mas consistente con el producto

## Stack y criterio tecnico

El frontend de `v2` para este flujo se asume en:

- `PySide6`
- `Qt Quick / QML`

Razon:

- mantiene una arquitectura mas compacta para una app sensible
- evita introducir un sidecar Python separado solo para la logica del vault
- permite una UI moderna, animada y con bastante libertad visual sin salir del ecosistema local

## Principios de producto

- este flujo habla de `unlock`, no de `sign in`
- el producto sigue siendo un vault local, no una cuenta online
- no se promete biometria ni `Windows Hello` antes de tener backend real
- el copy nunca debe exagerar destruccion o perdida si existen recovery o restore
- las decisiones visuales no pueden degradar claridad ni seguridad

## Direccion visual

La estetica buscada es `gothic clean / gamer sobrio`, no cyberpunk exagerado.

Debe sentirse:

- oscura
- nitida
- privada
- un poco intensa
- pero aun legible y confiable para uso diario

Paleta provisional sugerida:

- `bgMain`: `#0D0D12`
- `bgPanel`: `#14141B`
- `bgField`: `#1A1A24`
- `textPrimary`: `#E0E0E0`
- `textMuted`: `#8B8B98`
- `accentPrimary`: `#B82467`
- `accentPrimaryAlt`: `#8A2BE2`
- `accentTech`: `#00E5FF`
- `danger`: `#C1121F`
- `dangerBg`: `#1A0505`

Estos colores son provisionales y pueden refinarse despues. El layout y la logica no deben depender de un branding final.

## Branding provisional

Mientras no exista logo final, se permite usar:

- isotipo temporal
- iconos SVG temporales
- tagline provisional o ningun tagline

Regla:

- el codigo debe permitir reemplazar assets de branding sin romper layout ni jerarquia visual

## UI & Layout Guidelines (QML)

- el layout principal debe construirse con `ColumnLayout`, `RowLayout`, `GridLayout` y `anchors`
- el posicionamiento debe ser relativo al contenedor y a los componentes vecinos
- `x` y `y` fijos solo se permiten en casos visuales puntuales y justificados
- los margenes y `spacing` se usan para respiracion visual, no para empujar bloques a posiciones artificiales
- queda descartado acomodar pantallas con offsets grandes o magic numbers tipo `margin-top: 250px`
- el contenedor central debe mantenerse proporcionado en laptops y monitores grandes sin romper el foco ni la legibilidad
- el resize razonable de ventana no debe desmontar la jerarquia del unlock

## Mapa de estados del flujo

### Estado 1: Unlock de vault existente

Caso normal cuando el usuario ya tiene un vault local.

Objetivo:

- ingresar `main password`
- abrir el vault

### Estado 2: Forgot main password

Pantalla secundaria para explicar caminos reales de recuperacion o reset local.

Objetivo:

- recovery codes si existen
- restore desde respaldo cifrado si existe
- reset local si el usuario decide destruir el vault de este dispositivo

### Estado 3: Create vault / first run

Pantalla de primer uso o despues de reset destructivo.

Objetivo:

- crear vault nuevo
- elegir `main password`
- decidir recovery

### Estado 4: Corrupt / restore path

Estado de error para vault local dañado o invalido.

Objetivo:

- intentar restore desde backup local o respaldo cifrado
- permitir reset local si no hay salida recuperable

### Estado 5: Future quick unlock

Reservado para desbloqueo rapido con `Windows Hello`.

Objetivo futuro:

- desbloqueo local mas comodo despues de setup previo
- nunca reemplazar el alta inicial del vault ni la capacidad de unlock por password

## Pantalla 1: Unlock de vault existente

Esta debe ser la primera pantalla a implementar en `v2`.

### Copy base

Titulo sugerido:

- `Unlock vault`

Texto de apoyo sugerido:

- `The vault is locked. Enter your main password.`

CTA principal:

- `Unlock`

Enlace secundario real:

- `Forgot your main password?`

Regla de copy:

- usar `main password` o `master password`, pero elegir uno y mantenerlo consistente
- evitar `Sign in` si no hay identidad online

### Estructura visual

- bloque central protagonista
- icono de vault o isotipo arriba o alineado con marca
- nombre `Instanashelock` con jerarquia clara
- password field
- boton principal `Unlock`
- enlaces secundarios debajo
- area superior secundaria opcional para icono de ayuda / ajustes si se decide incluirlos

### Comportamiento

- el campo password recibe foco automatico al abrir
- `Enter` dispara el mismo flujo que el boton `Unlock`
- si la password es incorrecta:
  - shake breve del campo
  - borde a color `danger`
  - mensaje claro sin filtrar informacion extra
- si el vault esta bloqueado temporalmente por rate limit:
  - input y CTA muestran estado bloqueado
  - feedback visible y no ambiguo
- si el unlock esta procesando:
  - deshabilitar doble submit
  - mostrar estado `loading`

### Reglas de UX

- no contaminar esta pantalla con CTAs destructivos prominentes
- el forgot password debe sentirse secundario pero visible
- si algun dia aparece `Windows Hello`, no debe competir visualmente con el CTA principal

## Pantalla 2: Forgot your main password

No debe ser una pantalla sensacionalista.

Debe explicar caminos reales.

### Lo que no debe hacer

- no afirmar automaticamente `all your data will be deleted`
- no ocultar que puede existir recovery
- no ocultar que puede existir restore desde respaldo cifrado

### Lo que si debe hacer

- explicar que sin `main password` el vault no se abre por fuerza bruta desde UI
- ofrecer recovery si existe
- ofrecer restore desde respaldo cifrado si el usuario tiene uno
- explicar el reset local como ultimo recurso

### Bloques esperados

Bloque 1:

- `Use recovery codes`
- visible solo si el vault tiene recovery o el sistema puede detectarlo

Bloque 2:

- `Restore encrypted backup`
- explica que el archivo de respaldo sigue requiriendo la password correcta

Bloque 3:

- `Create a new vault on this device`
- opcion destructiva local
- copy claro: destruye el vault local de este equipo, no finge borrar una cuenta remota que no existe

### Warning box

Se permite un bloque visual de alerta, pero su copy debe ser honesto.

Copy orientativo:

- `Without your main password, this local vault cannot be opened directly.`
- `If you still have recovery codes or an encrypted backup, use them before resetting this device.`

### CTA destructivo

Texto sugerido:

- `Create new vault on this device`

No usar por defecto:

- `Delete everything`
- `All your data will be deleted`

porque el escenario real puede incluir respaldo externo o migracion futura.

## Pantalla 3: Create vault / first run

Esta pantalla debe heredar la misma familia visual del unlock.

Objetivos:

- crear un vault nuevo
- confirmar password
- elegir modo recovery o estricto

Regla:

- aunque visualmente se vea moderna, la logica heredada de `v1` no debe empeorar

## Windows Hello - politica futura

`Windows Hello` queda contemplado, pero no forma parte del primer piso funcional de `v2`.

Decision:

- no se promete como parte del unlock inicial
- no debe verse activo si no existe backend real
- si aparece antes del backend, solo puede existir como placeholder no interactivo o directamente oculto

Interpretacion correcta de la feature:

- no es passkey web por defecto
- no reemplaza el alta inicial del vault
- es un posible `quick unlock` local despues de que el usuario ya desbloqueo el vault con su password y habilito explicitamente esa opcion

Regla de activacion futura:

- primero unlock tradicional por password
- luego opt-in dentro de la app
- luego quick unlock en relocks posteriores

Copy correcto si algun dia aparece:

- `Unlock with Windows Hello`

No usar:

- `Sign in with Windows Hello`

## Relacion con `v1`

En la primera etapa de `v2`, este flujo no inventa una logica nueva completa.

Adapta lo ya existente en `v1`:

- unlock por password
- recovery codes
- restore desde backup local
- restore desde respaldo cifrado portable
- reset local / create new vault

La UI cambia fuerte.

Las reglas de seguridad y comportamiento deben mantenerse o mejorar.

## Orden de implementacion recomendado

1. `Theme.qml` y tokens visuales base
2. componentes atomicos del flujo (`PasswordField`, `PrimaryButton`, `TextLink`, `BrandLockup`)
3. pantalla `Unlock` visual sin backend
4. conexion del unlock real al backend reutilizado de `v1`
5. estados de error, loading y bloqueo temporal
6. pantalla `Forgot your main password?`
7. create vault / first run
8. placeholders o extensiones futuras (`Windows Hello`)

## No objetivos de este documento

- definir toda la shell multipanel de `v2`
- cerrar branding final de la marca
- decidir todavia biometria real
- describir cada componente con pixeles exactos

## Criterio de salida de este bloque

Este documento queda suficientemente bueno si nos permite construir el flujo de autenticacion de `v2` sin rediscutir cada semana:

- que copy usamos
- que pantallas existen
- que promesas son validas
- como se acomoda el layout
- que parte es presente y que parte es futura
