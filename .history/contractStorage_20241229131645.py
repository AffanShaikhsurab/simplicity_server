import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os
from typing import Any, Dict
from simplyLang.lexer import *
from simplyLang.praser import *

class ContractStorageDb:
    def __init__(self):
        self.firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
        self.database_url = "https://simplicity-coin-default-rtdb.firebaseio.com"
        self.local_storage_path = './contract_storage.json'
        
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
        self.initialize_contract_storage()

    def _serialize_position(self, pos):
        """Serialize position information."""
        if not pos:
            return None
        return {
            'idx': getattr(pos, 'idx', 0),
            'ln': getattr(pos, 'ln', 0),
            'col': getattr(pos, 'col', 0),
            'filename': getattr(pos, 'filename', '')
        }

    def _serialize_token(self, token):
        """Serialize token information."""
        if not token:
            return None
        return {
            'type': 'Token',
            'value': token.value if hasattr(token, 'value') else str(token),
            'start': self._serialize_position(getattr(token, 'start', None)),
            'end': self._serialize_position(getattr(token, 'end', None))
        }

    def _serialize_node(self, node):
        """Comprehensive node serializer that handles all node types."""
        if node is None:
            return None
            
        node_type = node.__class__.__name__
        
        serializers = {
            'StatementsNode': lambda n: {
                'type': 'StatementsNode',
                'statements': [self._serialize_node(stmt) for stmt in n.statements]
            },
            
            'BinaryOperationNode': lambda n: {
                'type': 'BinaryOperationNode',
                'left': self._serialize_node(n.left),
                'op': self._serialize_token(n.token),
                'right': self._serialize_node(n.right)
            },
            
            'CallContractNode': lambda n: {
                'type': 'CallContractNode',
                'contract_name': n.contract_name,
                'parameters': [self._serialize_node(param) for param in n.parameters]
            },
            
            'ContractNode': lambda n: {
                'type': 'ContractNode',
                'name': n.contract_name,
                'body': [self._serialize_node(stmt) for stmt in n.body],
                'variables': [self._serialize_node(var) for var in (n.variables or [])]
            },
            
            'GetPictureNode': lambda n: {
                'type': 'GetPictureNode',
                'variable': self._serialize_node(n.varibale)
            },
            
            'IfNode': lambda n: {
                'type': 'IfNode',
                'condition': self._serialize_node(n.condition_expr),
                'then': [self._serialize_node(expr) for expr in n.then_expr],
                'otherwise': [self._serialize_node(expr) for expr in (n.otherwise_expr or [])]
            },
            
            'TryNode': lambda n: {
                'type': 'TryNode',
                'then': [self._serialize_node(expr) for expr in n.then_expr],
                'otherwise': [self._serialize_node(expr) for expr in (n.otherwise_expr or [])]
            },
            
            'FunctionNode': lambda n: {
                'type': 'FunctionNode',
                'name': n.function_name,
                'body': [self._serialize_node(stmt) for stmt in n.body],
                'variables': [self._serialize_node(var) for var in (n.variables or [])]
            },
            
            'FunctionCallNode': lambda n: {
                'type': 'FunctionCallNode',
                'name': n.function_name,
                'parameters': [self._serialize_node(param) for param in n.parameters]
            },
            
            'ClassNode': lambda n: {
                'type': 'ClassNode',
                'name': n.class_name,
                'body': [self._serialize_node(stmt) for stmt in n.body],
                'variable': self._serialize_node(n.variable)
            },
            
            'ClassifyNode': lambda n: {
                'type': 'ClassifyNode',
                'variable_name': n.variable_name
            },
            
            'TillNode': lambda n: {
                'type': 'TillNode',
                'condition': self._serialize_node(n.condition_expr),
                'body': [self._serialize_node(stmt) for stmt in n.body]
            },
            
            'ShowNode': lambda n: {
                'type': 'ShowNode',
                'body': self._serialize_node(n.body)
            },
            
            'VariableAccessNode': lambda n: {
                'type': 'VariableAccessNode',
                'variable_name': self._serialize_token(n.variable_name)
            },
            
            'ArrayVariable': lambda n: {
                'type': 'ArrayVariable',
                'variable': self._serialize_token(n.variable),
                'index': self._serialize_node(n.index),
                'expression': self._serialize_node(n.expression)
            },
            
            'ClassAccessNode': lambda n: {
                'type': 'ClassAccessNode',
                'class_name': self._serialize_token(n.class_name),
                'access_node': self._serialize_node(n.access_node)
            },
            
            'NoteNode': lambda n: {
                'type': 'NoteNode',
                'note': [self._serialize_token(token) for token in n.note]
            },
            
            'VariableNode': lambda n: {
                'type': 'VariableNode',
                'variable_name': self._serialize_token(n.variable_name),
                'value_node': self._serialize_node(n.value_node)
            },
            
            'VariableFunctionNode': lambda n: {
                'type': 'VariableFunctionNode',
                'variable_name': self._serialize_token(n.variable_name),
                'value_node': self._serialize_node(n.value_node)
            },
            
            'VariableClassFunctionNode': lambda n: {
                'type': 'VariableClassFunctionNode',
                'variable_name': self._serialize_token(n.variable_name),
                'class_name': self._serialize_token(n.class_name),
                'function': self._serialize_node(n.function)
            },
            
            'ArrayNode': lambda n: {
                'type': 'ArrayNode',
                'variable_name': self._serialize_token(n.variable_name),
                'value_node': self._serialize_node(n.value_node)
            },
            
            'DictNode': lambda n: {
                'type': 'DictNode',
                'variable_name': self._serialize_token(n.variable_name),
                'dictionary': n.dictronary  # Assuming dictionary contains basic types
            },
            
            'ArrayAccessNode': lambda n: {
                'type': 'ArrayAccessNode',
                'variable_name': self._serialize_token(n.variable_name),
                'value_node': self._serialize_node(n.value_node),
                'access_variable': self._serialize_node(n.access_variable)
            },
            
            'ArrayArrangeNode': lambda n: {
                'type': 'ArrayArrangeNode',
                'variable_name': self._serialize_token(n.variable_name),
                'array': self._serialize_node(n.array),
                'type': n.type
            },
            
            'ClassAssignNode': lambda n: {
                'type': 'ClassAssignNode',
                'class_name': n.class_name,
                'value_node': n.value_node,
                'variables': [self._serialize_node(var) for var in n.variables]
            },
            
            'RepeatNode': lambda n: {
                'type': 'RepeatNode',
                'range': n.range,
                'body': [self._serialize_node(stmt) for stmt in n.body]
            },
            
            'ReturnNode': lambda n: {
                'type': 'ReturnNode',
                'token': self._serialize_token(n.token)
            },
            
            'ReturnExprNode': lambda n: {
                'type': 'ReturnExprNode',
                'token': self._serialize_node(n.token)
            },
            
            'UpdateDictNode': lambda n: {
                'type': 'UpdateDictNode',
                'key': self._serialize_token(n.key),
                'dict': self._serialize_node(n.dict),
                'expression': self._serialize_node(n.expression)
            },
            
            'NumberNode': lambda n: {
                'type': 'NumberNode',
                'token': self._serialize_token(n.token)
            },
            
            'StopNode': lambda n: {
                'type': 'StopNode',
                'token': self._serialize_token(n.token),
                'string': n.string
            },
            
            'BoolNode': lambda n: {
                'type': 'BoolNode',
                'token': self._serialize_token(n.token)
            },
            
            'AccessDictNode': lambda n: {
                'type': 'AccessDictNode',
                'variable': self._serialize_token(n.variable),
                'key': self._serialize_token(n.key),
                'dict': self._serialize_node(n.dict)
            },
            
            'ArrayLengthNode': lambda n: {
                'type': 'ArrayLengthNode',
                'variable': self._serialize_token(n.variable),
                'expression': self._serialize_node(n.expression)
            },
            
            'ShowMultiNode': lambda n: {
                'type': 'ShowMultiNode',
                'string': n.string,
                'variable': self._serialize_node(n.variable)
            },
            
            'UniaryOperatorNode': lambda n: {
                'type': 'UniaryOperatorNode',
                'token': self._serialize_token(n.token),
                'node': self._serialize_node(n.node)
            }
        }
        
        serializer = serializers.get(node_type)
        if serializer:
            try:
                return serializer(node)
            except Exception as e:
                print(f"Error serializing {node_type}: {str(e)}")
                return {'type': 'Error', 'message': f"Failed to serialize {node_type}"}
        
        # Default serialization for unknown types
        return {
            'type': 'Unknown',
            'node_type': node_type,
            'str_value': str(node)
        }

    def _deserialize_position(self, pos_data):
        """Deserialize position information."""
        if not pos_data:
            return None
            
        class Position:
            def __init__(self, idx, ln, col, filename):
                self.idx = idx
                self.ln = ln
                self.col = col
                self.filename = filename
                
        return Position(
            pos_data.get('idx', 0),
            pos_data.get('ln', 0),
            pos_data.get('col', 0),
            pos_data.get('filename', '')
        )

    def _deserialize_token(self, token_data):
        """Deserialize token information."""
        if not token_data:
            return None
            
        class Token:
            def __init__(self, value, start, end):
                self.value = value
                self.start = start
                self.end = end
                
        return Token(
            token_data.get('value'),
            self._deserialize_position(token_data.get('start')),
            self._deserialize_position(token_data.get('end'))
        )

    def _deserialize_node(self, data):
        """Complete deserializer for all node types."""
        if not data or not isinstance(data, dict):
            return None

        node_type = data.get('type')
        if not node_type:
            return None

        deserializers = {
            'StatementsNode': lambda d: StatementsNode(
                [self._deserialize_node(stmt) for stmt in d['statements']]
            ),
            
            'BinaryOperationNode': lambda d: BinaryOperationNode(
                self._deserialize_node(d['left']),
                self._deserialize_token(d['op']),
                self._deserialize_node(d['right'])
            ),
            
            'CallContractNode': lambda d: CallContractNode(
                d['contract_name'],
                [self._deserialize_node(param) for param in d['parameters']]
            ),
            
            'ContractNode': lambda d: ContractNode(
                d['name'],
                [self._deserialize_node(stmt) for stmt in d['body']],
                [self._deserialize_node(var) for var in d.get('variables', [])]
            ),
            
            'GetPictureNode': lambda d: GetPictureNode(
                self._deserialize_node(d['variable'])
            ),
            
            'IfNode': lambda d: IfNode(
                self._deserialize_node(d['condition']),
                [self._deserialize_node(expr) for expr in d['then']],
                [self._deserialize_node(expr) for expr in d.get('otherwise', [])]
            ),
            
            'TryNode': lambda d: TryNode(
                [self._deserialize_node(expr) for expr in d['then']],
                [self._deserialize_node(expr) for expr in d.get('otherwise', [])]
            ),
            
            'FunctionNode': lambda d: FunctionNode(
                d['name'],
                [self._deserialize_node(stmt) for stmt in d['body']],
                [self._deserialize_node(var) for var in d.get('variables', [])]
            ),
            
            'FunctionCallNode': lambda d: FunctionCallNode(
                d['name'],
                self._deserialize_token(d['function']),
                [self._deserialize_node(param) for param in d['parameters']]
            ),
            
            'ClassNode': lambda d: ClassNode(
                d['name'],
                [self._deserialize_node(stmt) for stmt in d['body']],
                self._deserialize_node(d['variable'])
            ),
            
            'ClassifyNode': lambda d: ClassifyNode(
                self._deserialize_token(Token(d['variable_name'], None, None))
            ),
            
            'TillNode': lambda d: TillNode(
                self._deserialize_node(d['condition']),
                [self._deserialize_node(stmt) for stmt in d['body']]
            ),
            
            'ShowNode': lambda d: ShowNode(
                self._deserialize_node(d['body']),
                self._deserialize_token(d.get('position_var'))
            ),
            
            'VariableAccessNode': lambda d: VariableAccessNode(
                self._deserialize_token(d['variable_name'])
            ),
            
            'ArrayVariable': lambda d: ArrayVariable(
                self._deserialize_token(d['variable']),
                self._deserialize_node(d['index']),
                self._deserialize_node(d['expression'])
            ),
            
            'ClassAccessNode': lambda d: ClassAccessNode(
                self._deserialize_token(d['class_name']),
                self._deserialize_node(d['access_node'])
            ),
            
            'NoteNode': lambda d: NoteNode(
                [self._deserialize_token(token) for token in d['note']]
            ),
            
            'VariableNode': lambda d: VariableNode(
                self._deserialize_token(d['variable_name']),
                self._deserialize_node(d['value_node'])
            ),
            
            'VariableFunctionNode': lambda d: VariableFunctionNode(
                self._deserialize_token(d['variable_name']),
                self._deserialize_node(d['value_node'])
            ),
            
            'VariableClassFunctionNode': lambda d: VariableClassFunctionNode(
                self._deserialize_token(d['variable_name']),
                self._deserialize_token(d['class_name']),
                self._deserialize_node(d['function'])
            ),
            
            'ArrayNode': lambda d: ArrayNode(
                self._deserialize_token(d['variable_name']),
                self._deserialize_node(d['value_node'])
            ),
            
            'DictNode': lambda d: DictNode(
                self._deserialize_token(d['variable_name']),
                d['dictionary']  # Dictionary should contain only basic types
            ),
            
            'ArrayAccessNode': lambda d: ArrayAccessNode(
                self._deserialize_token(d['variable_name']),
                self._deserialize_node(d['value_node']),
                self._deserialize_node(d['access_variable'])
            ),
            
            'ArrayArrangeNode': lambda d: ArrayArrangeNode(
                self._deserialize_token(d['variable_name']),
                self._deserialize_node(d['array']),
                d['type']
            ),
            
            'ClassAssignNode': lambda d: ClassAssignNode(
                Token(d['class_name'], None, None),
                Token(d['value_node'], None, None),
                [self._deserialize_node(var) for var in d['variables']]
            ),
            
            'RepeatNode': lambda d: RepeatNode(
                Token(d['range'], None, None),
                [self._deserialize_node(stmt) for stmt in d['body']]
            ),
            
            'ReturnNode': lambda d: ReturnNode(
                self._deserialize_token(d['token'])
            ),
            
            'ReturnExprNode': lambda d: ReturnExprNode(
                self._deserialize_node(d['token']),
                self._deserialize_token(d.get('pos_token'))
            ),
            
            'UpdateDictNode': lambda d: UpdateDictNode(
                self._deserialize_token(d['key']),
                self._deserialize_node(d['dict']),
                self._deserialize_node(d['expression'])
            ),
            
            'NumberNode': lambda d: NumberNode(
                self._deserialize_token(d['token'])
            ),
            
            'StopNode': lambda d: StopNode(
                self._deserialize_token(d['token']),
                d.get('string', '')
            ),
            
            'BoolNode': lambda d: BoolNode(
                self._deserialize_token(d['token'])
            ),
            
            'AccessDictNode': lambda d: AccessDictNode(
                self._deserialize_token(d['variable']),
                self._deserialize_token(d['key']),
                self._deserialize_node(d['dict'])
            ),
            
            'ArrayLengthNode': lambda d: ArrayLengthNode(
                self._deserialize_token(d['variable']),
                self._deserialize_node(d['expression'])
            ),
            
            'ShowMultiNode': lambda d: ShowMultiNode(
                d['string'],
                self._deserialize_token(d.get('lb')),
                self._deserialize_node(d['variable'])
            ),
            
            'UniaryOperatorNode': lambda d: UniaryOperatorNode(
                self._deserialize_token(d['token']),
                self._deserialize_node(d['node'])
            )
        }

        deserializer = deserializers.get(node_type)
        if deserializer:
            try:
                return deserializer(data)
            except Exception as e:
                print(f"Error deserializing {node_type}: {str(e)}")
                import traceback
                traceback.print_exc()
                return None

        print(f"No deserializer found for node type: {node_type}")
        return None

    def _deserialize_symbol_table(self, serialized_table):
        """Enhanced symbol table deserialization with support for all node types."""
        if serialized_table is None:
            return None

        from simplyLang.interpreter import SymbolTable, Number

        symbol_table = SymbolTable()
        for key, value_data in serialized_table.items():
            try:
                if value_data['type'] == 'Number':
                    symbol_table.set(key, Number(value_data['value']))
                elif value_data['type'] in ['int', 'float', 'str', 'bool']:
                    symbol_table.set(key, value_data['value'])
                else:
                    deserialized_node = self._deserialize_node(value_data)
                    if deserialized_node:
                        symbol_table.set(key, deserialized_node)
                    else:
                        print(f"Warning: Failed to deserialize node for key {key}")
            except Exception as e:
                print(f"Error deserializing symbol table entry {key}: {str(e)}")
                continue

        return symbol_table

    def _serialize_symbol_table(self, symbol_table):
        """Serialize symbol table with support for all node types."""
        if symbol_table is None:
            return None

        serialized = {}
        for key, value in symbol_table.symbols.items():
            if hasattr(value, 'value'):  # For Number objects
                serialized[key] = {
                    'type': value.__class__.__name__,
                    'value': value.value
                }
            elif isinstance(value, (int, float, str, bool)):  # For primitive types
                serialized[key] = {
                    'type': type(value).__name__,
                    'value': value
                }
            else:  # For custom nodes
                serialized[key] = self._serialize_node(value)
        return serialized

    def save_storage_state(self, storage_state):
        """Save the current contract storage state to Firebase and local backup."""
        try:
            serializable_state = {}
            for contract_name, data in storage_state.items():
                serializable_state[contract_name] = {
                    "contract_name": data["contract_name"],
                    "symbol_table": self._serialize_symbol_table(data["symbol_table"])
                }

            # Save to Firebase
            self.ref.set(serializable_state)

            # Save locally for backup
            with open(self.local_storage_path, 'w') as f:
                json.dump(serializable_state, f, indent=2)

            print("Contract storage state saved successfully")
            return True

        except Exception as e:
            print(f"Error saving contract storage state: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    def load_storage_state(self):
        """Load the contract storage state with enhanced error handling."""
        print("\n=== Starting load_storage_state ===")
        try:
            # Step 1: Try Firebase first
            print("\n--- Step 1: Loading from Firebase ---")
            storage_data = self.ref.get()
            print(f"Raw Firebase data: {repr(storage_data)}")

            # Step 2: Try local file if Firebase is empty
            if storage_data is None:
                print("\n--- Step 2: Loading from local file ---")
                try:
                    if not os.path.exists(self.local_storage_path):
                        print(f"Error: Local file does not exist at {self.local_storage_path}")
                        return {}

                    file_size = os.path.getsize(self.local_storage_path)
                    print(f"Local file size: {file_size} bytes")

                    with open(self.local_storage_path, 'r') as f:
                        raw_content = f.read()
                        print(f"Raw file content: {repr(raw_content)}")

                    try:
                        storage_data = json.loads(raw_content)
                        print(f"Parsed JSON data: {repr(storage_data)}")
                    except json.JSONDecodeError as je:
                        print(f"JSON parsing error: {je}")
                        print(f"Error at position: {je.pos}")
                        print(f"Line number: {je.lineno}")
                        print(f"Column number: {je.colno}")
                        return {}

                    if not isinstance(storage_data, dict):
                        print(f"Error: Loaded data is not a dictionary. Type: {type(storage_data)}")
                        return {}

                    self.ref.set(storage_data)
                    print("Local data synced to Firebase")

                except Exception as e:
                    print(f"Local file reading error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {}

            # Final validation and processing
            if not storage_data:
                print("Error: No data found in storage_data")
                return {}

            if not isinstance(storage_data, dict):
                print(f"Error: Final data is not a dictionary. Type: {type(storage_data)}")
                return {}

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

            return processed_data

        except Exception as e:
            print(f"Unexpected error in load_storage_state: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def initialize_contract_storage(self):
        """Initialize contract storage with default data."""
        contract_data = {
            "counter1": {
                "contract_name": "counter1",
                "symbol_table": None
            }
        }

        with open(self.local_storage_path, 'w') as f:
            json.dump(contract_data, f, indent=2)

        print("Contract data initialized successfully")

        with open(self.local_storage_path, 'r') as f:
            saved_data = json.load(f)
            print("\nVerifying saved data:")
            print(json.dumps(saved_data, indent=2))

    def broadcast_storage_state(self, nodes, storage_state):
        """Broadcast storage state to all known nodes."""
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
