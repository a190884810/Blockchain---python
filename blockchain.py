# Basic structure in the block;
# {
#     "index": 0,
#     "timestamp": "",
#     "transaction":[
#       {
#             "sender":"",
#             "recipient":"",
#             "amount":5,
#       }
#     ],
#     "proof":"",
#     "previous_hash":"",
# }
import hashlib
from time import time  # For timestamp
import json
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request

from argparse import ArgumentParser


class Blockchain:

    # Constructor
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        # Build the No.1 block
        self.new_block(proof=100, previous_hash=1)

    def register_node(self, address: str) -> None:
        # http://127.0.0.1:5001
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain) -> bool:

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:

        neighbours = self.nodes

        max_length = len(self.chain)
        new_chain = None

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False


    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),  # Return the time
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
            # Previous hash can be the delivered hash or the hash calculated by the hash function
        }

        self.current_transactions = []  # Clear the current transaction
        self.chain.append(block)  # Append the new block

        return block

    def new_transaction(self, sender, recipient, amount) -> int:
        # Current_transaction is an array storing the block
        self.current_transactions.append(
            {
                'sender': sender,
                'recipient': recipient,
                'amount': amount
            }
        )

        return self.last_block['index'] + 1

    # Block Hash computation method
    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()  # Convert the block to str
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof: int) -> int:
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    # Testify
    def valid_proof(self, last_proof: int, proof: int) -> bool:
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()

        # Take the first 4 hash number
        return guess_hash[0:4] == "0000"


# testPow = Blockchain()
# testPow.proof_of_work(100)

app = Flask(__name__)
blockchain = Blockchain()

node_identifier = str(uuid4()).replace('-', '')

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ["sender", "recipient", "amount"]

    # Request error handling
    if values is None:
        return "Missing values", 400

    # Request error handling
    if not all(k in values for k in required):
        return "Missing values", 400

    index = blockchain.new_transaction(values['sender'],
                                       values['recipient'],
                                       values['amount'])

    response = {"message": f'Transaction will be added to Block{index}'}
    return jsonify(response), 201


@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    #Encouragement
    blockchain.new_transaction(sender='0',
                               recipient=node_identifier,
                               amount=1)

    block = blockchain.new_block(proof, None)

    response = {
        "message": "New Block Forged",
        "index": block['index'],
        "transactions": block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    return jsonify(response), 200

# { "nodes": ["http://127.0.0.2:5000"] }

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get("nodes")

    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)
    response = {
        "message": "New nodes have been added",
        "total——nodes": list(blockchain.nodes)
    }

    return jsonify(response), 201

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

    return jsonify(response), 200

if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to') # -p --port 5001
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)  # 127.0.0.1
