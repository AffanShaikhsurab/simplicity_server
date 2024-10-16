import json
import os
from ellipticcurve.privateKey import PrivateKey

class AccountReader:
    def __init__(self, filename="accounts.json"):
        self.filename = filename
        self.account_data = self.load_accounts()

    def load_accounts(self):
        """Load account information from a JSON file."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except IOError as e:
                print(f"Error loading account data: {e}")
            except json.JSONDecodeError:
                print("Error decoding account data file")
        else:
            print(f"No accounts file found at {self.filename}")
        return []

