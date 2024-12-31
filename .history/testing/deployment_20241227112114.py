import json
import time
import requests
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import base64

# Define the smart contract code
code = """
contract counter with count does 
    count is count + 1
.
"""

# Generate the ECDSA private and public keys (for demonstration purposes)
# In a real-world scenario, the private key is securely stored and not exposed
private_key = SigningKey.generate(curve=SECP256k1)
public_key = private_key.get_verifying_key()

# Compress the public key
public_key_compressed = "03" + public_key.to_string().hex()[:64]  # Example of compressed form

# Create the transaction payload
transaction = {
    "sender": "02b91a05153e9ba81b55e1ade91241bf17bfdc1b8f553b0aff35636ec6f7f5078a",
    "contract_name": "counter",
    "code": code,
    "recipient": "0",
    "timestamp": time.time(),
}

# Convert transaction to JSON with sorted keys
transaction_json = json.dumps(transaction, sort_keys=True)

# Generate the digital signature
signature = private_key.sign(transaction_json.encode('utf-8'))  # Sign the transaction
digital_signature_base64 = base64.b64encode(signature).decode('utf-8')  # Encode the signature in Base64

# Add public key and digital signature to the transaction
transaction["public_key"] = public_key_compressed
transaction["digital_signature"] = digital_signature_base64

# Print details for debugging
print("Transaction JSON:", transaction_json)
print("Compressed Public Key:", public_key_compressed)
print("Digital Signature (Base64):", digital_signature_base64)

# Send the transaction request
response = requests.post("http://127.0.0.1:5001/contracts/new", json=transaction)

# Handle the response
if response.status_code == 200:
    print("Contract submitted successfully:", response.json())
else:
    print(f"Failed to submit contract. Status code: {response.status_code}, Response: {response.text}")
