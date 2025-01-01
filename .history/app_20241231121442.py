import threading
import time
from urllib.parse import urlparse
from uuid import uuid4
import flask
import requests
from blockchain import Blockchain
from contractStorage import ContractStorageDb
from database import BlockchainDb
from flask_cors import CORS  # Import CORS
import atexit

app = flask.Flask(__name__)
from flask import Flask, copy_current_request_context, g, request, jsonify

# Enable CORS for the entire Flask app
CORS(app)

blockchain = Blockchain()
should_continue = True


def periodic_save():
    """Background task to save blockchain data every 10 minutes"""
    while should_continue:
        time.sleep(600)  # Sleep for 10 minutes
        if should_continue:  # Check again after sleep
            try:
                database = BlockchainDb()
                database.save_blockchain(blockchain)
                database.save_to_firebase()
                print("Blockchain auto-saved to Firebase")
            except Exception as e:
                print(f"Error during auto-save: {str(e)}")
                
# Start the background save thread
save_thread = threading.Thread(target=periodic_save, daemon=True)
save_thread.start()



@app.route('/hello', methods=['GET'])
def hello():
    """Get all nodes in the network. This endpoint is useful for auto-discovery of nodes."""
    
    return flask.jsonify({
        'nodes': list(blockchain.nodes),
        'length': len(list(blockchain.nodes))
    })


@app.route('/chain', methods=['GET'])
def chain():
    print("the length of the blockchain is " + str(len(blockchain.chain)))
    return flask.jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    })


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = flask.request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['transaction', 'digital_signature', 'public_key']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index, error = blockchain.new_transaction(values['transaction'], values['public_key'], values['digital_signature'])
    if index is not None:
        response = {'message': f'Transaction will be added to Block {index}'}
    else:
        response = {'message': error}
    return flask.jsonify(response), 201


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = flask.request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        print("this is parent node","https://simplicity-server1.onrender.com")
        blockchain.register_node(node,"https://simplicity-server1.onrender.com")

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return flask.jsonify(response), 201

