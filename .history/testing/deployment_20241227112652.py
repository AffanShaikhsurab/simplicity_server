import json
import time
import requests
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.privateKey import PrivateKey , PublicKey 
class TransactionHandler:
    def __init__(self, private_address):
        self.private_address = private_address

    def sign_transaction(self, transaction):
        # Convert transaction to JSON string with sorted keys
        message = json.dumps(transaction, sort_keys=True)
        # Create PrivateKey object from private address
        private_key = PrivateKey.fromString(self.private_address)
        # Sign the message
        signature = Ecdsa.sign(message, private_key)
        # Return the Base64-encoded signature
        return signature.toBase64()

# Initialize the TransactionHandler with a private address
private_address = "03a591f399e3951aeba23ea4337367349b2289024acbc3990c2a41d767fc502846"  # Replace with actual private key
handler = TransactionHandler(private_address)

# Define the smart contract code
code = """
contract counter with count does 
    count is count + 1
.
"""

# Create the transaction payload
transaction = {
    "sender": "02b91a05153e9ba81b55e1ade91241bf17bfdc1b8f553b0aff35636ec6f7f5078a",
    "contract_name": "counter",
    "code": code,
    "recipient": "0",
    "timestamp": time.time(),
}

# Sign the transaction
digital_signature_base64 = handler.sign_transaction(transaction)

# Add public key and digital signature to the transaction
transaction["public_key"] = "03a591f399e3951aeba23ea4337367349b2289024acbc3990c2a41d767fc502846"  # Replace with actual compressed public key
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
