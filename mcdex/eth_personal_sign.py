# a simple version of eth_account

import codecs
from Crypto.Hash import (
    keccak,
)
import coincurve

CHAIN_ID_OFFSET = 35
V_OFFSET = 27

def keccak256(prehash: bytes) -> bytes:
    hasher = keccak.new(data=prehash, digest_bits=256)
    return hasher.digest()

class EthPersonalSign(object):
    def __init__(self, private_key):
        private_key_bytes = decode_hex(private_key)
        self._raw_key = private_key_bytes

    def signHash(self, msg_hash_bytes: bytes):
        if len(msg_hash_bytes) != 32:
            raise ValueError("The message hash must be exactly 32-bytes")
        key = self._raw_key

        signature_bytes = coincurve.PrivateKey(key).sign_recoverable(
            msg_hash_bytes,
            hasher=None,
        )
        if len(signature_bytes) != 65:
            raise ValueError("Unexpected signature format. Must be length 65 byte string")
        r = signature_bytes[0:32]
        s = signature_bytes[32:64]
        v = signature_bytes[64:65]

        v = ord(v)
        v = to_eth_v(v)
        v = bytes([v])

        eth_signature_bytes = r + s + v
        return {
            'messageHash': msg_hash_bytes,
            'signature': HexBytes(eth_signature_bytes)
        }

def to_bytes(primitive=None, hexstr: str = None, text: str = None) -> bytes:
    if isinstance(primitive, bytearray):
        return bytes(primitive)
    elif isinstance(primitive, bytes):
        return primitive
    elif hexstr is not None:
        if len(hexstr) % 2:
            # type check ignored here because casting an Optional arg to str is not possible
            hexstr = "0x0" + remove_0x_prefix(hexstr)  # type: ignore
        return decode_hex(hexstr)
    elif text is not None:
        return text.encode("utf-8")
    raise TypeError(
        "expected a bool, int, byte or bytearray in first arg, or keyword of hexstr or text"
    )

def to_eth_v(v_raw, chain_id=None):
    if chain_id is None:
        v = v_raw + V_OFFSET
    else:
        v = v_raw + CHAIN_ID_OFFSET + 2 * chain_id
    return v

def is_0x_prefixed(value) -> bool:
    return value.startswith("0x") or value.startswith("0X")

def remove_0x_prefix(value: str) -> str:
    if is_0x_prefixed(value):
        return value[2:]
    return value

def decode_hex(value: str) -> bytes:
    return codecs.decode(remove_0x_prefix(value), "hex")  # type: ignore

def signature_wrapper(message, version=b'E'):
    # watch here for updates to signature format: https://github.com/ethereum/EIPs/issues/191
    assert isinstance(message, bytes)
    if version == b'E':
        preamble = b'\x19Ethereum Signed Message:\n'
        size = str(len(message)).encode('utf-8')
        return preamble + size + message
    else:
        raise NotImplementedError("Only the 'Ethereum Signed Message' preamble is supported")

def defunct_hash_message(primitive=None, hexstr=None, text=None):
    message_bytes = to_bytes(primitive, hexstr=hexstr, text=text)
    wrapped = signature_wrapper(message_bytes)
    hashed = keccak256(wrapped)
    return hashed

class HexBytes(bytes):
    def __new__(cls, val: bytes):
        return super().__new__(cls, val)

    def hex(self):
        '''
        Just like :meth:`bytes.hex`, but prepends "0x"
        '''
        return '0x' + super().hex()

    def __repr__(self):
        return 'HexBytes(%r)' % self.hex()