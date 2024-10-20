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
# Define the hello endpoint
@app.get("/hello")
async def say_hello():
    return {"message": "hello"}

# Define the IP retrieval endpoint
@app.get("/ip")
async def get_ips():
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    return {"local_ip": local_ip, "public_ip": public_ip}

# Function to get the local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connecting to an external address to get the local IP
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

# Function to get the public IP address
def get_public_ip():
    response = requests.get('https://api.ipify.org?format=json')
    public_ip = response.json()["ip"]
    return public_ip

# Function to map the port using UPnP
def map_port_via_upnp(local_port):
    # Create a UPnP object
    upnp = miniupnpc.UPnP()

    # Discover UPnP devices (routers/gateways)
    upnp.discoverdelay = 200
    upnp.discover()

    # Select the first available Internet Gateway Device (IGD)
    upnp.selectigd()

    # External and internal port (you can change this)
    external_port = local_port  # We will map the local port to the same external port

    # Internal IP (your device IP in the local network)
    internal_ip = upnp.lanaddr

    # Add port forwarding
    upnp.addportmapping(external_port, 'TCP', internal_ip, local_port, 'FastAPI UPnP App', '')
    print(f"UPnP port mapping: External Port {external_port} to {internal_ip}:{local_port}")
    return internal_ip, external_port

if __name__ == "__main__":
    # Define the local port for FastAPI to run on
    local_port = 8000
    
    # Map the port via UPnP
    internal_ip, external_port = map_port_via_upnp(local_port)

    # Start the FastAPI server using Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=local_port)