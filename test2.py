from os import urandom
from math import log2, floor
from huffman import huffman_encode, huffman_decode
from reedsolo import RSCodec, ReedSolomonError
import json
import base64
import pickle
import os
import hashlib
import hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Configuration options
CONFIG = {
    'use_compression': True,    # Whether to use Huffman compression
    'use_encryption': True,     # Whether to use AES encryption
    'use_error_correction': True,  # Whether to use Reed-Solomon error correction
    'ecc_symbols': 20           # Number of error correction symbols if error correction is enabled
}

def initialize_nucleotides():
    """Initialize nucleotide mapping dictionaries."""
    nucleotides = ["A", "C", "G", "T"]
    inverse_nucleotides = {n: f"{i:02b}" for i, n in enumerate(nucleotides)}
    return nucleotides, inverse_nucleotides

def read_file(file_path):
    """Read binary data from a file."""
    with open(file_path, "r+b") as f:
        data = f.read()
    return data

def derive_key_iv_from_password(password, salt=None):
    """Derive encryption key and IV from a password using PBKDF2."""
    if salt is None:
        salt = os.urandom(16)  # Generate a random salt if not provided
    
    # Use PBKDF2 to derive a key from the password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=48,  # 32 bytes for key, 16 bytes for IV
        salt=salt,
        iterations=100000,  # High number of iterations for security
        backend=default_backend()
    )
    
    # Convert password string to bytes if it's not already
    if isinstance(password, str):
        password = password.encode('utf-8')
        
    # Derive the key material
    key_material = kdf.derive(password)
    
    # Split into key and IV
    key = key_material[:32]
    iv = key_material[32:48]
    
    return key, iv, salt

def encrypt_data(data, key_iv_tuple):
    """Encrypt data using AES-CBC with the given key and IV."""
    key, iv = key_iv_tuple
    
    # Pad the data to ensure it's a multiple of the block size (16 bytes for AES)
    padded_data = pad_data(bytes(data))
    
    # Create an AES cipher in CBC mode
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Encrypt the padded data
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    return bytearray(encrypted_data)

def encrypt_data_with_password(data, password):
    """Encrypt data using a password."""
    # Derive key and IV from password
    key, iv, salt = derive_key_iv_from_password(password)
    
    # Use the derived key and IV for encryption
    key_iv_tuple = (key, iv)
    encrypted_data = encrypt_data(data, key_iv_tuple)
    
    return encrypted_data, salt

def decrypt_data(encrypted_data, key_iv_tuple, original_length):
    """Decrypt data using AES-CBC with the given key and IV."""
    key, iv = key_iv_tuple
    
    # Create an AES cipher in CBC mode
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    # Decrypt the data
    decrypted_padded = decryptor.update(bytes(encrypted_data)) + decryptor.finalize()
    
    # Unpad the data
    decrypted_data = unpad_data(decrypted_padded)
    
    # Ensure we don't exceed the original length
    return bytearray(decrypted_data[:original_length])

def decrypt_data_with_password(encrypted_data, password, salt, original_length):
    """Decrypt data using a password and salt."""
    # Derive the same key and IV using the password and stored salt
    key, iv, _ = derive_key_iv_from_password(password, salt)
    
    # Use the derived key and IV for decryption
    key_iv_tuple = (key, iv)
    return decrypt_data(encrypted_data, key_iv_tuple, original_length)

def pad_data(data):
    """PKCS#7 padding for AES block size (16 bytes)."""
    block_size = 16
    padding_len = block_size - (len(data) % block_size)
    padding = bytes([padding_len]) * padding_len
    return data + padding

def unpad_data(padded_data):
    """Remove PKCS#7 padding."""
    padding_len = padded_data[-1]
    return padded_data[:-padding_len]

def serialize_key_iv(key_iv_tuple):
    """Serialize key and IV for storage."""
    key, iv = key_iv_tuple
    return base64.b64encode(key).decode('utf-8'), base64.b64encode(iv).decode('utf-8')

