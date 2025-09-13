# /src/network/security.py
import hashlib
import hmac
import secrets
from typing import Dict, Tuple

# ===================== Utilidades Criptográficas (SHA256, HKDF, PRF) =====================

def H(x: bytes) -> bytes:
    """Función de hash SHA-256."""
    return hashlib.sha256(x).digest()

def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """Paso 'extract' de HKDF usando HMAC-SHA256."""
    return hmac.new(salt, ikm, hashlib.sha256).digest()

def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """Paso 'expand' de HKDF usando HMAC-SHA256."""
    out, T = b"", b""
    i = 1
    while len(out) < length:
        T = hmac.new(prk, T + info + bytes([i]), hashlib.sha256).digest()
        out += T
        i += 1
    return out[:length]

def prf_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Genera un keystream pseudoaleatorio usando HMAC-SHA256 (simula un cifrador de flujo)."""
    out = bytearray()
    ctr = 0
    while len(out) < length:
        block = hmac.new(key, nonce + ctr.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        ctr += 1
    return bytes(out[:length])

def xor_bytes(a: bytes, b: bytes) -> bytes:
    """Realiza una operación XOR byte a byte entre dos cadenas de bytes."""
    return bytes(x ^ y for x, y in zip(a, b))

def hmac256(key: bytes, *parts: bytes) -> bytes:
    """Calcula un HMAC-SHA256 sobre una o más partes de un mensaje."""
    h = hmac.new(key, b"", hashlib.sha256)
    for p in parts:
        h.update(p)
    return h.digest()

# ===================== Utilidades de Conversión (Integer <-> Bytes) =======================

def i2b(n: int) -> bytes:
    """Convierte un entero a su representación en bytes (big-endian)."""
    l = (n.bit_length() + 7) // 8
    return n.to_bytes(l or 1, "big")

def b2i(b: bytes) -> int:
    """Convierte una cadena de bytes (big-endian) a un entero."""
    return int.from_bytes(b, "big")

# ===================== “RSA toy” para Firmas (Solo para simulación) =======================

# Clave pública y privada del servidor (fija para la demo)
RSA_N = int("C65F3F1B9B97E19B", 16)
RSA_E = 65537
RSA_D = 0x12345  # Valor de juguete, no corresponde a N y E reales

def rsa_sign_toy(msg_hash: bytes) -> int:
    """Firma un hash simulando RSA (NO SEGURO)."""
    h_int = b2i(msg_hash)
    return pow(h_int, RSA_D, RSA_N)

def rsa_verify(n: int, e: int, msg_hash: bytes, sig: int) -> bool:
    """Verifica una firma RSA simulada."""
    v = pow(sig, e, n)
    return i2b(v).endswith(msg_hash)

# ===================== Diffie-Hellman (Parámetros fijos para demo) ====================

DH_P = 0xFFFFFFFEFFFFFC2F  # Primo de secp256k1
DH_G = 5

def dh_generate_private_key() -> int:
    """Genera una clave privada de Diffie-Hellman."""
    return secrets.randbits(190) | 1

def dh_generate_public_key(private_key: int) -> int:
    """Calcula la clave pública de Diffie-Hellman."""
    return pow(DH_G, private_key, DH_P)

def dh_calculate_shared_secret(their_public_key: int, my_private_key: int) -> int:
    """Calcula el secreto compartido de Diffie-Hellman."""
    return pow(their_public_key, my_private_key, DH_P)

# ===================== Clase Principal de Sesión Segura ==============================

class SecureSession:
    """
    Gestiona el estado y las operaciones de una sesión TLS simulada.
    """
    def __init__(self):
        self.state = "START"
        self.keys: Dict[str, bytes] = {} # Almacenará key_enc, key_mac, nonce, prk
        self.seq_send = 0
        self.seq_recv = 0 # Se necesitará para verificar la secuencia de recepción

    def derive_keys(self, shared_secret: int, server_nonce: bytes, client_nonce: bytes = None):
        """
        Deriva las claves de cifrado y MAC a partir del secreto compartido.
        El nonce del cliente es opcional para el lado del servidor al inicio.
        """
        # La "sal" para el extract inicial puede ser el nonce del servidor o una combinación
        salt = server_nonce
        prk = hkdf_extract(salt, i2b(shared_secret))
        
        # El "info" para el expand puede incluir más datos del transcript si se desea
        key_block = hkdf_expand(prk, b"key-schedule", 32 + 32 + 12) # key_enc, key_mac, nonce_base
        
        self.keys = {
            "key_enc": key_block[:32],
            "key_mac": key_block[32:64],
            "nonce_base": key_block[64:76],
            "prk": prk
        }
        self.seq_send = 0
        self.seq_recv = 0
        self.state = "ESTABLISHED"
        print("[Security] ✅ Claves de sesión derivadas y listas para usar.")

    def encrypt(self, plaintext: bytes) -> Dict:
        """
        Cifra un payload y le añade un MAC para protegerlo. (Antes 'protect_record')
        """
        if not self.keys:
            raise RuntimeError("La sesión segura no ha sido establecida, no se puede cifrar.")
        
        seq_header = self.seq_send.to_bytes(8, "big")
        self.seq_send += 1
        
        # Keystream derivado del nonce base y el contador de secuencia
        keystream = prf_keystream(self.keys["key_enc"], self.keys["nonce_base"] + seq_header, len(plaintext))
        ciphertext = xor_bytes(plaintext, keystream)
        
        # MAC calculado sobre el header (seq) y el texto cifrado
        tag = hmac256(self.keys["key_mac"], seq_header, ciphertext)
        
        return {
            "seq": self.seq_send - 1,
            "ct": ciphertext.hex(),
            "tag": tag.hex()
        }

    def decrypt(self, record: Dict) -> bytes:
        """
        Verifica el MAC y descifra un payload recibido. (Antes 'unprotect_record')
        """
        if not self.keys:
            raise RuntimeError("La sesión segura no ha sido establecida, no se puede descifrar.")
        
        seq = record["seq"]
        ciphertext = bytes.fromhex(record["ct"])
        received_tag = bytes.fromhex(record["tag"])
        
        seq_header = seq.to_bytes(8, "big")
        
        # Recalcular el MAC y verificar la integridad
        expected_tag = hmac256(self.keys["key_mac"], seq_header, ciphertext)
        if not hmac.compare_digest(expected_tag, received_tag):
            raise ValueError("Error de integridad: El MAC no es válido.")
        
        # (Opcional) Verificación de replay attacks
        # if seq < self.seq_recv:
        #     raise ValueError("Error de secuencia: Posible ataque de repetición.")
        # self.seq_recv = seq + 1

        # Descifrar el payload
        keystream = prf_keystream(self.keys["key_enc"], self.keys["nonce_base"] + seq_header, len(ciphertext))
        plaintext = xor_bytes(ciphertext, keystream)
        
        return plaintext