from .eth_personal_sign import EthPersonalSign, defunct_hash_message

class Wallet:
    def __init__(self, private_key, public_key):
        self._account = EthPersonalSign(private_key)
        self._public_key = public_key

    def sign_hash(self, text=None, hexstr=None):
        msg_hash = defunct_hash_message(hexstr=hexstr, text=text)
        signature_dict = self._account.signHash(msg_hash)
        signature = signature_dict["signature"].hex()
        return signature

    @property
    def address(self):
        return self._public_key