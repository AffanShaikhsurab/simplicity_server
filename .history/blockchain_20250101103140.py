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
from requests.adapters import HTTPAdapter
import ecdsa
import flask
import requests
from urllib3 import Retry

from account_db import AccountReader
from contractStorage import ContractStorageDb
from nodeManager import NodeManager
from database import BlockchainDb
from simplyLang import lexer
from simplyLang import praser as Pr
from simplyLang import interpreter as Inter
from simplyLang.interpreter import InterpreterResult, Number, SymbolTable
from smartContract import ContractDeploymentTransaction, SmartContractTransaction

firebase_cred_path = "simplicity-coin-firebase-adminsdk-ghiek-54e4d6ed9d.json"

class Blockchain:


    def __init__(self):

        self.chain = []
        self.current_transactions = []
        #store smart-contract 
        self.smart_contract = [] 
        self.hash_list = set()
        self.nodes = set()
        self.ttl = {}
        self.storage_db = ContractStorageDb()
        self.storage = self.storage_db.load_storage_state() 
        self.public_address = ""
        self.private_address = ""
        self.ip_address = ""
        self.target = 4  # Easy target value
        self.max_block_size = 1000000  
        self.max_mempool = 0 # change this to 2 > 
        self.new_block(proof=100, prev_hash=1)
        self.error = ""        
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.database = BlockchainDb()
        db_chain = self.database.load_blockchain(self)
        
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
            print("the  db chain len is : ", len(self.chain))
            isValid = self.valid_chain(self.chain)
            if isValid:
                print("the  finall chain is : ", len(self.chain))
        
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
    def send_money(self, sender: str, reciever ,  amount: int):
        """
        Creates a coinbase transaction for the miner.

        :param miner_address: <str> Address of the miner receiving the reward
        :param reward: <int> Amount of coins to reward the miner
        :return: <dict> The coinbase transaction
        """
        print("checking balance ")
        isBalance  , error = self.check_balance(
            {
       
                'sender': sender,  # Indicates it's a coinbase transaction
                'recipient': reciever,
                'amount': amount,
            
        }
        )
        print("isBalance " , isBalance)
        if  isBalance == False :
            return False , error
        if isBalance:
            # Create the coinbase transaction structure
            print("creating coinbase transaction ")
            coinbase_tx = {
        
                    'sender': sender,  # Indicates it's a coinbase transaction
                    'recipient': reciever,
                    'amount': amount,
                    'timestamp': time(),
                
            }

            # Generate transaction ID
            coinbase_tx['transaction_id'] = self.generate_transaction_id(coinbase_tx)

            
            # Optionally set the public address and digital signature if needed
            # For the coinbase transaction, you may want to sign it with the miner's public key
            public_address = self.public_address # This should be set to the miner's public key
            print("public address is " , public_address)
            
            digital_signature = self.sign_transaction(coinbase_tx)
            coinbase_tx["public_address"] = public_address
            print("creating trnasction ")
            transaction = {
                "transaction": coinbase_tx,
                "public_address": public_address,
                "digital_signature": digital_signature
            }
            self.current_transactions.append(
                transaction
            )

            return transaction , None
        else:
            return False , "Not enough balance"
    def generate_transaction_id(self , coinbase_tx):
        transaction_data = json.dumps(coinbase_tx, sort_keys=True)
        return hashlib.sha256(transaction_data.encode()).hexdigest()
    
    def validate_loaded_chain(self):
        """Validate the loaded chain for integrity."""

        if len(self.chain) <= 2 :
            print("No chain found. Starting with a new chain.")
            return self.chain
        print(
            "Length of the chain is " + str(len(self.chain))
        )
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            if current_block['previous_hash'] != self.hash(previous_block):
                print("Loaded chain is valid. lenght is " + str(len(self.chain)))
                self.database.save_valid_chain(self.chain[:i-1] )
                return self.chain[:i-1]
            if not self.valid_proof(previous_block['proof'], current_block['proof'] , self.target):
                print("Loaded chain is valid. lenght is " + str(len(self.chain)))
                self.database.save_valid_chain(self.chain[:i-1] )
                return self.chain[:i-1]
        print("Loaded chain is valid. lenght is " + str(len(self.chain)))
        return self.chain    
    def create_mining_reward(self, miners_address, block_height):
        """
        Calculate and create mining reward including transaction fees.
        
        Args:
            miners_address (str): Address to receive the reward
            block_height (int): Current block height
        
        Returns:
            tuple: (total_reward, coinbase_transaction)
        """
        # Calculate the base reward based on block height
        base_reward = 50  # Starting reward
        halving_interval = 210000  # Number of blocks between reward halvings
        halvings = block_height // halving_interval
        current_reward = base_reward / (2 ** halvings)

        # Calculate transaction fees only from regular transactions that have an amount
        transaction_fees = 0
        for tx in self.current_transactions:
            # Skip coinbase transactions
            if tx['transaction']['sender'] == "0":
                continue
                
            # Only include amount if it exists (regular transactions)
            if 'amount' in tx['transaction']:
                transaction_fees += tx['transaction']['amount']

        # Calculate total reward
        total_reward = current_reward + transaction_fees

        # Create the coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(
            miner_address=miners_address,
            reward=total_reward
        )

        return total_reward, coinbase_tx
    def addUrl(self, url : str ):
        if "simplicity" in url :
            if not url.endswith(".onrender.com"):
                url = url + ".onrender.com"
        else:
            url = url + ".trycloudflare.com"
        return url
    
    
    def cleanUrl(self , url : str ):
        removed_https = url.replace("https://","")
        removed_dot = removed_https.split(".")[0]
        return removed_dot
                
    def register_node(self , neighbor_url , current_address):
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

        # parsed_url = urlparse(address) testing
        if neighbor_url not in self.nodes:
            self.nodes.add(neighbor_url)
        
        # clean the url
        current_url = self.cleanUrl(current_address)
        
        # add .onrender.com or .trycloudflare.com
        neighbor_url = self.addUrl(neighbor_url)
        
        requests.post(f'http://{neighbor_url}/nodes/update_chain' , json={
            "chain": self.chain  , "hash_list" : list(self.hash_list)
            })
        requests.post(f'http://{neighbor_url}/nodes/update_nodes' , json={
            "nodes": list(self.nodes)
        })
        if self.ttl:
            requests.post(f'http://{neighbor_url}/nodes/update_ttl' , json={
                    "updated_nodes": self.ttl,
                    "node" : current_url
                })
        
    
    # def _update_node(self, base_url, current_netloc):
    #     try:
    #         self.session.post(f'{base_url}/nodes/update_chain', 
    #                           json=[self.chain, current_netloc, list(self.hash_list), list(self.nodes)],
    #                           timeout=5)
            
            
    #         self.session.post(f'{base_url}/nodes/update_nodes', 
    #                           json={"nodes": list(self.nodes)},
    #                           timeout=5)
            
    #         if self.ttl:
    #             self.session.post(f'{base_url}/nodes/update_ttl', 
    #                               json={"updated_nodes": self.ttl, "node": current_netloc},
    #                               timeout=5)
            
    #         print(f"Successfully updated node: {base_url}")
    #     except requests.RequestException as e:
    #         print(f"Error communicating with node {base_url}: {e}")

    def remove_expired_nodes(self):
        primary_node = [
            "simplicity-server1",
            "simplicity-server"
        ]
        if self.ttl:
            # Iterate over a copy of the set to avoid modifying it while iterating
            for node in list(self.nodes):
                if node in primary_node:
                    continue
                
                if node not in self.ttl:
                    self.nodes.remove(node)
                    continue
                if self.ttl[node] < time():
                    self.nodes.remove(node)
                    #also remove from ttl
                    self.ttl.pop(node)

        
        
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
                if  'code' in tx['transaction']:
                    if not self.valid_transaction(tx['transaction'] , tx['public_address'], tx['digital_signature']):
                        print(f"Invalid transaction found: {tx}")
                        return False

                else:
                    if not self.valid_transaction(tx['transaction'] , tx['public_address'], tx['digital_signature']):
                        print(f"Invalid transaction found: {tx}")
                        return False

        return True
    def retrieve_contract_code(self, contract_name):
        for block in self.chain:
            for tx in block['transactions']:
                if 'contract_name' in tx['transaction'] and tx['transaction']['transaction_id'] == contract_name and 'code' in tx['transaction'] :
                    print(tx['transaction'])
                    return  tx['transaction']['code']
        return None

    def execute_contract(self , transaction ,  public_address, digital_signature):
        res = InterpreterResult()
        try:
            is_trasnfer = False
            print("executing cintract ")
            contract_code = self.retrieve_contract_code(transaction['contract_address'])
            contract_name = transaction['contract_address']
            if not contract_code:
                return None , "Smart contract not found in blockchain"
            print("retreving the contract " ,contract_name)

            tokens , error = lexer.Lex(contract_code , "<contract>").create_token()
            if error :
                return  None , error.print()
            print("contract code is " , contract_code)
            
            print("tokens are " , tokens)
            praserObj  = Pr
            praser = praserObj.Praser(tokens)
            ast = praser.parse()
            # print("AST : " ,  praserObj.print_ast(
            #     ast.node
            # ))
            contract = praser.contract_name
            self.public_address = public_address
            if ast.error:
                return  None , ast.error.print()
            # interpreter = Inter.Interpreter()
            # context = Inter.Context("<contract>")
            contract_symbol_table = None
            state = self.storage

            print("state is", self.storage)

            if contract_name in state:
                print("contract name is", state[contract_name]["contract_name"])

                if "symbol_table" in state[contract_name]:
                    print("symbol table is", state[contract_name]["symbol_table"])

                    if state[contract_name]["symbol_table"] is not None:
                        contract_symbol_table : SymbolTable = state[contract_name]["symbol_table"]
                        print(contract_symbol_table.get("count"))
                    else:
                        print(f"'symbol_table' key is missing in state[{contract_name}]")
                        # Initialize a new SymbolTable if the symbol_table is None
                        contract_symbol_table = Inter.SymbolTable()
                        contract_symbol_table.set("NULL", Number(0))
                else:
                    print(f"'symbol_table' key is missing in state[{contract_name}]")
                    # Handle the case where "symbol_table" is missing
                    contract_symbol_table = Inter.SymbolTable()
                    contract_symbol_table.set("NULL", Number(0))
            else:
                print(f"'{contract_name}' is not present in the state")
                # Handle the case where the contract_name is not found in state
                contract_symbol_table = Inter.SymbolTable()
                contract_symbol_table.set("NULL", Number(0))

            print("contract symbol is " , contract_symbol_table)
            parameters = {
                
            }
            if 'parameters' in transaction:
                for key, value in transaction['parameters'].items():
                    parameters[key] = value

                    print(f"Setting param with key: {key} and value: {value}")
                    # try:
                    #     value = contract_symbol_table.get(key)
                    #     print("value stored is " , value)
                    #     if not value :
                    #         print("value updating is " , key ,  value)
                    #         contract_symbol_table.set(key, value)
                    # except:
                    #     print("value updating is " , key , value)

                    #     contract_symbol_table.set(key, value)
            print("Contract Node is " , ast.node)        
            print("contract symbol table is " , contract_symbol_table)   
            interpreter = Inter.Interpreter()
            context = Inter.Context("<contract>")
            context.symbol_table = contract_symbol_table
            interpreter.visit(ast.node, context , [context.symbol_table])
            print("callContractNode is " , contract_name , parameters )

            print("calling contract node.......... ")
            interpreter.blockchain = self
            interpreter.address = transaction["sender"]
            function = transaction["function"]
            print("function is " , function)
            result  = res.register(  interpreter.visit_CallContractNode(
                
                Pr.CallContractNode(
                    contract , 
                     parameters 
                ),
                function ,
            context , [context.symbol_table]))
            
            if res.error:
                print("error is " , res.error)
                if type(res.error ) != str:
                    return None , res.error.print()
                else:
                    return None , res.error
        
            
            print("returning value " , result)    
            if type(result) is dict and "node_amount" in result:
                # Ensure 'self_address' is properly defined or retrieved
                self_address = result.get("self_address")
                node_address = result.get("node_address")
                node_amount = result.get("node_amount")

                if not self_address or not node_address or not node_amount:
                    raise ValueError("Invalid transfer details provided.")
                print("sending money")
                # Call the `send_money` function
                result = self.send_money(self_address, node_address, node_amount)
                
            # print("result is " , result)  
            # print("result.error" , result.error)
            
            # if result.error:
            #     try:
            #         print(result.error)
            #         return  None , result.error.print()

            #     except:   
            #         print("error is " , result.error.print())
            #         return  None , result.error.print()
            print("stroing the state" , state)
            if contract_name not in state:
                state[contract_name] = {
                    "contract_name": contract_name,
                    "symbol_table": None
                }
            print("storing....." , context.symbol_table)    
            state[contract_name]["symbol_table"] = context.symbol_table
            #creating a transaction for contract call                 
            contract_transaction = SmartContractTransaction(transaction['sender'] , transaction['contract_name'] , transaction.get('parameters', None) ,public_address , digital_signature)
            self.current_transactions.append({
                        "transaction": contract_transaction.to_dict(),
                        "public_address": public_address,
                        "digital_signature": digital_signature
                    })
            #calcuting the cost of the transaction for saving the state
            cost = self.storage_db.calculate_storage_cost(state)
            
            balance = self.check_balance(public_address)
            
            if cost > balance:
                return None , "Insufficient balance to cover storage cost."
            
            # Save and broadcast the updated storage state
            self.storage_db.save_storage_state(state)
            self.storage_db.broadcast_storage_state(self.nodes, state)
            
            self.send_money(
                public_address ,
                
            )
            try:
                print("returning value " , result.value)
                
                return result.value , None
            except:
                return result , None

        except Exception as e:
            return None , f"Error in  executing the contract : {str(e)}"
    def new_block(self, proof, prev_hash, isCoinbase=False, coinbase_transaction=None, miner_address=None):
        """
        Creates a new block in the blockchain.

        :param proof: <int> The proof provided by the Proof of Work algorithm.
        :param prev_hash: (Optional) <str> Hash of the previous block in the chain. If not provided, defaults to the last block's hash.
        :param isCoinbase: (Optional) <bool> Flag to indicate if this block contains a coinbase transaction (reward for mining).
        :param coinbase_transaction: (Optional) <dict> Coinbase transaction details (usually the miner's reward).
        :param miner_address: (Optional) <str> The address of the miner who found the proof of work.
        :return: <dict> The newly created block.
        """

        # Debugging: Print proof and previous hash
        print(f"Creating new block with proof: {proof} and previous hash: {prev_hash}")
        
        print("Current transactions Before combining: ", self.current_transactions)
    # Store current transactions including contract transactions
        transactions = []
        if coinbase_transaction:
            transactions.append(coinbase_transaction)
        
        # Add all pending transactions including contract transactions
        transactions.extend(self.current_transactions)
        
        print("Current transactions: ", transactions)
        # Constructing the block with necessary details
        block = {
            "index": len(self.chain) + 1,  # Index of the new block
            "timestamp": time(),  # Current timestamp
            "transactions": transactions or [],  # Coinbase transaction and others
            "proof": proof,  # The proof of work value
            "previous_hash": prev_hash or self.chain[len(self.chain) - 1]["hash"]  # Previous block's hash
        }

        # Debugging: Print the block before verification
        print(f"Block before verification: {block}")
        
        # Validating the newly created block before adding it to the chain
        if self.chain and not self.verify_block(block, self.chain[-1], self.target, self.max_block_size, isCoinbase):
            print("Invalid block")  # Debugging: Print if block validation fails
            return False  # Abort block creation if validation fails

        # If the block is valid, add it to the blockchain
        self.chain.append(block)

        # Debugging: Print the block after adding to chain
        print(f"Block added to chain: {block}")
        
        # Hash the block and add it to the list of known hashes
        hashed_block = self.hash(block)
        self.hash_list.add(hashed_block)

        # Debugging: Print the hashed block
        print(f"Hashed block: {hashed_block}")
        
        print(f"Broadcasting to nodes: {list(self.nodes)}\nBroadcasting to nodes")
        # Reset the current list of transactions since they've been included in the block
        self.remove_expired_nodes()
        # Debugging: Print the list of nodes before broadcasting
        print(f"Broadcasting to nodes: {list(self.nodes)}\nBroadcasting to nodes")

        for node , ttl in self.ttl.items():
            if ttl > time():
                self.nodes.add(node)
        
        # Broadcast the new block to all known nodes in the network
        for node in self.nodes:
            
            node = self.addUrl(node)
            
            # Send the new block data to the node
            print(f"Sending block to node: {f'https://{node}/nodes/update_block'} wiht data {block}")  # Debugging: Print node being sent to
            response = requests.post(f'http://{node}/nodes/update_block', json=block)
            print(
                f"Response status code: {response.status_code}\n"
                f"Response content: {response.content}\n"
                f"Response headers: {response.headers}"
            )
            # If TTL exists, broadcast the updated TTL and miner information
            if self.ttl:
                print(f"Updating TTL for node: {node} with miner address: {miner_address}")  # Debugging: Print TTL update info
                requests.post(f'http://{node}/nodes/update_ttl', json={
                    "updated_nodes": self.ttl,
                    "node": self.ip_address
                })
        
        # Clear the list of transactions for the next block
        self.current_transactions = []
        
        # Debugging: Print confirmation of transaction reset
        print("Transactions reset after block creation.")
        
        # Return the new block as the result
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
            # Helper function to clean and normalize node strings
            def clean_node(node):
                if isinstance(node, str):
                    parsed = urlparse(node)
                    netloc = parsed.netloc or parsed.path
                    # Remove .trycloudflare.com suffix if present
                    netloc = netloc.replace('.trycloudflare.com', '')
                    # Remove port if present
                    netloc = netloc.split(':')[0]
                    
                    # Remove .render.com suffix if present
                    if netloc.endswith('.onrender.com'):
                        netloc = netloc.replace('.onrender.com', '')
                    # Remove local URLs
                    if netloc in ['localhost', '127.0.0.1'] or netloc.startswith('192.168.') or netloc.startswith('10.'):
                        return None
                    return netloc
                return None  # Return None for non-string objects
            #add node and coressponding ttl if not exsists already
            print(f"Current TTL count: {len(self.ttl)}")
            if self.ttl == "":
                self.ttl = {}
            for node, ttl in updated_nodes.items():
                node_cleaned = clean_node(node)
                if node_cleaned not in self.ttl:
                    self.ttl[node_cleaned] = ttl
                if node_cleaned not in self.nodes:
                    self.nodes.add(node_cleaned)

            print(f"Updated TTL count: {len(self.ttl)}")
            
            # Clean the neighbor_node
            neighbor_node_cleaned = clean_node(neighbor_node)
            current_time = 0
            if neighbor_node_cleaned:
                print(f"Updating TTL for neighbor node: {neighbor_node_cleaned}")
                current_time = time()

                # Update TTL for the neighbor node
                self.ttl[neighbor_node_cleaned] = current_time + 600

            # Remove nodes with expired TTLs and clean existing keys
            new_ttl = {}
            for node, ttl in self.ttl.items():
                cleaned_node = clean_node(node)
                if cleaned_node and ttl >= current_time:
                    new_ttl[cleaned_node] = ttl
            self.ttl = new_ttl

            # Update TTLs for nodes in updated_nodes
            for node, ttl in updated_nodes.items():
                node_cleaned = clean_node(node)
                if node_cleaned:
                    self.ttl[node_cleaned] = max(self.ttl.get(node_cleaned, 0), ttl)

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
        if 'contract_name' not in transaction:
            try:
                recipient = PublicKey.fromCompressed(transaction["recipient"])
            except:
                self.error = "Transaction will not be added to Block due to invalid recipient address"
                return None, self.error
        print("analyzing the transaction")    
        if self.valid_transaction(transaction  , public_address , digital_signature) :
            print("the transaction is valid")
            if 'contract_name' in transaction and 'code' in transaction :
                print("adding contract to the blockchain")
                contract_transaction = ContractDeploymentTransaction(transaction['sender'] , transaction['contract_name'] , transaction.get('code') , public_address , digital_signature)

                self.current_transactions.append({
                    "transaction": contract_transaction.to_dict(),
                    "public_address": public_address,
                    "digital_signature": digital_signature
                })
                
                print("contract added : " , str(contract_transaction.to_dict()))
                self.storage[contract_transaction.transaction_id] = {
                    "contract_name": contract_transaction.transaction_id,
                    "symbol_table": None
                }
                
                self.storage_db.save_storage_state(self.storage)
            elif 'contract_name' in transaction:
                contract_transaction = SmartContractTransaction(transaction['sender'] , transaction['contract_name'] , transaction.get('parameters', None) ,public_address , digital_signature)
                self.current_transactions.append({
                        "transaction": contract_transaction.to_dict(),
                        "public_address": public_address,
                        "digital_signature": digital_signature
                    })
           
            else:
                self.current_transactions.append({
                    "transaction": transaction,
                    "public_address": public_address,
                    "digital_signature": digital_signature
                })
            
            print("Current transactions after transaction added: ", self.current_transactions)

            self.miner()
                # send transactions to the known nodes in the network
            self.remove_expired_nodes()
                
            self.storage_db.save_storage_state(
                self.storage
            )
            self.database.save_blockchain(
                self
            )
            self.database.save_to_firebase()
            self.transmit_transaction(
                transaction , public_address , digital_signature
            )
            
            return contract_transaction.transaction_id, "Successful Transaction"
        else:
            return None, self.error
    
    async def transmit_transaction(self , transaction , public_address , digital_signature):
        for node in self.nodes:
                node = self.addUrl(node)
                requests.post(f'http://{node}/nodes/update_transaction', json={
                "transaction": transaction,
                "public_address": public_address,
                "digital_signature": digital_signature
            })
            
                if self.ttl:
                    requests.post(f'http://{node}/nodes/update_ttl' , json={
                        "updated_nodes": self.ttl,
                        "node" : self.ip_address
                    })    
    def start_scheduled_mining(self):
        schedule.every(30).minutes.do(self.scheduled_mine)
        threading.Thread(target=self.run_schedule, daemon=True).start()

    def run_schedule(self):
        while True:
            schedule.run_pending()
            t.sleep(1)

    def scheduled_mine(self):
        if not self.mining_thread or not self.mining_thread.is_alive():
            print("started mining -----")
            self.should_mine = True
            self.mining_thread = threading.Thread(target=self.mine_with_timer)
            self.mining_thread.start()
    def mine(self):
        if not self.should_mine:
            return
        miners_address = self.public_key
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
        if "contract_name" not in transaction:
 
            sender_balance = self.check_balance(transaction)
            if sender_balance:
                return True
            else:
                self.error = "Transaction will not be added to Block due to insufficient funds"
                return False
        return True
    @staticmethod
    def hash(block):
        
        # Creates a SHA-256 hash of a Block
        
        # :param block: Block
        # :return: <str>
        
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    def verify_digital_signature(self, transaction, compressed_public_key, digital_signature_base64):
        try:
            # Validate input types
            if not isinstance(transaction, dict):
                raise ValueError("Transaction must be a dictionary")
            if not isinstance(compressed_public_key, str):
                raise ValueError("Compressed public key must be a string")
            if not isinstance(digital_signature_base64, str):
                raise ValueError("Digital signature must be a base64-encoded string")
            
            if "contract_name" not in transaction:
            # Validate transaction structure
                required_keys = ['sender', 'recipient', 'amount', 'timestamp']
                if not all(key in transaction for key in required_keys):
                    raise ValueError("Transaction is missing required fields")
            else:
                required_keys = ['sender',  'timestamp']
                if not all(key in transaction for key in required_keys):
                    raise ValueError("Transaction is missing required fields" , transaction)             

            if "digital_signature" in transaction:
                transaction.pop("digital_signature")
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
            raise
        except SignatureVerificationError as e:
            logging.error(f"Signature verification failed: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in verify_digital_signature: {e}")
            raise

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
        print(f"Sender address: {sender_address} , Sender amount: {sender_amount}")
        
        for block in self.chain:
            for transaction in block['transactions']:
                if "recipient" in transaction["transaction"]:
                    if transaction['transaction']['recipient'] == sender_address:
                        sender_balance += transaction['transaction']['amount']
                        print(f"Sender balance: {sender_balance}")
                if "sender" in transaction['transaction']:
                    if transaction['transaction']['sender'] == sender_address:
                        sender_balance -= transaction['transaction']['amount']
                        print(f"Sender balance: {sender_balance}")
                    
        for tx in self.current_transactions:
            if "recipient" in transaction["transaction"]:

                if tx['transaction']['recipient'] == sender_address:
                    sender_balance += tx['amount']
            if "sender" in transaction['transaction']:
                if tx['transaction']['sender'] == sender_address:
                    sender_balance -= tx['transaction']['amount'] 
                 
        print(f"Sender balance: {sender_balance}")
        if  sender_balance >= sender_amount:
            return True ,None
        else:
            self.error =  "Transaction will not be added to Block due to insufficient funds"        
            return False , self.error


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
