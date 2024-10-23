from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from hashlib import sha256
from ellipticcurve.privateKey import PrivateKey

# Step 1: Load the BIP39 wordlist file safely
try:
    with open("english.txt", "r") as bip39_wordlist_file:
        bip39_wordlist = bip39_wordlist_file.read().splitlines()
except FileNotFoundError:
    raise Exception("BIP39 wordlist file not found. Ensure 'english.txt' is present.")

# Step 2: Convert Private Key to BIP39 Mnemonic
def private_key_to_mnemonic(private_key_hex):
    try:
        # Convert private key from hex to binary (256-bit private key)
        entropy = bin(int(private_key_hex, 16))[2:].zfill(256)
        
        # Calculate SHA256 checksum (first 8 bits)
        sha256_hex = sha256(bytes.fromhex(private_key_hex)).hexdigest()
        sha256_bin = bin(int(sha256_hex, 16))[2:].zfill(256)
        checksum = sha256_bin[:8]  # First 8 bits of the SHA256 hash
        
        # Final binary string (entropy + checksum)
        final = entropy + checksum  # 256 bits + 8 bits = 264 bits
        
        # Split the final binary into 11-bit segments (24 words)
        word_length = 11
        res = [final[i:i + word_length] for i in range(0, len(final), word_length)]
        
        # Convert each 11-bit binary segment into a corresponding word from the BIP39 wordlist
        mnemonic = [bip39_wordlist[int(binary_place, 2)] for binary_place in res]
        
        return mnemonic
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid private key format")

# Step 3: Convert BIP39 Mnemonic to Private Key
def mnemonic_to_private_key(mnemonic):
    try:
        # Convert the mnemonic words back to the binary form
        final_bin = ''.join(bin(bip39_wordlist.index(word))[2:].zfill(11) for word in mnemonic)
        
        # Separate the entropy (256 bits) from the checksum (8 bits)
        entropy = final_bin[:256]
        private_key_hex = hex(int(entropy, 2))[2:].zfill(64)  # Convert binary entropy to hex (256 bits)
        
        # Generate public key from private key
        public_key_hex = PrivateKey.fromString(private_key_hex).publicKey().toCompressed()
        
        return {'private_key': private_key_hex, 'public_key': public_key_hex}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mnemonic words")

# FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request and response models
class PrivateKeyRequest(BaseModel):
    private_key: str

class MnemonicRequest(BaseModel):
    mnemonic: list

class MnemonicResponse(BaseModel):
    mnemonic: list

class PrivateKeyResponse(BaseModel):
    private_key: str
    public_key: str  # Add public_key to the response model

@app.post("/private_key_to_mnemonic", response_model=MnemonicResponse)
async def api_private_key_to_mnemonic(request: PrivateKeyRequest):
    private_key_hex = request.private_key
     
    if not private_key_hex or len(private_key_hex) != 64:
        raise HTTPException(status_code=400, detail="Invalid private key length. Expected 64 hex characters.")
    
    mnemonic = private_key_to_mnemonic(private_key_hex)
    
    return MnemonicResponse(mnemonic=mnemonic)

@app.post("/mnemonic_to_private_key", response_model=PrivateKeyResponse)
async def api_mnemonic_to_private_key(request: MnemonicRequest):
    mnemonic = request.mnemonic
    
    if not mnemonic or len(mnemonic) != 24:
        raise HTTPException(status_code=400, detail="Invalid mnemonic length. Expected 24 words.")
    
    key_data = mnemonic_to_private_key(mnemonic)
    
    return PrivateKeyResponse(private_key=key_data['private_key'], public_key=key_data['public_key'])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000, log_level="info")