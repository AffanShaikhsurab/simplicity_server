import json
from collections import OrderedDict
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os

firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
database_url = "https://simplicity-coin-default-rtdb.firebaseio.com"
local_file_path = "blockchain.json"

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
        Save the blockchain to a local JSON file.
        
        :param blockchain: The Blockchain instance to save
        """
        try:
            print("Saving blockchain to local file")

            unique_chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) for block in blockchain.chain).values())
            unique_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) for tx in blockchain.current_transactions).values())
            
            if not unique_chain:
                print("No data to save. Starting with a new blockchain.")
                return
            
            hashable_nodes = set(tuple(node) if isinstance(node, list) else node for node in blockchain.nodes)
            
            data = {
                'chain': unique_chain,
                'current_transactions': unique_transactions,
                'nodes': list(hashable_nodes),
                'ttl': blockchain.ttl
            }
            
            with open(local_file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print("Blockchain saved to local file")
        except Exception as e:
            print(f"Error saving blockchain to local file: {e}")

    def load_blockchain(self, blockchain):
        """
        Load the blockchain from Firebase.
        
        :param blockchain: The Blockchain instance to update
        :return: True if loaded successfully, False otherwise
        """
        try:
            self.ref = db.reference('blockchain')
            data = self.ref.get()
            
            if not data:
                print("No data found in Firebase. Starting with a new blockchain.")
                return False
            
            print("Retrieving data from Firebase")
            chain = data.get('chain', [])
            current_transactions = data.get('current_transactions', [])
            
            # Ensure nodes are converted back to hashable types (set requires hashable types)
            nodes = set(tuple(node) if isinstance(node, list) else node for node in data.get('nodes', []))
            ttl = data.get('ttl', blockchain.ttl)
            
            # Rebuild hash_list
            
            blockchain.chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) for block in chain).values())
            if blockchain.current_transactions != []:
                blockchain.current_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) for tx in current_transactions).values())
            blockchain.nodes =nodes
            blockchain.ttl = ttl
            # Rebuild hash_list
            blockchain.hash_list = set(blockchain.hash(block) for block in blockchain.chain)
            
            
            self.save_blockchain(blockchain)
            return True
        except Exception as e:
            print(f"Error loading blockchain from Firebase: {e}")
            return False

    def save_to_firebase(self):
        """
        Save the blockchain from the local JSON file to Firebase.
        """
        try:
            if not os.path.exists(local_file_path):
                print("No local data found to save to Firebase.")
                return
            
            with open(local_file_path, 'r') as f:
                data = json.load(f)
            self.ref.delete()
            print("Deleting data from Firebase")
            self.ref = db.reference('blockchain')
            self.ref.set(data)
            print("Blockchain saved to Firebase")
        except Exception as e:
            print(f"Error saving blockchain to Firebase: {e}")
