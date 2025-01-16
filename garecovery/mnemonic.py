import wallycore as wally

from . import exceptions
from gaservices.utils import h2b

wordlist_ = wally.bip39_get_wordlist('en')
wordlist = [wally.bip39_get_word(wordlist_, i) for i in range(2048)]


def seed_from_mnemonic(mnemonic_or_hex_seed, passphrase):
    """Return seed, mnemonic given an input string

    mnemonic_or_hex_seed can either be:
    - A mnemonic
    - A hex seed, with an 'X' at the end, which needs to be stripped

    seed will always be returned, mnemonic may be None if a seed was passed
    """
    if mnemonic_or_hex_seed.endswith('X'):
        mnemonic = None
        if passphrase:
            raise exceptions.InvalidMnemonicOrPasswordError(
                'Passphrase is incompatible with explicit seed')
        seed = h2b(mnemonic_or_hex_seed[:-1])
    else:
        mnemonic = mnemonic_or_hex_seed
        seed = wally.bip39_mnemonic_to_seed512(mnemonic_or_hex_seed, passphrase)

    assert len(seed) == wally.BIP39_SEED_LEN_512
    return seed, mnemonic


def wallet_from_mnemonic(mnemonic_or_hex_seed, passphrase, ver=wally.BIP32_VER_MAIN_PRIVATE):
    """Generate a BIP32 HD Master Key (wallet) from a mnemonic phrase or a hex seed"""
    seed, mnemonic = seed_from_mnemonic(mnemonic_or_hex_seed, passphrase)
    return wally.bip32_key_from_seed(seed, ver, wally.BIP32_FLAG_SKIP_HASH)


def _decrypt_mnemonic(mnemonic, password):
    """Decrypt a 27 word encrypted mnemonic to a 24 word mnemonic"""
    mnemonic = ' '.join(mnemonic.split())
    entropy = wally.bip39_mnemonic_to_bytes(None, mnemonic)
    assert len(entropy) == wally.BIP39_ENTROPY_LEN_288
    salt, encrypted = entropy[32:], entropy[:32]
    derived = bytearray(64)
    wally.scrypt(password.encode('utf-8'), salt, 16384, 8, 8, derived)
    key = derived[32:]
    decrypted = wally.aes(key, encrypted, wally.AES_FLAG_DECRYPT)
    assert len(decrypted) == 32
    for i in range(len(decrypted)):
        decrypted[i] ^= derived[i]
    if wally.sha256d(decrypted)[:4] != salt:
        raise exceptions.InvalidMnemonicOrPasswordError('Incorrect password')
    return wally.bip39_mnemonic_from_bytes(None, decrypted)


def check_mnemonic_or_hex_seed(mnemonic):
    """Raise an error if mnemonic/hex seed is invalid"""
    if ' ' not in mnemonic:
        if mnemonic.endswith('X'):
            # mnemonic is the hex seed
            return
        msg = 'Mnemonic words must be separated by spaces, hex seed must end with X'
        raise exceptions.InvalidMnemonicOrPasswordError(msg)

    for word in mnemonic.split():
        if word not in wordlist:
            msg = 'Invalid word: {}'.format(word)
            raise exceptions.InvalidMnemonicOrPasswordError(msg)

    try:
        wally.bip39_mnemonic_validate(None, mnemonic)
    except ValueError:
        raise exceptions.InvalidMnemonicOrPasswordError('Invalid mnemonic checksum')
