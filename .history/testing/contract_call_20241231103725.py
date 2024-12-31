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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Wallet:
    """Class to manage cryptographic keys, signing, and address generation."""

    def __init__(self):
        self.private_key = PrivateKey()
        self.public_key = self.private_key.publicKey()
        self.address = self.generate_address()

    def generate_address(self):
        """Generate a unique address from the public key."""
        try:
            public_key_bytes = bytes.fromhex(self.public_key.toCompressed())
            sha256_hash = hashlib.sha256(public_key_bytes).digest()
            ripemd160_hash = hashlib.new("ripemd160", sha256_hash).digest()
            return base64.b64encode(ripemd160_hash).decode("utf-8")
        except Exception as e:
            logger.error(f"Error generating wallet address: {e}")
            raise RuntimeError("Failed to generate wallet address") from e

    def sign_transaction(self, transaction):
        """Sign a transaction using the private key."""
        try:
            transaction_json = json.dumps(transaction, sort_keys=True)
            signature = Ecdsa.sign(transaction_json, self.private_key)
            return signature.toBase64()
        except Exception as e:
            logger.error(f"Error signing transaction: {e}")
            raise RuntimeError("Failed to sign transaction") from e

    def verify_signature(self, transaction, compressed_public_key, digital_signature_base64):
        """Verify a transaction's digital signature."""
        try:
            transaction_json = json.dumps(transaction, sort_keys=True)
            public_key = PublicKey.fromCompressed(compressed_public_key)
            signature = Signature.fromBase64(digital_signature_base64)
            return Ecdsa.verify(transaction_json, signature, public_key)
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

# Initialize Wallet
wallet = Wallet()
logger.info(f"Generated Wallet Address: {wallet.address}")
logger.info(f"Private Key: {wallet.private_key.toString()}")

# Define the contract and parameters
contract_name = "wallet1"  # The name of the contract to be called
parameters = {"amount": 5}  # Example contract parameters (can vary by contract)

# Create the transaction payload
transaction_payload = {
    "sender": wallet.public_key.toCompressed(),  # Sender's public key as the address
    "contract_name": contract_name,  # Contract name
    "parameters": parameters,  # Parameters for the contract
    'function' : 'deposit',
    "timestamp": time.time(),  # Current timestamp
    "public_key": wallet.public_key.toCompressed(),  # Sender's public key
}

# Sign the transaction
try:
    # Generate the digital signature
    digital_signature = wallet.sign_transaction(transaction_payload)

    # Add the digital signature to the payload
    transaction_payload["digital_signature"] = digital_signature  # Digital signature

    # Log the transaction payload for debugging
    logger.info("Transaction Payload:")
    logger.info(json.dumps(transaction_payload, indent=4, sort_keys=True))

    # Define the server endpoint for contract calling
    endpoint = "http://127.0.0.1:5001/contracts/call"  # Adjust the port if needed

    # Send the transaction to the server for calling the contract
    response = requests.post(endpoint, json=transaction_payload)
    response.raise_for_status()  # Raise an error for HTTP status codes >= 400

    # Log the server's response
    logger.info("Server Response:")
    logger.info(response.json())

except Exception as e:
    logger.error(f"Error processing transaction: {e}")
