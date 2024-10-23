import json
import logging
from flask import Flask, request, jsonify, abort
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.privateKey import PrivateKey
from ellipticcurve.publicKey import PublicKey
from ellipticcurve.signature import Signature
import hashlib
import base64
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


@app.route('/create_account', methods=['GET'])
def create_account():
    wallet = Wallet()
    logger.info("Account created: %s", wallet.address)
    return jsonify({
        'public_address': wallet.public_key.toCompressed(),
        'privateKey' : wallet.private_key.toString() ,
        'compressed_address': wallet.address
    })


@app.route('/sign_transaction', methods=['POST'])
def sign_transaction():
    data = request.json

    required_fields = ['private_key', 'recipient', 'amount' , 'public_key']
    for field in required_fields:
        if field not in data:
            logger.error(f"Missing field: {field}")
            abort(400, description=f'Missing field: {field}')

    try:
        wallet = Wallet()
        wallet.private_key = PrivateKey.fromString(data['private_key'])
        wallet.public_key = data['public_key']
        transaction = {
            "sender": wallet.public_key.toCompressed(),
            "recipient": data['recipient'],
            "amount": data['amount'],
            "timestamp": time.time()
        }

        transaction_string = json.dumps(transaction, sort_keys=True)
        transaction_id = hashlib.sha256(transaction_string.encode()).hexdigest()
        transaction["transaction_id"] = transaction_id

        signature = wallet.sign_transaction(transaction)

        logger.info("Transaction signed: %s", transaction_id)
        
        print("the signature is " , wallet.verify_digital_signature(transaction, wallet.public_key.toCompressed(), signature))
        
        return jsonify({
            "transaction": transaction,
            "digital_signature": signature,
            "public_key": wallet.public_key.toCompressed()
        })
    except Exception as e:
        logger.error("Error signing transaction: %s", str(e))
        abort(500, description="Error signing transaction")


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False, port=5005)