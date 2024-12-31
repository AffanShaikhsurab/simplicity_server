import json
import time
import requests
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.privateKey import PrivateKey


class TransactionHandler:
    def __init__(self, private_key: PrivateKey):
        self.private_key = private_key

    def sign_transaction(self, transaction):
        # Convert transaction to JSON string with sorted keys
        message = json.dumps(transaction, sort_keys=True)
        # Sign the message using the private key
        signature = Ecdsa.sign(message, self.private_key)
        # Return the Base64-encoded signature
        return signature.toBase64()


# Generate a new private key
private_key = PrivateKey()
public_key = private_key.publicKey()

print("Generated Private Key (Hex):", private_key.toString())
print("Corresponding Public Key (Compressed):", public_key.toCompressed())

# Initialize the TransactionHandler with the generated private key
handler = TransactionHandler(private_key)

# Define the smart contract code
code = """
contract counter with count does 
    count is count + 1
.
"""

# Create the transaction payload
transaction = {
    "sender": public_key.toCompressed(),  # Using public key as sender address
    "contract_name": "counter",
    "code": code,
    "recipient": "0",
    "timestamp": time.time(),
}

# Sign the transaction
digital_signature_base64 = handler.sign_transaction(transaction)

# Add public key and digital signature to the transaction
transaction["public_key"] = public_key.toCompressed()  # Compressed public key
transaction["digital_signature"] = digital_signature_base64

# Print transaction details for debugging
print("Transaction JSON:", json.dumps(transaction, indent=4, sort_keys=True))
print("Digital Signature (Base64):", digital_signature_base64)

# Send the transaction request
response = requests.post("http://127.0.0.1:5001/contracts/new", json=transaction)

# Handle the response
if response.status_code == 200:
    print("Contract submitted successfully:", response.json())
else:
    print(f"Failed to submit contract. Status code: {response.status_code}, Response: {response.text}")
