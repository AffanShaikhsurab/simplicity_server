import requests

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
    "public_key": "03a591f399e3951aeba23ea4337367349b2289024acbc3990c2a41d767fc502846",
    "digital_signature": "digital_signature"
}

# Send the transaction request
response = requests.post("http://127.0.0.1:5001/contracts/new", json=transaction)

# Handle the response
if response.status_code == 200:
    print("Contract submitted successfully:", response.json())
else:
    print(f"Failed to submit contract. Status code: {response.status_code}, Response: {response.text}")
