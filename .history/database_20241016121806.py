import json
from collections import OrderedDict
import random
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
database_url = "https://simplicity-coin-default-rtdb.firebaseio.com/"


class BlockchainDb:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
        self.ref = db.reference('blockchain')

    def save_blockchain(self, blockchain):
        """
        Save the blockchain to Firebase.

        :param blockchain: The Blockchain instance to save
        """
        unique_chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) for block in blockchain.chain).values())
        unique_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) for tx in blockchain.current_transactions).values())

        data = {
            'chain': unique_chain,
            'current_transactions': unique_transactions,
            'nodes': list(blockchain.nodes),
            'ttl': blockchain.ttl
        }

        self.ref.set(data)
        print("Blockchain saved to Firebase")

    def load_blockchain(self, blockchain):
        """
        Load the blockchain from Firebase.

        :param blockchain: The Blockchain instance to update
        :return: True if loaded successfully, False otherwise
        """
        data = self.ref.get()

        if not data:
            print("No data found in Firebase. Starting with a new blockchain.")
            return False

        blockchain.chain = data.get('chain', [])
        blockchain.current_transactions = data.get('current_transactions', [])
        blockchain.nodes = set(data.get('nodes', []))
        blockchain.ttl = data.get('ttl', blockchain.ttl)

        # Rebuild hash_list
        blockchain.hash_list = set(blockchain.hash(block) for block in blockchain.chain)

        print("Blockchain loaded from Firebase")
        return True