@app.route('/contracts/call', methods=['POST'])
def call_contract():
    values = flask.request.get_json()

    required_fields = ['sender', 'contract_name', 'digital_signature', 'public_key', 'timestamp' , 'function']
    missing_fields = [field for field in required_fields if field not in values]
    if missing_fields:
        return jsonify({
            "success": False,
            "message": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    parameters = values.get('parameters', None)
    transaction = {
        "sender": values['sender'],
        "contract_name": values['contract_name'],
        "parameters": parameters,
        "timestamp": values["timestamp"],
        "public_key": values['public_key'],
        "function": values['function']
    }

    result, error = blockchain.execute_contract(
        transaction, values['public_key'], values['digital_signature']
    )
    
    # Ensure `index` is serializable
    if result is not None:
        result = str(result)  # Fallback: convert to string

        return jsonify({
            "success": True,
            "message": "Contract executed successfully",
            "value": result
        }), 200

    # Ensure `error` is serializable
    if error is not None and not isinstance(error, (str, list, dict)):
        error = str(error)

    return jsonify({
        "success": False,
        "message": "Failed to execute contract",
        "error": error
    }), 400



@app.route('/contracts/new', methods=['POST'])
def new_contract():
    values = flask.request.get_json()
    if 'code' not in values or  'public_key' not in values or 'digital_signature' not in values or 'sender' not in values or 'contract_name' not in values:
        return 'Missing values', 400
    # parse the contract code using interpreter
    transaction = {
        "sender": values["sender"],
        "contract_name" : values["contract_name"],
        "code" : values['code'],
        "public_key" : values['public_key'],
        "digital_signature" : values['digital_signature'],
        "timestamp" : values["timestamp"]
    }
    
    index, error = blockchain.new_transaction(transaction, values['public_key'], values['digital_signature'])
    if index is not None:
        response = {'message': f'Contract address is {index}'}
    else:
        response = {'message': error}
    return flask.jsonify(response), 201

@app.route('/nodes/update_nodes', methods=['POST'])
def update_nodes():
    values = flask.request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        print("this is parent node","https://simplicity-server1.onrender.com")
        if node not in blockchain.nodes:
            blockchain.nodes.add(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return flask.jsonify(response), 201

@app.route('/nodes/update_ttl', methods=['POST'])
def update_ttl():
    values = flask.request.get_json()
    print(values)
    update_nodes = values.get('updated_nodes')
    print("this is the updated nodes in the request", update_nodes)
    node = values.get('node')
    if update_nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    blockchain.updateTTL(update_nodes , node )
    response = {
        'message': 'The TTL of nodes have been updated',
        'total_nodes': list(blockchain.nodes),
    }
    return flask.jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return flask.jsonify(response), 200

@app.route('/nodes/update_storage', methods=['POST'])
def update_storage():
    values = request.get_json()
    
    if not values:
        return 'Missing values', 400
        
    storage_state = values.get('storage_state')
    if not storage_state:
        return 'Missing storage state', 400
        
    blockchain.storage = storage_state
    blockchain.storage_db.save_storage_state(storage_state)
    
    return 'Storage state updated successfully', 200
@app.route('/nodes/update_block', methods=['POST'])
def update_block():
    block = flask.request.get_json()
    print("this is block", block)
    if blockchain.hash(block) in blockchain.hash_list:
        return flask.jsonify(f" Already added Block in the network {block}"), 200
    else:
        for transaction in block ['transactions']:
            if transaction in blockchain.current_transactions:
                blockchain.current_transactions.remove(transaction)

        blockchain.chain.append(block)
        blockchain.hash_list.add(blockchain.hash(block))
        # send data to the known nodes in the network
        for node in blockchain.nodes:
            node = blockchain.addUrl(node)

            requests.post(f'http://{node}/nodes/update_block', json=block, timeout=5)
            requests.post(f'http://{node}/nodes/update_nodes', json={
                "nodes": list(blockchain.nodes)
            })

    return flask.jsonify(f"Added Block to the network {block}"), 200


@app.route('/nodes/update_transaction', methods=['POST'])
def update_transaction():
    transaction = flask.request.get_json()

    if transaction.get('id') in [t.get('id') for t in blockchain.current_transactions]:
        return flask.jsonify({"message": f"Transaction already in the network", "transaction": transaction}), 200

    blockchain.current_transactions.append(transaction)
    blockchain.miner()

    # Send data to the known nodes in the network
    failed_nodes = []
    for node in blockchain.nodes:
        node = blockchain.addUrl(node)

        try:
            response = requests.post(f'http://{node}/nodes/update_transaction', json=transaction, timeout=5)
            if response.status_code != 200:
                failed_nodes.append({"node": node, "reason": f"Non-200 status code: {response.status_code}"})
        except requests.exceptions.RequestException as e:
            failed_nodes.append({"node": node, "reason": str(e)})

    if failed_nodes:
        app.logger.warning(f"Failed to send transaction to some nodes: {failed_nodes}")

    return flask.jsonify({
        "message": "Added transaction to the network",
        "transaction": transaction,
        "failed_nodes": failed_nodes
    }), 200


@app.route('/nodes/update_chain', methods=['POST'])
def update_chain():
    response = flask.request.get_json()
    blockchain.chain = []
    parent_node = response[1]
    blockchain.nodes.add(parent_node)
    chain_list = response[0]
    hash_list = response[2]
    blockchain.hash_list = set(hash_list)
    for chain in chain_list:
        if chain not in blockchain.chain:
            blockchain.chain.append(chain)

    return flask.jsonify(f"Added Chain to the network {chain_list} and nodes are {blockchain.nodes}"), 200


@app.route('/delete_node', methods=['POST'])
def delete_chain():
    response = flask.request.get_json()
    node = response.get("node")
    node_url :str = urlparse(node).netloc

    if node_url in blockchain.nodes :
        print("Node is already in the network" , blockchain.nodes)
        blockchain.nodes.remove(node_url)
        trimed_url = node_url.split('.')[0]
        blockchain.ttl.pop(trimed_url)

    return flask.jsonify(f"removed Node from the network"), 200


def shutdown_session(exception=None):
    """Cleanup function to run when the server shuts down"""
    global should_continue
    should_continue = False  # Signal the background thread to stop
    
    # blockchain.resolve_conflicts()
    database = BlockchainDb()
    
    database.save_blockchain(blockchain)
    database.save_to_firebase()
    blockchain.storage_db.save_storage_state(blockchain.storage)

    print("Blockchain saved to local file")

atexit.register(shutdown_session)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5001, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    # threading.Thread(target=register_node, args=[port], daemon=True).start()
    app.run(host='0.0.0.0', port=port)
