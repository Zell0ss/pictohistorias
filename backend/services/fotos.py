import secrets
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

TAMANO_MAX = 600
TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}


def guardar_foto(contenido: bytes, content_type: str, fotos_dir: str = "fotos") -> str:
    if content_type not in TIPOS_PERMITIDOS:
        raise ValueError(f"Tipo de imagen no soportado: {content_type}")

    Path(fotos_dir).mkdir(parents=True, exist_ok=True)
    nombre = f"{secrets.token_hex(16)}.jpg"
    destino = Path(fotos_dir) / nombre

    imagen = Image.open(BytesIO(contenido))
    imagen = ImageOps.exif_transpose(imagen)  # aplica la rotación EXIF antes de descartar los metadatos
    imagen = imagen.convert("RGB")
    imagen.thumbnail((TAMANO_MAX, TAMANO_MAX))
    imagen.save(destino, "JPEG", quality=85)  # Image.save() para JPEG no copia EXIF salvo que se pase explícitamente

    return str(destino)
