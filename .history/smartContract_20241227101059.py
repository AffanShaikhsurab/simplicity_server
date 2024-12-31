class SmartContractTransaction:
    def __init__(self, sender, contract_name, parameters, public_key , signature):
        self.sender = sender  # Address of the sender initiating the contract call
        self.contract_name = contract_name  # Name of the contract
        self.parameters = parameters  # List of parameter values for the contract
        self.public_key = public_key
        self.signature = signature
        self.timestamp = time()
        self.transaction_id = self.generate_transaction_id()
    def generate_transaction_id(self):
        transaction_data = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(transaction_data.encode()).hexdigest()

    def to_dict(self):
       return {
            "sender": self.sender,
            "contract_name": self.contract_name,
            "parameters": self.parameters,
            "public_address": self.public_key,
            "digital_signature": self.signature,
            "timestamp": self.timestamp,
            "transaction_id" : self.transaction_id

        }