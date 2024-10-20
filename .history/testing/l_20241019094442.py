import os
import sys
import socket
import requests
import uvicorn
from fastapi import FastAPI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix for Windows users with Python 3.8+
if sys.platform.startswith('win') and sys.version_info >= (3, 8):
    try:
        import site
        dll_path = os.path.join(site.getsitepackages()[0], "DLLs")
        if os.path.exists(dll_path):
            os.add_dll_directory(dll_path)
        logger.info(f"Added DLL directory: {dll_path}")
    except Exception as e:
        logger.warning(f"Failed to add DLL directory: {e}")

app = FastAPI()

@app.get("/hello")
async def say_hello():
    return {"message": "hello"}

@app.get("/ip")
async def get_ips():
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    return {"local_ip": local_ip, "public_ip": public_ip}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return None

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        response.raise_for_status()
        public_ip = response.json()["ip"]
        return public_ip
    except requests.RequestException as e:
        logger.error(f"Error getting public IP: {e}")
        return None

if __name__ == "__main__":
    local_port = 8000
    
    logger.info(f"Starting server on port {local_port}")
    logger.info(f"Local IP: {get_local_ip()}")
    logger.info(f"Public IP: {get_public_ip()}")
    logger.info("Note: To make this server accessible from the internet, you may need to set up port forwarding on your router.")
    
    uvicorn.run(app, host="0.0.0.0", port=local_port)