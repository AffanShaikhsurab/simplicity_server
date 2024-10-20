import uvicorn
from fastapi import FastAPI
import miniupnpc

app = FastAPI()

# Define the hello endpoint
@app.get("/hello")
async def say_hello():
    return {"message": "hello"}

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
