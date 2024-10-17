import threading
import time
from urllib.parse import urlparse
from uuid import uuid4
import flask
import requests
from g.blockchain import Blockchain
from database import BlockchainDb
from flask_cors import CORS  # Import CORS

app = flask.Flask(__name__)
from flask import Flask, copy_current_request_context, g, request, jsonify

# Enable CORS for the entire Flask app
CORS(app)

blockchain = Blockchain()

# Use app.before_request to ensure g.blockchain is initialized before each request
@app.before_request
def before_request():
    g.blockchain = blockchain
    
    
@app.route('/hello', methods=['GET'])
def hello():
    
    return flask.jsonify({
        'nodes': list(g.blockchain.nodes),
        'length': len(list(g.blockchain.nodes))
    })


@app.route('/chain', methods=['GET'])
def chain():
    return flask.jsonify({
        'chain': g.blockchain.chain,
        'length': len(g.blockchain.chain)
    })


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = flask.request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['transaction', 'digital_signature', 'public_key']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index, error = g.blockchain.new_transaction(values['transaction'], values['public_key'], values['digital_signature'])
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
        print("this is parent node", "simplicity_server1.onrender.com")
        g.blockchain.register_node(node, "simplicity_server1.onrender.com")

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(g.blockchain.nodes),
    }
    return flask.jsonify(response), 201


@app.route('/nodes/update_nodes', methods=['POST'])
def update_nodes():
    values = flask.request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        print("this is parent node", "simplicity_server1.onrender.com")
        if node not in g.blockchain.nodes:
            g.blockchain.nodes.add(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(g.blockchain.nodes),
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

    g.blockchain.updateTTL(update_nodes , node )
    response = {
        'message': 'The TTL of nodes have been updated',
        'total_nodes': list(g.blockchain.nodes),
    }
    return flask.jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = g.blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': g.blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': g.blockchain.chain
        }

    return flask.jsonify(response), 200


@app.route('/nodes/update_block', methods=['POST'])
def update_block():
    block = flask.request.get_json()
    print("this is block", block)
    if g.blockchain.hash(block) in g.blockchain.hash_list:
        return flask.jsonify(f"Already added Block in the network {block}"), 200
    else:
        for transaction in block['transactions']:
            if transaction in g.blockchain.current_transactions:
                g.blockchain.current_transactions.remove(transaction)

        g.blockchain.chain.append(block)
        g.blockchain.hash_list.add(g.blockchain.hash(block))

        # send data to the known nodes in the network
        for node in g.blockchain.nodes:
            requests.post(f'http://{node}/nodes/update_block', json=block, timeout=5)
            requests.post(f'http://{node}/nodes/update_nodes', json={
                "nodes": list(g.blockchain.nodes)
            })

    return flask.jsonify(f"Added Block to the network {block}"), 200


@app.route('/nodes/update_transaction', methods=['POST'])
def update_transaction():
    transaction = flask.request.get_json()

    if transaction.get('id') in [t.get('id') for t in g.blockchain.current_transactions]:
        return flask.jsonify({"message": f"Transaction already in the network", "transaction": transaction}), 200

    g.blockchain.current_transactions.append(transaction)
    g.blockchain.miner()

    # Send data to the known nodes in the network
    failed_nodes = []
    for node in g.blockchain.nodes:
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
    g.blockchain.chain = []
    parent_node = response[1]
    g.blockchain.nodes.add(parent_node)
    chain_list = response[0]
    hash_list = response[2]
    g.blockchain.hash_list = set(hash_list)
    for chain in chain_list:
        if chain not in g.blockchain.chain:
            g.blockchain.chain.append(chain)

    return flask.jsonify(f"Added Chain to the network {chain_list} and nodes are {g.blockchain.nodes}"), 200


@app.route('/delete_node', methods=['POST'])
def delete_chain():
    response = flask.request.get_json()
    g.blockchain.nodes.remove(response.get("node"))

    return flask.jsonify(f"removed Node from the network"), 200


@app.teardown_appcontext
def shutdown_session(exception=None):
    database = BlockchainDb()
    database.save_blockchain(g.blockchain)

    host_url = getattr(g, 'host_url', None)  # Get the host URL safely
    if host_url:
        for node in g.blockchain.nodes:
            try:
                requests.post(f'http://{node}/delete_node', json={"node": host_url}, timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"Error notifying node {node}: {e}")


# def register_node(port):
#     print(f"Registering node with port {port}...")
#     print("nodes" ,g.blockchain.nodes)
#     print("nodes type" ,type(g.blockchain.nodes))
#     print("chain" ,g.blockchain.chain)
#     print("chain type" ,type(g.blockchain.chain))
#     g.blockchain.register('simplicity_server1.onrender.com')


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    # threading.Thread(target=register_node, args=[port], daemon=True).start()
    app.run(host='0.0.0.0', port=port)
