import random
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"
database_url = "https://simplicity-coin-default-rtdb.firebaseio.com/"
class NodeManager:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
        self.ref = db.reference('nodes')
        self.nodes = self.load_nodes()

    def load_nodes(self):
        """
        Load nodes from Firebase and return the list of nodes.
        """
        nodes = self.ref.get()
        if nodes:
            return list(nodes.values())
        else:
            print("No nodes found in Firebase")
            return []

    def get_random_node(self):
        """
        Get a random node from the list of loaded nodes.
        """
        if self.nodes:
            return random.choice(self.nodes)
        else:
            print("No nodes available.")
            return None

    def add_node(self, node):
        """
        Add a new node to Firebase.
        """
        new_node_ref = self.ref.push()
        new_node_ref.set(node)
        self.nodes.append(node)
        print(f"Node added to Firebase: {node}")
