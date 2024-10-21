import threading
import time
from urllib.parse import urlparse
from uuid import uuid4
from typing import List, Optional
import uvicorn
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from blockchain import Blockchain
from database import BlockchainDb
import atexit
import argparse

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the parser
parser = argparse.ArgumentParser(description="Run the Blockchain FastAPI App")
parser.add_argument('--url', type=str, required=True, help='Cloudflare Tunnel URL')
parser.add_argument('-p', '--port', type=int, default=5000, help='port to listen on')

# Parse the arguments
args = parser.parse_args()

# Get the Cloudflare Tunnel URL from command line argument
tunnel_url = args.url
if not tunnel_url:
    raise ValueError("--url argument is required")

blockchain = Blockchain()

# Pydantic models
class TransactionModel(BaseModel):
    transaction: dict
    digital_signature: str
    public_key: str

class NodesModel(BaseModel):
    nodes: List

class UpdateChainModel(BaseModel):
    chain : List
    hash_list : List
    
class UpdateNodesModel(BaseModel):
    updated_nodes: dict
    node: str

def register_node():
    print(f"Registering node with url {tunnel_url}...")
    blockchain.register(tunnel_url)

@app.get('/hello')
def hello():
    return {
        'nodes': list(blockchain.nodes),
        'length': len(list(blockchain.nodes))
    }

@app.get('/chain')
def chain():
    print("the length of the blockchain is " + str(len(blockchain.chain)))
    return {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }

@app.post('/transactions/new')
def new_transaction(transaction: TransactionModel):
    # Create a new Transaction
    index, error = blockchain.new_transaction(transaction.transaction, transaction.public_key, transaction.digital_signature)
    if index is not None:
        return {'message': f'Transaction will be added to Block {index}'}, 201
    else:
        raise HTTPException(status_code=400, detail=error)

@app.post('/nodes/register')
def register_nodes(nodes: NodesModel):
    for node in nodes.nodes:
        print("this is parent node", tunnel_url)
        blockchain.register_node(node, tunnel_url)

    return {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }, 201

@app.post('/nodes/update_nodes')
def update_nodes(nodes: NodesModel):
    for node in nodes.nodes:
        print("this is parent node", tunnel_url)
        if node not in blockchain.nodes:
            blockchain.nodes.add(node)

    return {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }, 201

@app.post('/nodes/update_ttl')
def update_ttl(update_data: UpdateNodesModel):
    blockchain.updateTTL(update_data.updated_nodes, update_data.node)
    return {
        'message': 'The TTL of nodes have been updated',
        'total_nodes': list(blockchain.nodes),
    }, 201

@app.get('/nodes/resolve')
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        return {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }, 200
    else:
        return {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }, 200

@app.post('/nodes/update_block')
def update_block(block: dict):
    print("this is block", block)
    if blockchain.hash(block) in blockchain.hash_list:
        return f"Already added Block in the network {block}", 200
    else:
        for transaction in block['transactions']:
            if transaction in blockchain.current_transactions:
                blockchain.current_transactions.remove(transaction)

        blockchain.chain.append(block)
        blockchain.hash_list.add(blockchain.hash(block))

        # send data to the known nodes in the network
        for node in blockchain.nodes:
            requests.post(f'http://{node}/nodes/update_block', json=block, timeout=5)
            requests.post(f'http://{node}/nodes/update_nodes', json={
                "nodes": list(blockchain.nodes)
            })

    return f"Added Block to the network {block}", 200

@app.post('/nodes/update_transaction')
def update_transaction(transaction: dict):
    if transaction.get('id') in [t.get('id') for t in blockchain.current_transactions]:
        return {"message": f"Transaction already in the network", "transaction": transaction}, 200

    blockchain.current_transactions.append(transaction)
    blockchain.miner()

    # Send data to the known nodes in the network
    failed_nodes = []
    for node in blockchain.nodes:
        try:
            response = requests.post(f'http://{node}/nodes/update_transaction', json=transaction, timeout=5)
            if response.status_code != 200:
                failed_nodes.append({"node": node, "reason": f"Non-200 status code: {response.status_code}"})
        except requests.exceptions.RequestException as e:
            failed_nodes.append({"node": node, "reason": str(e)})

    if failed_nodes:
        print(f"Failed to send transaction to some nodes: {failed_nodes}")

    return {
        "message": "Added transaction to the network",
        "transaction": transaction,
        "failed_nodes": failed_nodes
    }, 200

@app.post('/nodes/update_chain')
def update_chain(data: UpdateChainModel):
    print("this is request in update chain", data)
    chain_list = data.chain
    hash_list = data.hash_list
    blockchain.hash_list = set(hash_list)
    
    for chain in chain_list:
        if chain not in blockchain.chain:
            blockchain.chain.append(chain)

    return f"Added Chain to the network {chain_list} and nodes are {blockchain.nodes}", 200

@app.post('/delete_node')
def delete_chain(node_data: dict):
    blockchain.nodes.remove(node_data.get("node"))
    return "removed Node from the network", 200

def shutdown_session():
    database = BlockchainDb()
    
    database.save_blockchain(blockchain)
    if tunnel_url:
        for node in blockchain.nodes:
            try:
                requests.post(f'http://{node}/delete_node', json={"node": tunnel_url}, timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"Error notifying node {node}: {e}")
    print("FastAPI server is shutting down...")

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_session()

if __name__ == '__main__':
    threading.Thread(target=register_node, daemon=True).start()
    print(f"Cloudflare Tunnel URL: {tunnel_url}")
    print(f"Starting FastAPI Server on port {args.port}...")
    uvicorn.run(app, port=args.port)