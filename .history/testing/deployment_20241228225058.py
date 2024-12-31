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
        self.address = self.public_key_to_address()

    def public_key_to_address(self):
        """Generate a unique address from the public key."""
        try:
            public_key_bytes = bytes.fromhex(self.public_key.toCompressed())
            sha256_hash = hashlib.sha256(public_key_bytes).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            return base64.b64encode(ripemd160_hash).decode('utf-8')
        except Exception as e:
            logger.error(f"Error generating address: {e}")
            raise

    def sign_transaction(self, transaction):
        """Sign a transaction using the private key."""
        try:
            message = json.dumps(transaction, sort_keys=True)
            signature = Ecdsa.sign(message, self.private_key)
            return signature.toBase64()
        except Exception as e:
            logger.error(f"Error signing transaction: {e}")
            raise

    def verify_digital_signature(self, transaction, compressed_public_key, digital_signature_base64):
        """Verify a transaction's digital signature."""
        try:
            transaction_json = json.dumps(transaction, sort_keys=True)
            public_address = PublicKey.fromCompressed(compressed_public_key)
            digital_signature = Signature.fromBase64(digital_signature_base64)
            is_valid = Ecdsa.verify(transaction_json, digital_signature, public_address)
            return is_valid
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False


# Initialize the Wallet
wallet = Wallet()
logger.info(f"Generated Wallet Address: {wallet.address}")

# Extract private key and compressed address
private_key_str = wallet.private_key.toString()
compressed_address = wallet.address
logger.info(f"Private Key: {private_key_str}")
logger.info(f"Compressed Address: {compressed_address}")

# Create transaction payload
transaction = {
    "sender": wallet.public_key.toCompressed(),  # Use the public address from the wallet
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
try:
    sign_response = requests.post("http://127.0.0.1:5001/sign_transaction", json=sign_data)
    sign_response.raise_for_status()
    signed_data = sign_response.json()
    logger.info("Signed Transaction:")
    logger.info(json.dumps(signed_data, indent=4))
except requests.exceptions.RequestException as e:
    logger.error(f"Error during transaction signing: {e}")
except json.JSONDecodeError as e:
    logger.error(f"Error decoding JSON response: {e}")
