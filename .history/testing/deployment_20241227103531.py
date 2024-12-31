import requests


code = """
    contract counter with count does 
        count is count + 1
    .
    """

transaction = {
    "sender": "02b91a05153e9ba81b55e1ade91241bf17bfdc1b8f553b0aff35636ec6f7f5078a",
    "contract_name" : "counter",
    "code" : code
}

requests.post("http://0.0.0.0:5000/contracts/new", json=transaction, public_key = "publicKey" , digital_signature = "digital_signature")