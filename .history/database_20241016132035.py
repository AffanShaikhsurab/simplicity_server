import json
from collections import OrderedDict
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
        
        self.ref  = db.reference('blockchain')
        try:
            unique_chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) for block in blockchain.chain).values())
            unique_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) for tx in blockchain.current_transactions).values())

            if not unique_chain or not unique_transactions:
                print("No data to save to Firebase. Starting with a new blockchain.")
                return

            # Ensure nodes are stored as hashable types (e.g., converting lists to tuples if necessary)
            hashable_nodes = set(tuple(node) if isinstance(node, list) else node for node in blockchain.nodes)

            data = {
                'chain': unique_chain,
                'current_transactions': unique_transactions,
                'nodes': list(hashable_nodes),
                'ttl': blockchain.ttl
            }

            self.ref.set(data)
            print("Blockchain saved to Firebase")
        except Exception as e:
            print(f"Error saving blockchain: {e}")

    def load_blockchain(self, blockchain):
        """
        Load the blockchain from Firebase.

        :param blockchain: The Blockchain instance to update
        :return: True if loaded successfully, False otherwise
        """
        try:
            data = self.ref.get()
            ref = self.ref

            if not data:
                print("No data found in Firebase. Starting with a new blockchain.")
                return False
            print("retriving data from firebase")
            blockchain.chain = ref.get('chain', [])
            print("retrived data from firebase" , ref.get('chain', []))

            blockchain.current_transactions = ref.get('current_transactions', [])

            # Ensure nodes are converted back to hashable types (set requires hashable types)
            blockchain.nodes = set(tuple(node) if isinstance(node, list) else node for node in ref.get('nodes', []))
            blockchain.ttl = ref.get('ttl', blockchain.ttl)

            # Rebuild hash_list
            blockchain.hash_list = set(blockchain.hash(block) for block in blockchain.chain)

            print("Blockchain loaded from Firebase")
            return True
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            return False
