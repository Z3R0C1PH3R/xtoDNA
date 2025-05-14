import heapq
from collections import Counter
import pickle


class Node:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None
        
    def __lt__(self, other):
        return self.freq < other.freq


def build_huffman_tree(data):
    """Build a Huffman tree from the given data."""
    # Count frequency of each byte
    frequency = Counter(data)
    
    # Create a priority queue (min heap)
    priority_queue = [Node(char, freq) for char, freq in frequency.items()]
    heapq.heapify(priority_queue)
    
    # Build the Huffman tree
    while len(priority_queue) > 1:
        # Get the two nodes with lowest frequency
        left = heapq.heappop(priority_queue)
        right = heapq.heappop(priority_queue)
        
        # Create a new internal node with these two nodes as children
        internal_node = Node(None, left.freq + right.freq)
        internal_node.left = left
        internal_node.right = right
        
        # Add the new node back to the queue
        heapq.heappush(priority_queue, internal_node)
    
    # Return the root of the Huffman tree
    return priority_queue[0] if priority_queue else None


def generate_codes(node, current_code="", codes=None):
    """Generate Huffman codes for each character."""
    if codes is None:
        codes = {}
        
    if node:
        if node.char is not None:  # Leaf node
            codes[node.char] = current_code if current_code else "0"  # Special case for single character
        else:  # Internal node
            generate_codes(node.left, current_code + "0", codes)
            generate_codes(node.right, current_code + "1", codes)
            
    return codes


def huffman_encode(data):
    """
    Encode the input bytes using Huffman coding.
    
    Args:
        data (bytes): Input bytes to encode
        
    Returns:
        tuple: (encoded_data, encoding_info) where:
            - encoded_data is the compressed data as bytes
            - encoding_info contains the Huffman codes and other metadata for decoding
    """
    if not data:
        return b"", {"codes": {}, "padding": 0}
    
    # Build Huffman tree
    root = build_huffman_tree(data)
    
    # Generate codes for each character
    codes = generate_codes(root)
    
    # Encode the data
    encoded_string = ""
    for byte in data:
        encoded_string += codes[byte]
    
    # Convert the encoded string to bytes
    padding = 8 - len(encoded_string) % 8 if len(encoded_string) % 8 != 0 else 0
    encoded_string += padding * "0"  # Pad with zeros to make length a multiple of 8
    
    encoded_bytes = bytearray()
    for i in range(0, len(encoded_string), 8):
        byte_str = encoded_string[i:i+8]
        encoded_bytes.append(int(byte_str, 2))
    
    # Save encoding info for decoding
    encoding_info = {
        "codes": codes,
        "padding": padding
    }
    
    return bytes(encoded_bytes), encoding_info


def huffman_decode(encoded_data, encoding_info):
    """
    Decode Huffman-encoded data.
    
    Args:
        encoded_data (bytes): Compressed data
        encoding_info (dict): Dictionary containing Huffman codes and padding info
        
    Returns:
        bytes: Decompressed data
    """
    codes = encoding_info["codes"]
    padding = encoding_info["padding"]
    
    # Reverse the codes for decoding
    reverse_codes = {code: char for char, code in codes.items()}
    
    # Convert encoded_data to a binary string
    binary_string = ""
    for byte in encoded_data:
        binary_string += format(byte, '08b')
    
    # Remove padding
    if padding:
        binary_string = binary_string[:-padding]
    
    # Decode the binary string
    decoded_data = bytearray()
    current_code = ""
    for bit in binary_string:
        current_code += bit
        if current_code in reverse_codes:
            decoded_data.append(reverse_codes[current_code])
            current_code = ""
            
    return bytes(decoded_data)


def compress_file(input_path, output_path):
    """Compress a file using Huffman coding."""
    with open(input_path, 'rb') as file:
        data = file.read()
    
    encoded_data, encoding_info = huffman_encode(data)
    
    with open(output_path, 'wb') as file:
        # Save encoding info for later decompression
        pickle.dump(encoding_info, file)
        file.write(encoded_data)


def decompress_file(input_path, output_path):
    """Decompress a Huffman-compressed file."""
    with open(input_path, 'rb') as file:
        # Load encoding info
        encoding_info = pickle.load(file)
        # Read compressed data
        encoded_data = file.read()
    
    decoded_data = huffman_decode(encoded_data, encoding_info)
    
    with open(output_path, 'wb') as file:
        file.write(decoded_data)


# Example usage:
if __name__ == "__main__":
    # Example of encoding and decoding bytes
    sample_data = b"hello world, this is a test of Huffman coding, how are you guys meow meow haha meow"
    encoded, info = huffman_encode(sample_data)
    print(f"Encoded data: {encoded}")
    print(f"Encoding info: {info}")
    print(f"Original size: {len(sample_data)} bytes")
    print(f"Compressed size: {len(encoded)} bytes")
    print(f"Compression ratio: {len(encoded) / len(sample_data):.2f}")
    
    decoded = huffman_decode(encoded, info)
    print(f"Successfully decoded: {decoded == sample_data}")
