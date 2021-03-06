import base64

# TODO: replace to pyca/cryptography as Bandit advises (low)
from Crypto.Cipher import AES


class AESCipher:
    BS = 256 // 8

    def __init__(self, key):
        self.key = bytes.fromhex(key)

    # not used
    # def pad(self, s):
    #     return s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)

    # def unpad(self, s):
    #     return s[: -ord(s[len(s) - 1 :])]

    def encrypt_with_params_separate(self, raw):
        encoded = base64.b64encode(raw.encode("utf-8"))
        cipher = AES.new(self.key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(encoded)
        return (
            base64.b64encode(cipher.nonce).decode("utf-8"),
            base64.b64encode(tag).decode("utf-8"),
            base64.b64encode(ciphertext).decode("utf-8"),
        )

    def decrypt(self, iv, tag, ciphertext):
        iv = base64.b64decode(iv)
        tag = base64.b64decode(tag)
        ciphertext = base64.b64decode(ciphertext)
        cipher = AES.new(self.key, AES.MODE_GCM, iv)
        return cipher.decrypt_and_verify(ciphertext, tag)
