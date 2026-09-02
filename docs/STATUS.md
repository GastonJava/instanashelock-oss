# Instanashelock Manager — Estado historico pre-OSS y roadmap

Este documento conserva un corte tecnico del desarrollo privado previo al
inicio del repositorio OSS. Las cifras y estados fechados son evidencia
historica local, no afirmaciones sobre una release publica.

## Resumen de lo que tenemos

### Arquitectura criptográfica
- **VMK (Vault Master Key)**: clave aleatoria de 256 bits que cifra los datos
- **AES-256-GCM** con AAD (header autenticado)
- **Argon2id** como KDF principal (memory-hard, resistente a GPU/ASIC)
- **PBKDF2-HMAC-SHA256** soportado para vaults legacy
- VMK wrapeado separadamente por password-derived key y recovery-derived key
- Cambio de password sin re-encriptar todo el vault (solo re-wrap del VMK)

### Vault format v3
- Header binario versionado con magic bytes, KDF params, salt, wrapped VMK
- Header autenticado como AAD en AES-GCM
- Migración transparente v1 → v3 y v2 → v3
- Campo `has_recovery` que gobierna si hay material de recovery en el header
- Guardado atómico (tmp + fsync + replace + fsync dir) con backup `.bak`
- Permisos 0o600 en POSIX para vault y backup

### Recovery codes
- 10 grupos de 4 caracteres, charset base-31 sin ambigüedades (sin 0/O/1/I/L)
- 160 bits de entropía (más fuerte que cualquier password humana)
- Se muestran una sola vez al crear vault o al regenerar
- Se invalidan automáticamente después de usarlos (rotación forzada)
- Smart paste: pegar el código completo en cualquier casilla los distribuye
- 4 caracteres máximo por casilla + auto-advance

### Modos de vault
- **Modo estricto**: sin recovery, sin material residual en header
- **Modo recuperación**: con emergency recovery codes
- Selección al crear vault con radio buttons y texto contextual
- Upgrade de estricto a recuperación desde el sidebar ("Activar Recovery")
- Regeneración de codes desde el sidebar ("Regenerar Recovery")

### Máquina de estados del unlock
- **State A**: init → detecta si hay vault o no
- **State B**: crear vault (modo estricto / recuperación)
- **State C**: unlock (password input + rate limiting exponencial)
- **State D**: vault desbloqueado
- **State E**: strict lockout (3+ fallos → reset destructivo)
- **State F**: recovery disponible (3+ fallos → link de recovery)
- **State G**: vault corrupto/inválido (backup restore + reset)
- **State H**: recovery agotada (3+ fallos de recovery → link desaparece → reset)

### Reset destructivo
- Doble confirmación: primer diálogo yes/no + segundo con typed "ELIMINAR"
- Borra vault + backup
- Vuelve a pantalla de crear vault

### Seguridad operacional
- Auto-lock por inactividad
- Clipboard inteligente: solo borra lo que la app copió, auto-clear a 30s
- Recovery codes clipboard auto-clear a 60s
- Rate limiting exponencial en password y recovery (2s → 30s cap)
- Memory wipe best-effort (ctypes.memset) al bloquear/cerrar
- Sin password hints en ningún lado

### UI / UX
- Tema dark minimalista
- Vista de password separada de editar (double-click = ver, botón = editar)
- Barra de fortaleza de password (entropía visual)
- Generador de passwords (caracteres + passphrases)
- Búsqueda en lista de entries
- Copiar, ver con auto-close a 20s

### Proyecto
- Arquitectura modular: `crypto.py`, `storage.py`, `header.py`, `recovery.py`, `security.py`, `ui/`
- 47 tests unitarios cubriendo crypto, header, recovery, VMK, strict mode, backup, rate limiter
- venv con requirements separados (base, dev, build)
- Pipeline de release: Nuitka + Inno Setup + template de Authenticode listo; firma/publicacion diferidas por ahora

---

## Decisiones de diseño tomadas

- **Sin base de datos**: vault file único + backup es suficiente para app local single-user
- **JSON cifrado internamente**: se serializa a JSON antes de cifrar, pero el producto lo trata como vault binario versionado
- **Recovery codes no se persisten en plaintext**: se muestran una vez, se deriva key, se wrappea VMK, nunca se guardan
- **El .bak es material igual de sensible**: mismo cifrado, mismos permisos
- **Password input sigue accesible después de agotar recovery**: el usuario podría recordar su password
- **No password hints**: nunca, en ningún flujo, ni en config ni en header ni en UI

---

## Borrador: mejoras UX futuras

### 1. Contador de intentos visible
- "Intento 1 de 3" / "Intento 2 de 3" / "Ultimo intento antes de bloqueo"
- Aplicar tanto a password como a recovery
- Mensaje de advertencia más fuerte en el último intento

### 2. Feedback más claro en rate limiting
- Countdown visual en tiempo real: "Reintenta en 15s" con barra de progreso o timer
- Deshabilitar visualmente el input (grayed out) durante el cooldown

### 3. Indicador de modo del vault en unlock
- Mostrar discretamente si el vault es estricto o tiene recovery antes de fallar 3 veces
- Ej: un ícono pequeño o texto "Vault con recovery" / "Vault estricto" debajo del título

### 4. Confirmación visual al copiar recovery codes
- Feedback "Copiado" junto al botón de copiar en el diálogo de recovery codes
- Timer visual "Clipboard se limpia en 58s... 57s..."

### 5. Countdown visual también al copiar passwords normales
- Cuando se copia una password desde una entry, mostrar un timer decreciente real hasta `0`
- Evitar texto estático tipo "se elimina en 30" si no sigue bajando en vivo
- Mantener el feedback aunque el usuario no vuelva a interactuar con la card

### 6. Mejora del diálogo de recovery input
- Indicador visual de progreso al llenar casillas (checkmark por casilla completa)
- Validación en tiempo real del charset (marcar en rojo caracteres inválidos)

### 7. Escape hatch cuando el usuario no recuerda sus recovery codes
- Agregar una salida explicita tipo `Olvidaste tus recovery codes`
- Permitir volver al unlock sin friccion o explicar claramente que el reset requiere agotar intentos
- Evitar que el usuario sienta que debe inventar codigos solo para destrabar el flujo

### 8. Onboarding / primer uso
- Breve explicación al crear vault sobre qué es passphrase vs password
- Tooltip o expand sobre qué significa modo estricto vs recovery

### 9. Export de recovery codes
- Opción de generar PDF para imprimir (sin guardar en disco)
- O "Copiar como texto formateado" para pegar en papel

### 10. Historial de entries (stretch)
- Guardar la fecha de última modificación por entry
- Indicador "password vieja" si tiene más de X días sin cambiar

### 11. Pulido UX del flujo `Opciones avanzadas`
- Funcionalmente el flujo `Desinstalar app` / `Destruir vault y datos` ya quedó validado
- El modal actual se percibe tosco visualmente y necesita pasada de frontend dedicada
- Ajustes a recordar:
  - el texto del botón `Cerrar` puede quedar cortado visualmente
  - la card de `Destruir vault y datos` y su CTA necesitan mejor espaciado y jerarquía
  - el layout general se siente pegado a una esquina / con distribución poco cuidada
  - los diálogos siguen viéndose como ventanas nativas altas y cuadradas; revisar si conviene estilizado más consistente con la app
  - revisar copy spacing, márgenes, altura del modal y balance visual antes de publicar
  - cuando toque frontend, tratar este flujo como pulido UX/UI, no como rediseño de seguridad

---

*Última actualización: 2026-03-28*
