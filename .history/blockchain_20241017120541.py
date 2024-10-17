import base64
import logging
from time import time
import threading
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve import PublicKey , Signature
from flask import request
from ellipticcurve.ecdsa import Ecdsa
from ellipticcurve.privateKey import PrivateKey , PublicKey 
import hashlib
import json
import time as t 
from typing import Dict
from urllib.parse import urlparse
import schedule

import ecdsa
import flask
import requests

from account_db import AccountReader
from nodeManager import NodeManager
from database import BlockchainDb

firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"

class Blockchain:


    def __init__(self):

        self.chain = []
        self.current_transactions = []
        self.hash_list = set()
        self.nodes = set()
        self.ttl = {}
        self.public_address = ""
        self.private_address = ""
        self.ip_address = ""
        self.target = 4  # Easy target value
        self.max_block_size = 1000000  
        self.max_mempool = 2
        self.new_block(proof=100, prev_hash=1)
        self.error = ""
        
        database = BlockchainDb()
        db_chain = database.load_blockchain(self)
        
        self.mining_thread = None
        self.should_mine = False
        
        accountDb = AccountReader()
        accountDb.load_accounts()
        accounts_data = accountDb.account_data
        for account in accounts_data:
            if account['publicKey']:
                self.public_key = account['publicKey']
            if account['privateKey']:
                self.private_address = account['privateKey']
                
        print("the db chain is : ", db_chain)
        if db_chain:
            self.chain = self.validate_loaded_chain()
        
        self.start_scheduled_mining()
    def Blockchain(self , public_address):
        self.public_address = public_address
    
    def create_coinbase_transaction(self, miner_address: str, reward: int = 50):
        """
        Creates a coinbase transaction for the miner.

        :param miner_address: <str> Address of the miner receiving the reward
        :param reward: <int> Amount of coins to reward the miner
        :return: <dict> The coinbase transaction
        """
        # Create the coinbase transaction structure
        coinbase_tx = {
       
                'sender': '0',  # Indicates it's a coinbase transaction
                'recipient': miner_address,
                'amount': reward,
                'timestamp': time(),
            
        }

        # Generate transaction ID
        coinbase_tx['transaction_id'] = self.generate_transaction_id(coinbase_tx)


        # Optionally set the public address and digital signature if needed
        # For the coinbase transaction, you may want to sign it with the miner's public key
        public_address = self.public_address # This should be set to the miner's public key

        
        digital_signature = self.sign_transaction(coinbase_tx)
        coinbase_tx["public_address"] = public_address
        
        transaction = {
            "transaction": coinbase_tx,
            "public_address": public_address,
            "digital_signature": digital_signature
        }

        return transaction
    def generate_transaction_id(self , coinbase_tx):
        transaction_data = json.dumps(coinbase_tx, sort_keys=True)
        return hashlib.sha256(transaction_data.encode()).hexdigest()
    
    def validate_loaded_chain(self):
        """Validate the loaded chain for integrity."""

        if len(self.chain) == 0:
            print("No chain found. Starting with a new chain.")
            return self.chain
        
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            if current_block['previous_hash'] != self.hash(previous_block):
                print("Loaded chain is valid. lenght is " + str(len(self.chain)))
                return self.chain[:i-1]
            if not self.valid_proof(previous_block['proof'], current_block['proof'] , self.target):
                print("Loaded chain is valid. lenght is " + str(len(self.chain)))
                return self.chain[:i-1]
        print("Loaded chain is valid. lenght is " + str(len(self.chain)))
        return self.chain    
    def create_mining_reward(self, miners_address, block_height):
        # Calculate the reward based on block height
        base_reward = 50  # Starting reward
        halving_interval = 210000  # Number of blocks between reward halvings
        halvings = block_height // halving_interval
        current_reward = base_reward / (2 ** halvings)

        # Add a transaction fee reward
        transaction_fees = sum(tx['transaction']['amount'] for tx in self.current_transactions if tx['transaction']['sender'] != "0")
        total_reward = current_reward + transaction_fees

        # Create the coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(
            miner_address=miners_address,
            reward=total_reward
        )

    # The coinbase transaction will be added as the first transaction in the new block
        return total_reward, coinbase_tx
    
    def register(self , ip_address):
            # Create a NodeManager instance
        node_manager = NodeManager()
        self.ip_address = ip_address
        # Get a random node
        random_node = node_manager.get_random_node()
        nodes = node_manager.load_nodes()
        print("the nodes are : ", nodes)
        print("the random node is : ", random_node)
        self.remove_expired_nodes()
        print("the ip address is : ", self.ip_address)
        print("nodes after removing expired nodes : ", nodes)

        if self.ip_address not in nodes:
            data = {
                    "nodes": [self.ip_address]
            }
            print("Registering node : {}".format(ip_address) )
            requests.post(f'http://{random_node}/nodes/register' , json=data)
            if self.ttl:
                requests.post(f'http://{random_node}/nodes/update_ttl' , json={
                    "updated_nodes": self.ttl,
                    "node" : self.ip_address
                })
        
        
        
    
    def register_node(self , address , current_address):
        """
        Adds a new node to the list of nodes

        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """
        
        #What is netloc?
        """
        `netloc` is an attribute of the `ParseResult` object returned by the `urlparse` function in Python's `urllib.parse` module.

        `netloc` contains the network location part of the URL, which includes:

        * The hostname or domain name
        * The port number (if specified)

        For example, if the URL is `http://example.com:8080/path`, `netloc` would be `example.com:8080`.

        In the context of the original code snippet, `netloc` is used to extract the node's network location (i.e., its hostname or IP address) from the URL.
        """
        self.remove_expired_nodes()

        parsed_url = urlparse(address)
        if parsed_url not  in self.nodes:
            self.nodes.add(parsed_url)
        current_url = urlparse(current_address)
        requests.post(f'http://{parsed_url}/nodes/update_chain' , json=[self.chain , current_url , list(self.hash_list) , list(self.nodes)])
        requests.post(f'http://{parsed_url}/nodes/update_nodes' , json={
            "nodes": list(self.nodes)
        })
        if self.ttl:
            requests.post(f'http://{parsed_url}/nodes/update_ttl' , json={
                    "updated_nodes": self.ttl,
                    "node" : current_url
                })
        
    def remove_expired_nodes(self):
        if self.ttl:
            # Iterate over a copy of the set to avoid modifying it while iterating
            for node in list(self.nodes):
                if node not in self.ttl:
                    self.nodes.remove(node)
                    continue
                if int(self.ttl[node]) < int(time()):
                    self.nodes.remove(node)

        
    def verify_block(self , block: Dict, previous_block: Dict, target: int, max_block_size: int , isCoinbase) -> bool:
        """
        Verify the validity of a block.

        :param block: The block to verify
        :param previous_block: The previous block in the chain
        :param target: The current mining difficulty target
        :param max_block_size: The maximum allowed block size in bytes
        :return: True if the block is valid, False otherwise
        """
        # Check block structure
        required_keys = ['index', 'timestamp', 'transactions', 'proof', 'previous_hash']
        if not all(key in block for key in required_keys):
            print("Invalid block structure")
            return False

        # Verify block header hash
        if self.valid_proof(previous_block['proof'], block['proof'], target) is False:
            print("Block hash does not meet the target difficulty")
            return False

        # Check timestamp
        current_time = int(time())
        if block['timestamp'] > current_time + 7200:  # 2 hours in the future
            print("Block timestamp is too far in the future")
            return False

        # Check block size
        block_size = len(str(block).encode())
        if block_size > max_block_size:
            print(f"Block size ({block_size} bytes) exceeds maximum allowed size ({max_block_size} bytes)")
            return False

        # Verify previous block hash
        if block['previous_hash'] != self.hash(previous_block):
            print("Previous block hash is incorrect")
            return False

        # Check that the first transaction is a coinbase transaction
        if not block['transactions'] or  block['transactions'][0]['transaction']['sender'] != "0":
            print("First transaction is not a coinbase transaction")
            return False

        # Verify all transactions in the block
        if not isCoinbase:
            for tx in block['transactions'][1:]:  # Skip the coinbase transaction
                if not self.valid_transaction(tx):
                    print(f"Invalid transaction found: {tx}")
                    return False

        return True

    def new_block(self , proof , prev_hash ,   isCoinbase = False ,coinbase_transaction=None , miner_address=None  ):
        
        # Creates a new Block in the Blockchain
        
        # :param proof: <int> The proof given by the Proof of Work algorithm
        # :param previous_hash: (Optional) <str> Hash of previous Block
        # :return: <dict> New Block


        block = {
            "index" : len(self.chain) + 1 ,
            "timestamp" : time(),
            "transactions" : [coinbase_transaction] +  self.current_transactions ,
            "proof" : proof,
            "previous_hash" : prev_hash or self.chain[len(self.chain) - 1]["hash"]
        }
    
        if self.chain and  not self.verify_block(block , self.chain[-1] , self.target , self.max_block_size , isCoinbase):
            print("Invalid block")
            return False

        

        self.chain.append(block)
        hashed_block = self.hash(block)
        self.hash_list.add(hashed_block)
        # Reset the current list of transactions
        self.remove_expired_nodes()

        #send data to the konwn nodes in the network
        for node in self.nodes:
            requests.post(f'http://{node}/nodes/update_block' , json=block)
            if self.ttl:
                requests.post(f'http://{node}/nodes/update_ttl' , json={
                    "updated_nodes": self.ttl,
                    "node" : miner_address
                })
        
        
        self.current_transactions = []
        return block
    
    
    

    def updateTTL(self, updated_nodes: dict, neighbor_node: str):
        """
        Remove nodes from ttl that have timed out and update TTLs for nodes.
        
        :param updated_nodes: A dictionary of nodes and their corresponding TTLs
        :type updated_nodes: dict
        :param neighbor_node: The node that transmitted the block
        :type neighbor_node: str
        """
        try:
            # Remove any protocol (http, https) from neighbor_node if it exists
            parsed_neighbor = urlparse(neighbor_node)
            neighbor_node_cleaned = parsed_neighbor or neighbor_node  # Use netloc if available, otherwise raw string
            
            print("Updating TTL for neighbor node...", neighbor_node_cleaned)
            if neighbor_node_cleaned in self.ttl:
                self.ttl[neighbor_node_cleaned] = self.ttl[neighbor_node_cleaned] + 600
                print(f"Updated TTL for neighbor_node '{neighbor_node_cleaned}' to {self.ttl[neighbor_node_cleaned]}")
            else:
                self.ttl[neighbor_node_cleaned] = time() + 600

            # Remove nodes with expired TTLs
            current_time = time()
            old_ttl_count = len(self.ttl)
            self.ttl = {node: ttl for node, ttl in self.ttl.items() if ttl >= current_time}
            print(f"Removed {old_ttl_count - len(self.ttl)} timed-out nodes.")

            # Update TTLs for nodes in updated_nodes
            for node, ttl in updated_nodes.items():
                parsed_node = urlparse(node)
                node_cleaned = parsed_node or node  # Remove protocol if present

                if node_cleaned in self.ttl:
                    old_ttl = self.ttl[node_cleaned]
                    self.ttl[node_cleaned] = max(self.ttl[node_cleaned], ttl)
                    print(f"Updated TTL for node '{node_cleaned}' from {old_ttl} to {self.ttl[node_cleaned]}")
                else:
                    self.ttl[node_cleaned] = ttl
                    print(f"Added node '{node_cleaned}' with TTL {ttl}")

            print(f"TTL update completed. Current TTL count: {len(self.ttl)}")

        except Exception as e:
            print(f"Error in updateTTL: {str(e)}")


    def new_transaction(self, transaction ,  public_address , digital_signature):
        try:
            print("senders key" , transaction["sender"])
            sender = PublicKey.fromCompressed(transaction["sender"])
        except:
            self.error = "Transaction will not be added to Block due to invalid sender address"
            return None, self.error
        try:
            recipient = PublicKey.fromCompressed(transaction["recipient"])
        except:
            self.error = "Transaction will not be added to Block due to invalid recipient address"
            return None, self.error
        
        if self.valid_transaction(transaction  , public_address , digital_signature) or sender == "0":
            self.current_transactions.append({
                "transaction": transaction,
                "public_address": public_address,
                "digital_signature": digital_signature
            })
            self.miner()
            # send transactions to the known nodes in the network
            self.remove_expired_nodes()
            for node in self.nodes:
                requests.post(f'http://{node}/nodes/update_transaction', json={
                "transaction": transaction,
                "public_address": public_address,
                "digital_signature": digital_signature
            })
            if self.ttl:
                requests.post(f'http://{node}/nodes/update_ttl' , json={
                    "updated_nodes": self.ttl,
                    "node" : request.host_url
                })
            return self.last_block['index'] + 1, "Successful Transaction"
        else:
            return None, self.error
            

    def start_scheduled_mining(self):
        print("the chain is " , self.chain)
        schedule.every(10).minutes.do(self.scheduled_mine)
        threading.Thread(target=self.run_schedule, daemon=True).start()

    def run_schedule(self):
        while True:
            schedule.run_pending()
            t.sleep(1)

    def scheduled_mine(self):
        if not self.mining_thread or not self.mining_thread.is_alive():
            self.should_mine = True
            self.mining_thread = threading.Thread(target=self.mine_with_timer)
            self.mining_thread.start()
    def mine(self):
        if not self.should_mine:
            return
        miners_address = "02b91a05153e9ba81b55e1ade91241bf17bfdc1b8f553b0aff35636ec6f7f5078a"
        last_block = self.last_block
        last_proof = last_block['proof']
        proof = self.proof_of_work(last_proof)
        block_height = len(self.chain)

        total_reward, coinbase_tx = self.create_mining_reward(miners_address, block_height)
        previous_hash = self.hash(last_block)
        self.new_block(proof, previous_hash, True, coinbase_tx)
        
    def mine_with_timer(self):
        start_time = time()
        self.mine()
        end_time = time()
        print(f"Mining took {end_time - start_time} seconds")
        self.should_mine = False


    def miner(self):
        if len(self.current_transactions) >= self.max_mempool or len(self.current_transactions) >= self.max_block_size:
            self.should_mine = True
            if not self.mining_thread or not self.mining_thread.is_alive():
                self.mining_thread = threading.Thread(target=self.mine_with_timer)
                self.mining_thread.start()
        
    def valid_transaction(self, transaction , public_address , digital_signature):
        # Verify the transaction signature
        if not self.verify_digital_signature(transaction , public_address , digital_signature): 
            self.error = "Transaction will not be added to Block due to invalid signature"
            return False

        # Check if the sender has enough coins
        sender_balance = self.check_balance(transaction)
        if sender_balance:
            return True
        else:
            self.error = "Transaction will not be added to Block due to insufficient funds"
            return False
    @staticmethod
    def hash(block):
        
        # Creates a SHA-256 hash of a Block
        
        # :param block: Block
        # :return: <str>
        
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    # def verify_signature(self, transaction , public_address , digital_signature):
    #     """
    #     Verify the digital signature of the transaction.
    #     """
    #     try:
    #         public_address = ecdsa.VerifyingKey.from_string(bytes.fromhex(public_address), curve=ecdsa.SECP256k1)
    #         transaction = transaction
    #         signature = bytes.fromhex(digital_signature)
            
    #         # Recreate the transaction data string that was signed
    #         transaction_string = json.dumps(transaction, sort_keys=True)
            
    #         public_address.verify(signature, transaction_string.encode())
    #         return True
    #     except (ecdsa.BadSignatureError, ValueError):
    #         return False
    




    def verify_digital_signature(self, transaction, compressed_public_key, digital_signature_base64):
        try:
            # Validate input types
            if not isinstance(transaction, dict):
                raise ValueError("Transaction must be a dictionary")
            if not isinstance(compressed_public_key, str):
                raise ValueError("Compressed public key must be a string")
            if not isinstance(digital_signature_base64, str):
                raise ValueError("Digital signature must be a base64-encoded string")

            # Validate transaction structure
            required_keys = ['sender', 'recipient', 'amount', 'timestamp']
            if not all(key in transaction for key in required_keys):
                raise ValueError("Transaction is missing required fields")

            # Convert transaction to JSON with sorted keys
            transaction_json = json.dumps(transaction, sort_keys=True)

            # Create PublicKey object
            try:
                print("Compressed public key: ", compressed_public_key)
                public_address = PublicKey.fromCompressed(compressed_public_key)
                print("public key: ", compressed_public_key)
            except ValueError as e:
                print("Invalid compressed public key: ", e)
                raise ValueError(f"Invalid compressed public key: {e}")

            # Create Signature object
            try:
                digital_signature = Signature.fromBase64(digital_signature_base64)
            except (ValueError, base64.binascii.Error) as e:
                raise ValueError(f"Invalid digital signature: {e}")
            print(
                f"Transaction: {transaction_json}\n"
                f"Public key: {public_address}\n"
                f"Digital signature: {digital_signature}"
            )
            # Verify the signature
            is_valid = Ecdsa.verify(transaction_json, digital_signature, public_address)

            if not is_valid:
                raise SignatureVerificationError("Signature verification failed")

            return True

        except ValueError as e:
            logging.error(f"Input validation error: {e}")
            return False
        except SignatureVerificationError as e:
            logging.error(f"Signature verification failed: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error in verify_digital_signature: {e}")
            return False

    def sign_transaction(self, transaction):
        message = json.dumps(transaction, sort_keys=True)
        private_key = PrivateKey.fromString(self.private_address)
        signature = Ecdsa.sign(message, private_key)
        return signature.toBase64()
    
    @property
    def last_block(self):
        
        """
        Returns the last block in the blockchain
        :return: <dict> The last block in the blockchain
        """
        
        return self.chain[-1]
    
    
    def proof_of_work(self , last_proof):
        
        # Finds a number p' such that hash(pp') contains 4 leading zeroes

        # :param last_proof: <int>
        # :return: <int> A number p'
        proof = 0
        while self.valid_proof(last_proof , proof , self.target) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, target):
        """
        Validates the Proof: Checks if hash(last_proof, proof) meets the target difficulty.
        
        :param last_proof: <int> Previous proof value
        :param proof: <int> Current proof value
        :param target: <int> The difficulty target (number of leading zeros required in the hash)
        :return: <bool> True if valid, False otherwise
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        
        # Check if the hash is valid by comparing to the target difficulty
        if guess_hash[:target] == '0' * target:
            return True  # The proof is valid (meets difficulty)
        return False  # The proof does not meet the difficulty
    


    def valid_chain(self , chain):
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'] , block['proof'] , self.target):
                return False
            last_block = block
            current_index += 1
        return True

    def check_balance(self , transaction):
    
        # Check if the sender has enough coins
        sender_balance = 0 
        sender_address = transaction['sender']
        sender_amount = transaction['amount']
        
        for block in self.chain:
            for transaction in block['transactions']:
                if transaction['transaction']['recipient'] == sender_address:
                    sender_balance += transaction['transaction']['amount']
                if transaction['transaction']['sender'] == sender_address:
                    sender_balance -= transaction['transaction']['amount']
                    
        for tx in self.current_transactions:
            if tx['transaction']['recipient'] == sender_address:
                sender_balance += tx['amount']
            if tx['transaction']['sender'] == sender_address:
                sender_balance -= tx['transaction']['amount']  
        if  sender_balance >= sender_amount:
            return True
        else:
            self.error =  "Transaction will not be added to Block due to insufficient funds"        
            return False


    def resolve_conflicts(self):

        # This is our Consensus Algorithm, it resolves conflicts
        
        # by replacing our chain with the longest one in the network.

        # :return: <bool> True if our chain was replaced, False if not
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

class SignatureVerificationError(Exception):
    pass
