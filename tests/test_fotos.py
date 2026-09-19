import io

import pytest
from PIL import Image

from backend.services.fotos import guardar_foto


def _imagen_bytes(formato: str, size=(1200, 800)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(200, 100, 50)).save(buf, formato)
    return buf.getvalue()


def test_guardar_foto_redimensiona_a_600px_de_lado_mayor(tmp_path):
    contenido = _imagen_bytes("JPEG", size=(1200, 800))

    ruta = guardar_foto(contenido, "image/jpeg", fotos_dir=str(tmp_path))

    with Image.open(ruta) as img:
        assert max(img.size) == 600
        assert img.format == "JPEG"


def test_guardar_foto_acepta_png_y_convierte_a_jpeg(tmp_path):
    contenido = _imagen_bytes("PNG", size=(400, 300))

    ruta = guardar_foto(contenido, "image/png", fotos_dir=str(tmp_path))

    assert ruta.endswith(".jpg")
    with Image.open(ruta) as img:
        assert img.format == "JPEG"


def test_guardar_foto_acepta_webp(tmp_path):
    contenido = _imagen_bytes("WEBP", size=(400, 300))

    ruta = guardar_foto(contenido, "image/webp", fotos_dir=str(tmp_path))

    with Image.open(ruta) as img:
        assert img.format == "JPEG"


def test_guardar_foto_rechaza_tipo_no_soportado(tmp_path):
    with pytest.raises(ValueError):
        guardar_foto(b"no es una imagen real", "application/pdf", fotos_dir=str(tmp_path))


def test_guardar_foto_usa_nombre_aleatorio_y_no_colisiona(tmp_path):
    contenido = _imagen_bytes("JPEG")

    ruta1 = guardar_foto(contenido, "image/jpeg", fotos_dir=str(tmp_path))
    ruta2 = guardar_foto(contenido, "image/jpeg", fotos_dir=str(tmp_path))

    assert ruta1 != ruta2


def test_guardar_foto_quita_exif_aplicando_antes_la_rotacion(tmp_path):
    # Imagen con orientación EXIF=6 (rotar 90° a la derecha): 1200x800 "físico"
    # debe guardarse como si fuera 800x1200 tras aplicar la rotación.
    buf = io.BytesIO()
    img = Image.new("RGB", (1200, 800), color=(10, 20, 30))
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation tag
    img.save(buf, "JPEG", exif=exif)
    contenido = buf.getvalue()

    ruta = guardar_foto(contenido, "image/jpeg", fotos_dir=str(tmp_path))

    with Image.open(ruta) as resultado:
        assert resultado.getexif().get(0x0112) is None  # sin EXIF
        assert resultado.size[1] > resultado.size[0]  # se aplicó la rotación: ahora es más alta que ancha
