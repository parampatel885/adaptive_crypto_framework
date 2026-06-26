import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

STATIC_KEY_32 = b'\x01' * 32
STATIC_KEY_16 = b'\x01' * 16
STATIC_NONCE_16 = b'\x00' * 16

def execute_standard_aes(data_string):
    start_time = time.perf_counter()
    raw_bytes = data_string.encode('utf-8')
    cipher = Cipher(algorithms.AES(STATIC_KEY_16), modes.CTR(STATIC_NONCE_16))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(raw_bytes) + encryptor.finalize()
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return ciphertext, round(elapsed_ms, 4), round(elapsed_ms * 12.5, 4)

def execute_hybrid_ecc_aes(data_string):
    start_time = time.perf_counter()
    raw_bytes = data_string.encode('utf-8')
    private_key = ec.generate_private_key(ec.SECP256R1())
    peer_public_key = ec.generate_private_key(ec.SECP256R1()).public_key()
    shared_secret = private_key.exchange(ec.ECDH(), peer_public_key)
    derived_key = HKDF(algorithm=hashes.SHA256(), length=16, salt=None, info=b'adaptive-crypto',).derive(shared_secret)
    cipher = Cipher(algorithms.AES(derived_key), modes.CTR(STATIC_NONCE_16))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(raw_bytes) + encryptor.finalize()
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return ciphertext, round(elapsed_ms, 4), round(elapsed_ms * 38.2, 4)

def execute_lightweight_trivium(data_string):
    start_time = time.perf_counter()
    raw_bytes = data_string.encode('utf-8')
    cipher = Cipher(algorithms.ChaCha20(STATIC_KEY_32, STATIC_NONCE_16), mode=None)
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(raw_bytes) + encryptor.finalize()
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return ciphertext, round(elapsed_ms, 4), round(elapsed_ms * 3.1, 4)
