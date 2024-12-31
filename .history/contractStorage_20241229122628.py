import json
import firebase_admin
from firebase_admin import credentials

from firebase_admin import db
firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
database_url = "https://simplicity-coin-default-rtdb.firebaseio.com"
class ContractStorageDb:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            self.local_storage_path = './contract_storage.json'

        self.ref = db.reference('contract_storage')
        
    def save_storage_state(self, storage_state):
        """
        Save the current contract storage state to Firebase.
        
        Args:
            storage_state (dict): Current contract storage state
        """
        try:
            # Convert any non-serializable objects to strings
            serializable_state = {}
            for contract_name, data in storage_state.items():
                serializable_state[contract_name] = {
                    "contract_name": data["contract_name"],
                    "symbol_table": self._serialize_symbol_table(data["symbol_table"])
                }
            print("the contract state is " , storage_state)
            # Save to Firebase
            self.ref.set(serializable_state)
            
            # Also save locally for backup
            with open('./contract_storage.json', 'w') as f:
                json.dump(serializable_state, f, indent=2)
                
            print("Contract storage state saved successfully")
            return True
        except Exception as e:
            print(f"Error saving contract storage state: {e}")
            return False

import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os

class ContractStorageDb:
    def __init__(self):
        self.firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
        self.database_url = "https://simplicity-coin-default-rtdb.firebaseio.com"
        self.local_storage_path = './contract_storage.json'
        
        # Add initialization logging
        print(f"Initializing ContractStorageDb")
        print(f"Checking if local storage exists: {os.path.exists(self.local_storage_path)}")
        
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(self.firebase_cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.database_url
                })
                print("Firebase initialized successfully")
            except Exception as e:
                print(f"Firebase initialization error: {e}")
        self.ref = db.reference('contract_storage')
    def initialize_contract_storage():
        # Your contract data
        contract_data = {
            "counter1": {
                "contract_name": "counter1",
                "symbol_table": None
            }
        }
        
        # Write to the local file
        with open('contract_storage.json', 'w') as f:
            json.dump(contract_data, f, indent=2)
            
        print("Contract data initialized successfully")
        
        # Verify the file contents
        with open('contract_storage.json', 'r') as f:
            saved_data = json.load(f)
            print("\nVerifying saved data:")
            print(json.dumps(saved_data, indent=2))

    def load_storage_state(self):
        """
        Load the contract storage state with enhanced debugging.
        """
        print("\n=== Starting load_storage_state ===")
        try:
            # Step 1: Try Firebase first
            print("\n--- Step 1: Loading from Firebase ---")
            storage_data = self.ref.get()
            print(f"Raw Firebase data: {repr(storage_data)}")  # Using repr for exact representation

            # Step 2: Try local file if Firebase is empty
            if storage_data is None:
                print("\n--- Step 2: Loading from local file ---")
                try:
                    # Check if file exists and is readable
                    if not os.path.exists(self.local_storage_path):
                        print(f"Error: Local file does not exist at {self.local_storage_path}")
                        return {}
                    
                    # Check file size
                    file_size = os.path.getsize(self.local_storage_path)
                    print(f"Local file size: {file_size} bytes")
                    
                    # Read raw content first
                    with open(self.local_storage_path, 'r') as f:
                        raw_content = f.read()
                        print(f"Raw file content: {repr(raw_content)}")
                    
                    # Try to parse JSON
                    try:
                        storage_data = json.loads(raw_content)
                        print(f"Parsed JSON data: {repr(storage_data)}")
                    except json.JSONDecodeError as je:
                        print(f"JSON parsing error: {je}")
                        print(f"Error at position: {je.pos}")
                        print(f"Line number: {je.lineno}")
                        print(f"Column number: {je.colno}")
                        return {}
                    
                    # Validate structure
                    if not isinstance(storage_data, dict):
                        print(f"Error: Loaded data is not a dictionary. Type: {type(storage_data)}")
                        return {}
                    
                    # Push to Firebase if valid
                    self.ref.set(storage_data)
                    print("Local data synced to Firebase")
                    
                except Exception as e:
                    print(f"Local file reading error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {}

            # Final validation
            print("\n--- Final Data Validation ---")
            if not storage_data:
                print("Error: No data found in storage_data")
                return {}
                
            if not isinstance(storage_data, dict):
                print(f"Error: Final data is not a dictionary. Type: {type(storage_data)}")
                return {}

            # Process contract data
            print("\n--- Processing Contracts ---")
            processed_data = {}
            for contract_name, contract_data in storage_data.items():
                print(f"Processing contract: {contract_name}")
                print(f"Contract data: {repr(contract_data)}")
                
                if not isinstance(contract_data, dict):
                    print(f"Warning: Invalid contract data for {contract_name}")
                    continue
                    
                processed_data[contract_name] = {
                    "contract_name": contract_data.get("contract_name"),
                    "symbol_table": self._deserialize_symbol_table(contract_data.get("symbol_table"))
                }
                print(f"Processed contract data: {repr(processed_data[contract_name])}")

            print("\n=== Final processed data ===")
            print(repr(processed_data))
            return processed_data

        except Exception as e:
            print(f"Unexpected error in load_storage_state: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
            
    def _deserialize_symbol_table(self, serialized_table):
        """Handle symbol table deserialization with null check."""
        if serialized_table is None:
            return None
            
        from simplyLang.interpreter import SymbolTable, Number
        
        symbol_table = SymbolTable()
        for key, value_data in serialized_table.items():
            if value_data['type'] == 'Number':
                symbol_table.set(key, Number(value_data['value']))
            else:
                symbol_table.set(key, value_data['value'])
        return symbol_table
    def broadcast_storage_state(self, nodes, storage_state):
        """
        Broadcast storage state to all known nodes.
        
        Args:
            nodes (set): Set of node URLs
            storage_state (dict): Current storage state to broadcast
        """
        import requests
        
        for node in nodes:
            try:
                node_url = self._format_node_url(node)
                response = requests.post(
                    f'http://{node_url}/nodes/update_storage',
                    json={"storage_state": storage_state}
                )
                if response.status_code == 200:
                    print(f"Successfully broadcast storage state to {node}")
                else:
                    print(f"Failed to broadcast to {node}: {response.status_code}")
            except Exception as e:
                print(f"Error broadcasting to {node}: {e}")
    
    def _serialize_symbol_table(self, symbol_table):
        """
        Convert symbol table to serializable format.
        """
        if symbol_table is None:
            return None
        
        serialized = {}
        for key, value in symbol_table.symbols.items():
            if hasattr(value, 'value'):
                serialized[key] = {
                    'type': value.__class__.__name__,
                    'value': value.value
                }
            else:
                serialized[key] = {
                    'type': 'raw',
                    'value': value
                }
        return serialized
    
    def _deserialize_symbol_table(self, serialized_table):
        """
        Convert serialized format back to symbol table.
        """
        if serialized_table is None:
            return None
        
        from simplyLang.interpreter import SymbolTable, Number
        
        symbol_table = SymbolTable()
        for key, value_data in serialized_table.items():
            if value_data['type'] == 'Number':
                symbol_table.set(key, Number(value_data['value']))
            else:
                symbol_table.set(key, value_data['value'])
        return symbol_table
    
    def _format_node_url(self, url):
        """Format node URL consistently."""
        url = url.replace("https://", "").replace("http://", "")
        if "simplicity" in url:
            if not url.endswith(".onrender.com"):
                url = f"{url}.onrender.com"
        else:
            if not url.endswith(".trycloudflare.com"):
                url = f"{url}.trycloudflare.com"
        return url