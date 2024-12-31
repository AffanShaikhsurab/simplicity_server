import json
import os
import tempfile
from collections import OrderedDict
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import atexit
import contextlib

firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
database_url = "https://simplicity-coin-default-rtdb.firebaseio.com"
local_file_path = "./blockchain.json"

class BlockchainDb:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
        self.ref = db.reference('blockchain')
        self.temp_file = None
        # Register cleanup on exit
        atexit.register(self.cleanup)

    def cleanup(self):
        """Clean up temporary files when the process exits."""
        self.close_temp_file()

    def close_temp_file(self):
        """Safely close and delete temporary file."""
        if self.temp_file:
            try:
                self.temp_file.close()
                if os.path.exists(self.temp_file.name):
                    os.unlink(self.temp_file.name)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}")
            finally:
                self.temp_file = None

    @contextlib.contextmanager
    def create_temp_file(self):
        """Context manager for handling temporary files."""
        temp = None
        try:
            temp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            yield temp
        finally:
            if temp:
                temp.close()

    def get_firebase_chain_length(self):
        """Get the length of the current chain in Firebase."""
        try:
            chain_data = self.ref.child('chain').get()
            return len(chain_data) if chain_data else 0
        except Exception as e:
            print(f"Error getting Firebase chain length: {e}")
            return 0

    def save_blockchain(self, blockchain):
        """Save the blockchain to a local JSON file."""
        try:
            print("Saving blockchain to local file")
            
            unique_chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) 
                                          for block in blockchain.chain).values())
            unique_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) 
                                                 for tx in blockchain.current_transactions).values())
            
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
        """Load the blockchain from Firebase."""
        try:
            data = self.ref.get()
            
            if not data:
                print("No data found in Firebase. Starting with a new blockchain.")
                return False
            
            print("Retrieving data from Firebase")
            chain = data.get('chain', [])
            current_transactions = data.get('current_transactions', [])
            
            nodes = set(tuple(node) if isinstance(node, list) else node 
                       for node in data.get('nodes', []))
            ttl = data.get('ttl', blockchain.ttl)
            
            blockchain.chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) 
                                              for block in chain).values())
            if blockchain.current_transactions != []:
                blockchain.current_transactions = list(OrderedDict((json.dumps(tx, sort_keys=True), tx) 
                                                                 for tx in current_transactions).values())
            blockchain.nodes = nodes
            blockchain.ttl = ttl
            blockchain.hash_list = set(blockchain.hash(block) for block in blockchain.chain)
            
            self.save_blockchain(blockchain)
            return True
        except Exception as e:
            print(f"Error loading blockchain from Firebase: {e}")
            return False

    def save_to_temp_file(self):
        """Save the blockchain to a temporary file."""
        self.close_temp_file()  # Clean up any existing temp file
        
        try:
            with open(local_file_path, 'r') as f:
                data = json.load(f)
            
            with self.create_temp_file() as temp:
                json.dump(data, temp)
                temp.flush()
                self.temp_file = temp
                print(f"Blockchain saved to temporary file: {temp.name}")
        except Exception as e:
            print(f"Error saving blockchain to temporary file: {e}")
            self.close_temp_file()

    def save_to_firebase(self):
        """Safely save the blockchain to Firebase with chain length validation."""
        if not os.path.exists(local_file_path):
            print("No local data found to save to Firebase.")
            return

        try:
            # Load local data
            with open(local_file_path, 'r') as f:
                new_data = json.load(f)
            
            # Get lengths of chains
            firebase_chain_length = self.get_firebase_chain_length()
            local_chain_length = len(new_data.get('chain', []))
            
            # Compare chain lengths
            if local_chain_length <= firebase_chain_length:
                print(f"Local chain ({local_chain_length}) is not longer than Firebase chain ({firebase_chain_length}). Skipping update.")
                return
            
            # Save to temporary file first for backup
            self.save_to_temp_file()
            
            if not self.ref:
                self.ref = db.reference('blockchain')

            print(f"Updating Firebase with longer chain (length: {local_chain_length})")
            
            # Update transactions and nodes
            self.ref.child('current_transactions').set(new_data.get('current_transactions', []))
            self.ref.child('nodes').set(new_data.get('nodes', {}))
            self.ref.child('ttl').set(new_data.get('ttl'))
            
            # Update chain blocks individually
            chain_ref = self.ref.child('chain')
            for index, block in enumerate(new_data.get('chain', [])):
                chain_ref.child(str(index)).set(block)
            
            print("Blockchain update to Firebase completed successfully.")
            self.close_temp_file()

        except Exception as e:
            print(f"Critical error saving blockchain to Firebase: {e}")
            self.revert_to_temp_file()

    def save_valid_chain(self, valid_chain):
        """Save a validated blockchain chain."""
        try:
            if not self.ref:
                self.ref = db.reference('blockchain')
            
            # Check chain lengths
            firebase_chain_length = self.get_firebase_chain_length()
            if len(valid_chain) <= firebase_chain_length:
                print(f"Valid chain ({len(valid_chain)}) is not longer than Firebase chain ({firebase_chain_length}). Skipping update.")
                return False
            
            # Create backup before deletion
            print("Creating backup of current blockchain...")
            self.save_to_temp_file()
            
            # Get chain reference
            chain_ref = self.ref.child('chain')
            
            print("Deleting existing chain from Firebase...")
            chain_ref.delete()
            
            print(f"Saving new valid chain (length: {len(valid_chain)}) to Firebase...")
            unique_chain = list(OrderedDict((json.dumps(block, sort_keys=True), block) 
                                          for block in valid_chain).values())
            
            for index, block in enumerate(unique_chain):
                try:
                    chain_ref.child(str(index)).set(block)
                    print(f"Saved block {block.get('index', 'unknown')} to Firebase")
                except Exception as e:
                    print(f"Error saving block {block.get('index', 'unknown')}: {e}")
                    self.revert_to_temp_file()
                    return False
            
            print("Successfully saved valid chain to Firebase")
            self.close_temp_file()
            return True
            
        except Exception as e:
            print(f"Critical error saving valid chain to Firebase: {e}")
            self.revert_to_temp_file()
            return False

    def revert_to_temp_file(self):
        """Revert the blockchain to the state saved in the temporary file."""
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
                self.close_temp_file()
        else:
            print("No temporary file found to revert to.")