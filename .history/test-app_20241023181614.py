import requests

print(len(requests.get("https://simplicity-server.onrender.com/chain")["chain"]))