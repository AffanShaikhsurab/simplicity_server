import requests

print(requests.get("https://simplicity-server.onrender.com/chain").json()["length"])