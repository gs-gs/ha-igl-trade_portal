import base64

from trade_portal.documents.services.encryption import AESCipher


def test_aes_cipher():
    """
    This code tests more the fact that our cipher class is able to extract the same text it's own output
    and doesn't guarantee that this is correct AES
    """
    KEY = "04E3C669A730B3A9EAA0F5107D253248486948DD92D1E2F8DDA2BDD1F7559CFB"
    CLEARTEXT = '{"test":"cleartext"}'

    cipher = AESCipher(KEY)
    iv_base64, tag_base64, ciphertext = cipher.encrypt_with_params_separate(CLEARTEXT)

    assert iv_base64 and tag_base64 and ciphertext

    cipher = AESCipher(KEY)  # re-init the cipher to avoid side effects
    decrypted_text_b64 = cipher.decrypt(iv_base64, tag_base64, ciphertext)

    assert base64.b64decode(decrypted_text_b64).decode("utf-8") == CLEARTEXT
