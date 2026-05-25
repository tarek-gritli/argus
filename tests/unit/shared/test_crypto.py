from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

KEY = Fernet.generate_key().decode()


def test_encrypt_decrypt_round_trip():
    from shared.crypto import decrypt, encrypt

    with patch("shared.crypto._get_key", return_value=KEY):
        assert decrypt(encrypt("my_secret")) == "my_secret"


def test_encrypt_produces_different_ciphertext_each_time():
    from shared.crypto import encrypt

    with patch("shared.crypto._get_key", return_value=KEY):
        assert encrypt("same") != encrypt("same")


def test_decrypt_wrong_key_raises():
    from shared.crypto import decrypt, encrypt

    other_key = Fernet.generate_key().decode()
    with patch("shared.crypto._get_key", return_value=KEY):
        ciphertext = encrypt("secret")
    with patch("shared.crypto._get_key", return_value=other_key):
        with pytest.raises(Exception):
            decrypt(ciphertext)


def test_encrypt_empty_string():
    from shared.crypto import decrypt, encrypt

    with patch("shared.crypto._get_key", return_value=KEY):
        assert decrypt(encrypt("")) == ""