def deserialize_key_iv(key_b64, iv_b64):
    """Deserialize key and IV from storage."""
    key = base64.b64decode(key_b64)
    iv = base64.b64decode(iv_b64)
    return key, iv

def convert_to_nucleotides(encrypted_data, nucleotides):
    """Convert encrypted binary data to nucleotide sequence."""
    nucleotides_list = []
    for i in encrypted_data:
        binary = f"{i:08b}"
        nucleotides_list.extend([nucleotides[int(binary[j:j+2], 2)] for j in range(0, 8, 2)])
    return "ATG" + "".join(nucleotides_list) + "TAC"  # Add start/stop codons

def decode_nucleotides(encoded_data, inverse_nucleotides):
    """Convert nucleotide sequence back to binary string."""
    string = ""
    for i in encoded_data[3:-3]:  # Skip start/stop codons
        string += inverse_nucleotides[i]
    return string

def binary_to_bytes(binary_string):
    """Convert binary string to byte array."""
    # Make sure binary string length is a multiple of 8
    padded_length = ((len(binary_string) + 7) // 8) * 8
    padded_binary = binary_string.ljust(padded_length, '0')
    return bytearray(int(padded_binary[i:i + 8], 2) for i in range(0, len(padded_binary), 8))

def rs_encode(data, ecc_symbols=10):
    """Apply Reed-Solomon encoding with error correction."""
    rsc = RSCodec(ecc_symbols)
    return rsc.encode(data)

def rs_decode(data, ecc_symbols=10):
    """Apply Reed-Solomon decoding with error correction."""
    rsc = RSCodec(ecc_symbols)
    try:
        return rsc.decode(data)[0]  # [0] to get the decoded data without ecc symbols
    except ReedSolomonError as e:
        print(f"Reed-Solomon decoding error: {e}")
        return data  # Return original data if decoding fails

def save_metadata(metadata, file_path):
    """Save metadata to a file."""
    with open(file_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_metadata(file_path):
    """Load metadata from a file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def serialize_huffman_info(info):
    """Serialize Huffman encoding information for storage in metadata."""
    if info is None:
        return None
    return base64.b64encode(pickle.dumps(info)).decode('utf-8')

def deserialize_huffman_info(serialized_info):
    """Deserialize Huffman encoding information from metadata."""
    if serialized_info is None:
        return None
    return pickle.loads(base64.b64decode(serialized_info.encode('utf-8')))

def main():
    # Initialize mappings
    nucleotides, inverse_nucleotides = initialize_nucleotides()
    
    # Check if we're in encoding or decoding mode
    encode_mode = True
    if len(os.sys.argv) > 1 and os.sys.argv[1].lower() == 'decode':
        encode_mode = False
    
    if encode_mode:
        # ENCODING MODE
        # Read input file
        input_file = "input.txt"
        if len(os.sys.argv) > 2:
            input_file = os.sys.argv[2]
            
        data = read_file(input_file)
        
        # Process data based on configuration
        processed_data = data
        original_encoded_length = len(data)
        info = None
        
        # Step 1: Compression (optional)
        if CONFIG['use_compression']:
            processed_data, info = huffman_encode(processed_data)
            original_encoded_length = len(processed_data)
            print(f"Compression ratio: {len(data)/original_encoded_length:.2f}")
        else:
            print("Compression disabled")
        
        # Step 2: Encryption (optional)
        encryption_salt = None
        if CONFIG['use_encryption']:
            # Get password from user
            import getpass
            password = getpass.getpass("Enter encryption password: ")
            processed_data, encryption_salt = encrypt_data_with_password(processed_data, password)
            print(f"Data encrypted with password-derived key")
        else:
            print("Encryption disabled")
        
        # Step 3: Error correction (optional)
        if CONFIG['use_error_correction']:
            ecc_symbols = CONFIG['ecc_symbols']
            processed_data = rs_encode(bytes(processed_data), ecc_symbols)
            print(f"Data size after RS encoding: {len(processed_data)} bytes")
        else:
            print("Error correction disabled")
        
        # Convert to DNA sequence
        dna_sequence = convert_to_nucleotides(processed_data, nucleotides)
        print(f"DNA sequence length: {len(dna_sequence)} nucleotides")
        
        # Create metadata
        metadata = {
            'config': CONFIG,
            'original_file_name': os.path.basename(input_file),
            'original_size': len(data),
            'processed_size': original_encoded_length,
            'encryption_salt': base64.b64encode(encryption_salt).decode('utf-8') if encryption_salt else None,
            'huffman_info': serialize_huffman_info(info),
            'dna_sequence_length': len(dna_sequence)
        }
        
        # Save DNA sequence and metadata
        output_base = os.path.splitext(input_file)[0]
        dna_file = f"{output_base}.dna"
        metadata_file = f"{output_base}_metadata.json"
        
        with open(dna_file, 'w') as f:
            f.write(dna_sequence)
        
        save_metadata(metadata, metadata_file)
        
        print(f"DNA sequence saved to {dna_file}")
        print(f"Metadata saved to {metadata_file}")
        
    else:
        # DECODING MODE
        # Load DNA sequence and metadata
        if len(os.sys.argv) < 3:
            print("Usage: python test2.py decode <dna_file> <metadata_file>")
            return
            
        dna_file = os.sys.argv[2]
        metadata_file = os.sys.argv[3]
        
        with open(dna_file, 'r') as f:
            dna_sequence = f.read().strip()
        
        metadata = load_metadata(metadata_file)
        
        # Extract configuration and needed information
        config = metadata['config']
        original_encoded_length = metadata['processed_size']
        huffman_info = deserialize_huffman_info(metadata['huffman_info'])
        output_file = metadata['original_file_name']
        
        print(f"Decoding DNA sequence of length {len(dna_sequence)}")
        
        # Decode the DNA sequence
        binary_string = decode_nucleotides(dna_sequence, inverse_nucleotides)
        
        # Convert binary string to bytes
        byte_array = binary_to_bytes(binary_string)
        
        # Process data back based on configuration (in reverse order)
        retrieved_data = byte_array
        
        # Step 1: Error correction (optional) - reverse
        if config['use_error_correction']:
            ecc_symbols = config['ecc_symbols']
            retrieved_data = rs_decode(retrieved_data, ecc_symbols)
            print(f"Data size after RS decoding: {len(retrieved_data)} bytes")
        
        # Get encryption password if needed
        if config['use_encryption']:
            # Check if we have a salt in the metadata
            if 'encryption_salt' not in metadata or not metadata['encryption_salt']:
                print("Error: Encryption salt not found in metadata")
                return
                
            import getpass
            password = getpass.getpass("Enter decryption password: ")
            encryption_salt = base64.b64decode(metadata['encryption_salt'])
        
        # Step 2: Decryption (optional) - reverse
        if config['use_encryption']:
            try:
                retrieved_data = decrypt_data_with_password(
                    retrieved_data, password, encryption_salt, original_encoded_length)
                # Ensure output is the right length
                retrieved_data = retrieved_data[:original_encoded_length]
            except Exception as e:
                print(f"Decryption failed: {e}")
                print("This may be due to an incorrect password.")
                return
        
        # Step 3: Decompression (optional) - reverse
        if config['use_compression']:
            retrieved_data = huffman_decode(bytes(retrieved_data), huffman_info)
        
        # Save the decoded output to a file
        output_path = f"decoded_{output_file}"
        with open(output_path, "wb") as f:
            f.write(retrieved_data)
        
        print(f"Decoding completed successfully! Output saved to {output_path}")

if __name__ == "__main__":
    main()