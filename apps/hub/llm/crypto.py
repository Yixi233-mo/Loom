"""本地密钥加密（标准库）。

算法：scrypt 派生密钥 + SHA256-CTR 流密码 + HMAC-SHA256 认证标签（encrypt-then-MAC）。
用于本机 API Key 落盘加密，不依赖第三方库。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets


class CryptoError(Exception):
    pass


def _derive_key(master: bytes, salt: bytes) -> bytes:
    return hashlib.scrypt(master, salt=salt, n=2**14, r=8, p=1, dklen=32)


def _keystream_xor(key: bytes, nonce: bytes, data: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < len(data):
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(data, bytes(out[: len(data)])))


def encrypt(plaintext: str, master_key: str) -> str:
    """加密字符串，返回 base64(salt|nonce|ciphertext|mac)。"""
    if not master_key:
        raise CryptoError("master_key 为空")
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    key = _derive_key(master_key.encode("utf-8"), salt)
    ct = _keystream_xor(key, nonce, plaintext.encode("utf-8"))
    mac = hmac.new(key, salt + nonce + ct, hashlib.sha256).digest()
    raw = salt + nonce + ct + mac
    import base64

    return base64.urlsafe_b64encode(raw).decode("ascii")


def decrypt(token: str, master_key: str) -> str:
    """解密 encrypt() 的输出。"""
    import base64

    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception as e:  # noqa: BLE001
        raise CryptoError(f"密文格式错误: {e}") from e
    if len(raw) < 16 + 16 + 32:
        raise CryptoError("密文过短")
    salt, nonce = raw[:16], raw[16:32]
    mac, ct = raw[-32:], raw[32:-32]
    key = _derive_key(master_key.encode("utf-8"), salt)
    expect = hmac.new(key, salt + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expect):
        raise CryptoError("MAC 校验失败")
    pt = _keystream_xor(key, nonce, ct)
    return pt.decode("utf-8")


def mask_secret(value: str) -> str:
    """展示用脱敏：sk-abc…xyz → sk-abc***xyz"""
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-3:]
