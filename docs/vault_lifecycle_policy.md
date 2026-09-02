# Vault Lifecycle UX Decision

Decision final de UX y seguridad para separar claramente:

- desinstalar la app
- destruir el vault local
- mantener limpio el flujo principal de unlock

Este documento ya no es brainstorming. Define el comportamiento esperado, el copy exacto y las reglas de implementacion.

## Decision final

- `desinstalar app != destruir vault`
- desinstalar la app NO borra el vault por defecto
- destruir el vault debe existir como accion explicita y separada
- unlock debe seguir limpio, sin botones destructivos grandes

## Entry points

### Unlock con vault existente

La pantalla principal sigue enfocada en:

- ingresar password
- entrar al vault

Acceso secundario visible pero discreto:

- link: `Opciones avanzadas`

No se muestra en first-run sin vault.

### Dentro del vault desbloqueado

En la top bar se agrega una accion secundaria:

- boton: `Opciones`

No debe verse como CTA destructivo.

## Modal de acciones avanzadas

Titulo exacto:

- `Opciones avanzadas`

Texto introductorio exacto:

`Estas acciones no forman parte del uso normal del vault. Desinstalar la app y destruir el vault son cosas distintas.`

Aviso fijo dentro del modal:

`Desinstalar la app NO elimina tu vault ni tus datos cifrados.`

### Bloque 1

Titulo:

- `Desinstalar app`

Descripcion:

`Quita Instanashelock de este equipo. El vault local queda intacto.`

Boton normal si existe desinstalador local:

- `Abrir desinstalador`

Boton fallback si no existe desinstalador local:

- `Como desinstalar`

### Bloque 2

Titulo:

- `Destruir vault y datos`

Descripcion:

`Elimina el vault local, el backup local y el lock local de este dispositivo. Esta accion no se puede deshacer.`

Boton destructivo:

- `Destruir vault...`

Boton de cierre del modal:

- `Cerrar`

## Accion: Desinstalar app

### Confirmacion previa

Titulo exacto:

- `Abrir desinstalador`

Mensaje exacto:

`Se abrira el desinstalador de Instanashelock.`

`Desinstalar la app NO elimina tu vault ni tus datos cifrados.`

`Si continuas, esta ventana se cerrara.`

`Continuar?`

### Fallback sin desinstalador local

Titulo exacto:

- `Desinstalacion manual`

Mensaje exacto:

`Esta copia no expone un desinstalador local.`

`Si la instalaste, usa Configuracion > Aplicaciones de Windows.`

`Si es portable, elimina la carpeta de la app.`

`Desinstalar la app NO elimina tu vault ni tus datos cifrados.`

### Regla de comportamiento

- si el desinstalador local existe, se lanza y la app se cierra
- si no existe, solo se muestran instrucciones
- esta accion nunca pide master password
- esta accion nunca borra vault, backup ni lock por defecto

## Accion: Destruir vault y datos

### Confirmacion 1

Titulo exacto:

- `Destruir vault y datos`

Mensaje exacto:

`Esto eliminara permanentemente tu vault local y todas las passwords guardadas.`

`Se eliminara:`

- `El vault principal`
- `El backup local`
- `El lock local`

`Esta accion NO se puede deshacer.`

`Continuar?`

### Confirmacion 2

Se mantiene la confirmacion tipada con la palabra:

- `ELIMINAR`

Titulo exacto del segundo dialogo:

- `Confirmar eliminacion`

Titulo interno exacto:

- `ULTIMA CONFIRMACION`

Mensaje exacto:

`Vas a perder TODAS tus passwords.`

`Esta accion NO se puede deshacer.`

`Escribe ELIMINAR para confirmar:`

Boton final:

- `Destruir vault`

### Regla de comportamiento

- no requiere master password:
  - es una accion local destructiva, no una autenticacion remota
  - las confirmaciones existen para evitar errores, no para reemplazar el control del sistema operativo
- debe borrar:
  - `passwords.vault`
  - `passwords.vault.bak`
  - `passwords.vault.lock`
- si la accion parte desde una sesion desbloqueada:
  - limpiar clipboard
  - cancelar callbacks pendientes
  - hacer wipe best-effort de secretos en memoria
- despues del borrado:
  - desde unlock: volver a `Crear vault`
  - desde el vault desbloqueado: cerrar la sesion actual y volver al flujo de `Crear vault`

## Reglas de producto

- desinstalar y destruir vault son acciones distintas y deben seguir separadas
- el uninstall del sistema no borra secretos por defecto
- el usuario no debe depender de errores de password para destruir su vault
- el flujo principal de unlock no debe contaminarse con acciones destructivas prominentes
- si el usuario controla la cuenta local de Windows, siempre podria borrar archivos manualmente; la UI debe prevenir errores, no fingir identidad remota que no existe

## No-go

- no agregar dos botones destructivos grandes en la pantalla principal de unlock
- no pedir master password dentro del desinstalador
- no mezclar uninstall con wipe por defecto
- no depender solo del flujo de lockout para eliminar el vault

## Nota de implementacion actual

- el flujo funcional ya quedo validado localmente
- la deuda restante de este bloque es principalmente visual
- antes de release final conviene una pasada de frontend sobre:
  - espaciado y jerarquia del modal `Opciones avanzadas`
  - visibilidad completa de CTAs y labels
  - consistencia visual de los dialogos destructivos con el resto de la app
