import pytest
from pydantic import ValidationError

from app.models import MensajeCreate, UsuarioCreate


def test_usuario_nombre_se_normaliza():
    usuario = UsuarioCreate(nombre="  Cris  ")

    assert usuario.nombre == "Cris"


@pytest.mark.parametrize("nombre", ["", " ", "a"])
def test_usuario_nombre_rechaza_valores_cortos(nombre):
    with pytest.raises(ValidationError):
        UsuarioCreate(nombre=nombre)


def test_mensaje_contenido_se_normaliza():
    mensaje = MensajeCreate(
        emisor_id="u1",
        receptor_id="u2",
        contenido="  hola  ",
    )

    assert mensaje.contenido == "hola"


@pytest.mark.parametrize("contenido", ["", "   "])
def test_mensaje_rechaza_contenido_vacio(contenido):
    with pytest.raises(ValidationError):
        MensajeCreate(emisor_id="u1", receptor_id="u2", contenido=contenido)
