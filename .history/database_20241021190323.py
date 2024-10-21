import json
import os
import tempfile
from collections import OrderedDict
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

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
        self.temp_file = None

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
            
            nodes_dict = {str(i): node for i, node in enumerate(blockchain.nodes)}
            
            data = {
                'chain': unique_chain,
                'current_transactions': unique_transactions,
                'nodes': nodes_dict,
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
            data = self.ref.get()
            
            if not data:
                print("No data found in Firebase. Starting with a new blockchain.")
                return False
            
            print("Retrieving data from Firebase")
            chain = data.get('chain', [])
            current_transactions = data.get('current_transactions', [])
            
            nodes = set(tuple(node) if isinstance(node, list) else node for node in data.get('nodes', []))
            ttl = data.get('ttl', blockchain.ttl)
            
            blockchain.chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) for block in chain).values())
            if blockchain.current_transactions != []:
                blockchain.current_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) for tx in current_transactions).values())
            blockchain.nodes = nodes
            blockchain.ttl = ttl
            blockchain.hash_list = set(blockchain.hash(block) for block in blockchain.chain)
            
            self.save_blockchain(blockchain)
            return True
        except Exception as e:
            print(f"Error loading blockchain from Firebase: {e}")
            return False

    def save_to_temp_file(self):
        """
        Save the blockchain to a temporary file.
        """
        try:
            with open(local_file_path, 'r') as f:
                data = json.load(f)
            
            self.temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            json.dump(data, self.temp_file)
            self.temp_file.flush()
            print(f"Blockchain saved to temporary file: {self.temp_file.name}")
        except Exception as e:
            print(f"Error saving blockchain to temporary file: {e}")

    def save_to_firebase(self):
        """
        Save the blockchain from the local JSON file to Firebase after deleting the existing data.
        If saving to Firebase fails, revert to the temporary file.
        """
        try:
            if not os.path.exists(local_file_path):
                print("No local data found to save to Firebase.")
                return

            # Save to temporary file first
            self.save_to_temp_file()

            with open(local_file_path, 'r') as f:
                data = json.load(f)
            
            if not self.ref:
                self.ref = db.reference('blockchain')
            
            print("Deleting existing data from Firebase...")
            self.ref.delete()

            print("Saving new blockchain data to Firebase...")
            self.ref.set(data)
            print("Blockchain successfully saved to Firebase.")

            # Remove the temporary file if Firebase save was successful
            if self.temp_file:
                os.unlink(self.temp_file.name)
                self.temp_file = None

        except Exception as e:
            print(f"Error saving blockchain to Firebase: {e}")
            self.revert_to_temp_file()

    def revert_to_temp_file(self):
        """
        Revert the blockchain to the state saved in the temporary file and update Firebase.
        """
        if self.temp_file and os.path.exists(self.temp_file.name):
            try:
                with open(self.temp_file.name, 'r') as temp_f:
                    temp_data = json.load(temp_f)
                
                # Update local file
                with open(local_file_path, 'w') as local_f:
                    json.dump(temp_data, local_f, indent=2)
                
                print(f"Blockchain reverted to the state in temporary file: {self.temp_file.name}")

                # Update Firebase with the reverted data
                if not self.ref:
                    self.ref = db.reference('blockchain')
                
                print("Updating Firebase with reverted data...")
                self.ref.set(temp_data)
                print("Firebase updated successfully with reverted data.")

            except Exception as e:
                print(f"Error reverting to temporary file and updating Firebase: {e}")
            finally:
                os.unlink(self.temp_file.name)
                self.temp_file = None
        else:
            print("No temporary file found to revert to.")