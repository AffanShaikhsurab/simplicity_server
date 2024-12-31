import json
import time
from ellipticcurve.privateKey import PrivateKey
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.signature import Signature

# Mock wallet with private key and public key
class Wallet:
    def __init__(self):
        self.private_key = PrivateKey()
        self.public_key = self.private_key.publicKey()

    def to_compressed(self):
        return self.public_key.toCompressed()

    def sign_transaction(self, transaction):
        message = json.dumps(transaction, sort_keys=True)  # Sort keys for consistent signing
        signature = Ecdsa.sign(message, self.private_key)
        return signature.toBase64()

# Create a wallet instance
wallet = Wallet()

# Create a transaction payload
transaction = {
    "sender": wallet.to_compressed(),  # Compressed public key
    "contract_name": "counter",
    "timestamp": time.time(),
}

# Sign the transaction
try:
    # Sort keys and serialize the transaction
    sorted_transaction_json = json.dumps(transaction, sort_keys=True)

    # Generate digital signature
    digital_signature = wallet.sign_transaction(transaction)

    # Print debug information
    print("Transaction JSON:", sorted_transaction_json)
    print("Compressed Public Key:", wallet.to_compressed())
    print("Digital Signature:", digital_signature)

    # Prepare payload for the server
    payload = {
        "sender": wallet.to_compressed(),
        "contract_name": transaction["contract_name"],
        "timestamp": transaction["timestamp"],
        "code": """
        contract counter with count does
            count is count + 1
        .
        """,
        "public_key": wallet.to_compressed(),
        "digital_signature": digital_signature,
    }

    # Send the transaction payload to the server
    import requests
    response = requests.post("http://127.0.0.1:5001/contracts/new", json=payload)

    # Log the server response
    print("Server Response:", response.status_code, response.json())

except Exception as e:
    print("Error:", e)
