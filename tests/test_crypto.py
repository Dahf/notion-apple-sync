from app.crypto import decrypt, encrypt


def test_roundtrip():
    enc = encrypt("hello world")
    assert isinstance(enc, bytes)
    assert b"hello" not in enc
    assert decrypt(enc) == "hello world"


def test_roundtrip_unicode():
    s = "Uni-Kalender 📅 äöü"
    assert decrypt(encrypt(s)) == s
