# Ver PictoHistorias en el móvil (acceso remoto)

Guía para dejar PictoHistorias corriendo en un equipo pequeño (una Raspberry Pi, un mini PC, un portátil viejo) y abrirla desde los móviles y tablets de la familia, desde casa o desde la calle. Se asume que la app ya funciona en local: sigue antes el [README](../README.md#puesta-en-marcha).

Hay dos formas. **Para una familia o un grupo pequeño, Tailscale es lo más sencillo.**

| | [Tailscale](#con-tailscale-recomendado) | [Cloudflare Tunnel + Access](#con-cloudflare-tunnel--access) |
|---|---|---|
| Hay que instalar una app en cada móvil | Sí | No (entran por el navegador, con código por correo) |
| Necesita dominio propio | No | Sí |
| Complejidad | Baja | Media |
| Sabe quién escribe cada historia | No | Sí (`USUARIOS_MAPA`) |

> **No se ha probado esta guía en una Raspberry Pi.** Los comandos de Tailscale están contrastados con su documentación y con la ayuda de `tailscale` 1.102; el resto (nginx, systemd, Cloudflare) es lo que usa el proyecto en mi servidor x86. Si algo falla, abre una issue.

## Antes de empezar: seguridad

PictoHistorias **no tiene usuarios ni contraseñas**: quien llegue a la web puede ver las historias y las fotos, y gastar tus créditos de Anthropic y OpenAI generando historias. Por eso:

- ✅ Ponle delante **Tailscale** o **Cloudflare Access**: solo entran quienes tú autorices.
- ❌ **No uses `tailscale funnel`** ni abras el puerto en el router: publica el servicio a todo internet, y aquí no hay nada que lo proteja.
- 💸 Pon un **límite de gasto** en las consolas de Anthropic y OpenAI. Cada persona con acceso gasta de tu saldo.

---

## Con Tailscale (recomendado)

[Tailscale](https://tailscale.com) crea una red privada entre tus dispositivos. El servidor y los móviles se ven como si estuvieran en la misma wifi, y desde fuera de esa red no se ve nada.

```
móvil / tablet ──(red privada Tailscale, cifrada)──► servidor ──► nginx :5252 ──► PictoHistorias
   con la app Tailscale                                (Raspberry, mini PC…)
```

**Qué necesitas:** una cuenta de Tailscale (gratuita para uso personal; a fecha de esta guía, hasta 6 usuarios según [su página de precios](https://tailscale.com/pricing)) y el servidor con acceso por terminal y `sudo`.

### Paso 1. Instalar Tailscale en el servidor

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

`tailscale up` imprime un enlace: ábrelo en cualquier navegador e inicia sesión con tu cuenta. Comprueba que está conectado:

```bash
tailscale status
tailscale ip -4        # la IP privada del servidor, del tipo 100.x.y.z
```

Ponle un nombre corto y neutro (será su dirección): `sudo tailscale set --hostname=pictohistorias`.

**Desactiva la caducidad de la clave (importante).** Por defecto, la clave de cada dispositivo **caduca a los 180 días** y el servidor se desconectaría solo. Como va a estar siempre encendido, desactívala: en la [consola de administración](https://login.tailscale.com/admin/machines) → tu servidor → menú `⋯` → **Disable key expiry**.

### Paso 2. Publicar la app en la red privada

#### Opción A (la más simple): nginx escucha en la IP de Tailscale

Es lo que ya hace el proyecto. Con Tailscale activo:

```bash
make deploy
```

Instala la config de nginx sustituyendo `TAILSCALE_IP` por la IP privada del servidor. (Para que la app arranque sola al encender el equipo, instala también el servicio con `make install-services`; ajusta antes el usuario y la ruta en `pictohistorias-backend.service`, como indica el README.) Ya puedes abrir, desde un dispositivo con Tailscale:

- `http://pictohistorias:5252` (el nombre funciona si MagicDNS está activado, que lo está por defecto en las redes nuevas), o
- `http://100.x.y.z:5252` con la IP que te dio `tailscale ip -4`.

Que el navegador diga «no seguro» es normal: es HTTP, pero por dentro de Tailscale el tráfico va cifrado de extremo a extremo. La app no necesita HTTPS para funcionar.

**Si tras reiniciar el servidor la web no responde:** nginx puede arrancar antes de que Tailscale tenga IP y fallar. Se arregla haciendo que nginx se reintente solo:

```bash
sudo systemctl edit nginx
```

y pega esto en el editor que se abre:

```ini
[Service]
Restart=on-failure
RestartSec=5
```

#### Opción B: HTTPS con nombre bonito (`tailscale serve`)

Da una dirección `https://pictohistorias.<tu-red>.ts.net`, sin puerto y sin aviso de «no seguro». Se añade **encima de la opción A**: `tailscale serve` reenvía al nginx local (`127.0.0.1:5252`), así que primero ejecuta `make deploy`.

1. En la consola de administración → [DNS](https://login.tailscale.com/admin/dns): activa **MagicDNS** y **Enable HTTPS**.
2. En el servidor:

   ```bash
   sudo tailscale serve --bg 5252
   tailscale serve status        # ver qué está publicado
   ```

3. Para quitarlo: `sudo tailscale serve reset`.

⚠️ Al activar HTTPS, Tailscale registra el **nombre de tu servidor y el de tu red en un registro público** de certificados ([documentación](https://tailscale.com/kb/1153/enabling-https)). Por eso conviene el nombre neutro del paso 1, y no algo como `casa-de-los-garcia`. Sigue siendo privado: el registro no expone el servicio, solo esos nombres.

Ambas direcciones siguen funcionando a la vez: `serve` usa el puerto 443 y nginx el 5252.

### Paso 3. Conectar los móviles y tablets

En cada dispositivo desde el que se vaya a usar (el del niño incluido):

1. Instala la app **Tailscale** (App Store / Google Play) e inicia sesión con una cuenta de tu red.
2. Deja la VPN de Tailscale **activada**. Si está apagada, la web no carga: es lo primero que hay que mirar cuando «no va».
3. Abre la dirección del paso 2 y añádela a la pantalla de inicio para tener un acceso directo.

#### Dar acceso a otras personas (el otro progenitor, abuelos, terapeuta)

Hay dos formas. Los menús de Tailscale cambian; ante la duda, sigue su documentación.

| Forma | Cuándo | Cómo |
|---|---|---|
| **Invitar a tu red** | Familia cercana | Consola → *Users* → *Invite*. Ojo: por defecto, quien está en tu red puede llegar a **todos** tus dispositivos, no solo al servidor |
| **Compartir solo el servidor** | Gente de fuera (terapeuta, otra familia) | Consola → *Machines* → `⋯` del servidor → *Share*. La otra persona, con su propia cuenta de Tailscale, acepta la invitación y solo llega a ese servidor. Docs: [Sharing](https://tailscale.com/kb/1084/sharing) |

Quien reciba el servidor compartido lo abre con su nombre completo: `http://pictohistorias.<tu-red>.ts.net:5252` (opción A) o el `https://…` de la opción B. No he probado el modo compartido con esta app.

### Limitaciones con Tailscale

- **No sabe quién es cada persona.** Todas las historias se redactan como si las escribiera «mamá» (en el prompt, «mi coche» pasa a ser «el coche de mamá»). `USUARIOS_MAPA` solo funciona con Cloudflare Access (ver más abajo).
- **El prompt está escrito para un caso concreto:** un niño de 6 años, con autismo y no verbal ([`backend/prompts/historia.md`](../backend/prompts/historia.md)). Si tu caso es distinto, edítalo (vale para cualquier vía de acceso).

### Problemas frecuentes con Tailscale

| Síntoma | Qué mirar |
|---|---|
| No carga en el móvil | ¿Está activada la VPN de Tailscale en el móvil? ¿Sale el servidor en `tailscale status` como conectado? |
| Funcionaba y dejó de funcionar a los ~6 meses | Caducó la clave del servidor: paso 1, «Desactiva la caducidad» |
| Tras un reinicio, nada | Ajuste de `Restart=on-failure` de nginx (opción A). Comprueba con `systemctl status nginx pictohistorias-backend` |
| `make deploy` da error con `tailscale ip` | Tailscale no está conectado: `sudo tailscale up` |
| El nombre `pictohistorias` no resuelve | Usa la IP `100.x.y.z`, o activa MagicDNS en la consola |

---

## Con Cloudflare Tunnel + Access

Sirve si quieres que la gente entre sin instalar nada (con un código por correo) y quieres saber quién escribe cada historia. Necesita un dominio propio.

1. Crea un túnel y una aplicación de Access en Cloudflare, con el túnel apuntando a `http://127.0.0.1:5252`.
2. Rellena en `.env` las cuatro variables `CLOUDFLARE_TUNNEL_TOKEN`, `CLOUDFLARE_TEAM`, `CLOUDFLARE_ACCESS_AUD` y `USUARIOS_MAPA`. `USUARIOS_MAPA` tiene la forma `email:etiqueta,email:etiqueta` y sirve para saber quién escribe cada historia (esa etiqueta pasa al prompt). `CLOUDFLARE_ACCESS_AUD` puedes dejarlo vacío al principio: el backend registra en el log el `aud` de los JWT válidos que reciba.
3. `make install-cloudflared` (con `sudo`). El unit que crea `cloudflared` contiene el token, así que ejecuta después `sudo chmod 600 /etc/systemd/system/cloudflared.service`.

**Ojo en Raspberry Pi (ARM):** el `Makefile` descarga el paquete `amd64`, que no funciona en ARM. Cambia `cloudflared-linux-amd64.deb` por `cloudflared-linux-arm64.deb` (existe; comprobado) o instálalo a mano.

El backend solo verifica el JWT de Access cuando la petición trae `Cf-Connecting-Ip`, es decir, cuando llega por el túnel. Ojo: esa verificación cubre `/api/`; las imágenes y el frontend los sirve nginx directamente, así que ahí la protección es la política de Access en Cloudflare.
