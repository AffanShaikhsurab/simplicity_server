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
    
    def load_storage_state(self):
        """
        Load the contract storage state from Firebase.
        
        Returns:
            dict: The loaded storage state or empty dict if none exists
        """
        try:
            # Try to load from Firebase first
            storage_data = self.ref.get()
            print("Firebase data:", storage_data)

            if not storage_data:
                # If no data in Firebase, try loading from local backup
                print("No data in Firebase, attempting to load from local file.")
                try:
                    with open('./contract_storage.json', 'r') as f:
                        storage_data = json.load(f)
                    print("Loaded data from local file:", storage_data)
                except FileNotFoundError:
                    print("Local file not found, returning empty storage.")
                    return {}
            
            # Deserialize the symbol tables
            for contract_name in storage_data:
                if "symbol_table" in storage_data[contract_name]:
                    print(f"Deserializing symbol table for contract: {contract_name}")
                    storage_data[contract_name]["symbol_table"] = self._deserialize_symbol_table(
                        storage_data[contract_name]["symbol_table"]
                    )
            
            print("Returning storage data:", storage_data)
            return storage_data
        except Exception as e:
            print(f"Error loading contract storage state: {e}")
            return {}

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