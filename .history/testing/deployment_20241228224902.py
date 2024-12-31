import base64
import hashlib
import json
import logging
import time
import requests
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.privateKey import PrivateKey
from ellipticcurve.publicKey import PublicKey
from ellipticcurve.signature import Signature
class Wallet:
    def __init__(self):
        self.private_key = PrivateKey()
        self.public_key = self.private_key.publicKey()
        self.address = self.public_key_to_address()

    def public_key_to_address(self):
        public_key_bytes = bytes.fromhex(self.public_key.toCompressed())
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        return base64.b64encode(ripemd160_hash).decode('utf-8')

    def sign_transaction(self, transaction):
        message = json.dumps(transaction, sort_keys=True)
        signature = Ecdsa.sign(message, self.private_key)
        return signature.toBase64()

    def verify_digital_signature(self, transaction, compressed_public_key, digital_signature_base64):
        try:
            # Convert transaction to JSON with sorted keys
            transaction_json = json.dumps(transaction, sort_keys=True)

            # Create PublicKey object
            public_address = PublicKey.fromCompressed(compressed_public_key)

            # Create Signature object
            digital_signature = Signature.fromBase64(digital_signature_base64)

            # Verify the signature
            print(
                f"Transaction JSON: {transaction_json}, Public Address: {public_address}, Digital Signature: {digital_signature}"
            )
            is_valid = Ecdsa.verify(transaction_json, digital_signature, public_address)

            return is_valid

        except Exception as e:
            logging.error(f"Error verifying signature: {e}")
            return False

# Initialize the Wallet
wallet = Wallet()

# Generate a new account
response = requests.get("http://127.0.0.1:5005/create_account")
if response.status_code != 200:
    raise Exception("Failed to create account")
account_data = response.json()
print("Generated Account:", account_data)

# Extract private key and compressed address
private_key_str = account_data["privateKey"]
compressed_address = account_data["compressed_address"]

# Create transaction payload
transaction = {
    "sender": account_data["public_address"],  # Use the public address from the generated wallet
    "recipient": "recipient_address_example",  # Replace with the actual recipient address
    "amount": 100,  # Example amount
    "timestamp": time.time(),
}

# Prepare the transaction data for signing
sign_data = {
    "private_key": private_key_str,
    "recipient": transaction["recipient"],
    "amount": transaction["amount"],
}

# Call the `/sign_transaction` endpoint
sign_response = requests.post("http://127.0.0.1:5001/sign_transaction", json=sign_data)

if sign_response.status_code != 200:
    print(f"Failed to sign transaction: {sign_response.text}")
else:
    signed_data = sign_response.json()
    print("Signed Transaction:", json.dumps(signed_data, indent=4))
