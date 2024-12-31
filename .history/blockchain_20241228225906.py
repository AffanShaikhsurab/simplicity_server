from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.privateKey import PrivateKey

# Generate a private key
private_key = PrivateKey()

# Sign a message
message = "Test message"
signature = Ecdsa.sign(message, private_key)

# Verify the signature
is_valid = Ecdsa.verify(message, signature, private_key.publicKey())
print("Signature valid:", is_valid)
