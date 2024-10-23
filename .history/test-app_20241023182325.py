import requests

print(requests.get("http://127.0.0.1:5001/chain").json()["length"])