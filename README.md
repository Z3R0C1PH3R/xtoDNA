# DNA Storage System

A web-based application for encoding digital data into DNA sequences and decoding it back. This system demonstrates the concept of using DNA as a storage medium by converting binary data to nucleotide sequences with options for compression, encryption, and error correction.

## Features

- **File Encoding**: Convert any file to a DNA nucleotide sequence
- **Text Processing**: Directly encode and decode text in the browser
- **Compression**: Optional Huffman coding to reduce data size
- **Encryption**: AES-256 encryption with password protection
- **Error Correction**: Reed-Solomon error correction to ensure data integrity
- **Web Interface**: User-friendly interface for all operations

## How It Works

1. **Compression**: Files are optionally compressed using Huffman encoding to reduce size (not recommended for already compressed files like images or videos)
2. **Encryption**: Data can be encrypted with AES-256 using a password-derived key
3. **Error Correction**: Reed-Solomon encoding adds redundancy to protect against errors
4. **DNA Encoding**: Binary data is encoded using the four DNA nucleotides (A, T, G, C)
5. **Start/Stop Codons**: "ATG" and "TAC" are added as markers

## Setup Instructions

### Prerequisites

- Python 3.8+
- Flask
- Required Python packages (see requirements.txt)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/dna-storage-system.git
   cd dna-storage-system
   ```

2. Create a virtual environment (recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Usage

### Encoding a File

1. Click "Encode File" on the homepage
2. Upload your file (supported formats: txt, pdf, png, jpg, jpeg, gif, mp3, mp4, zip)
3. Configure options:
   - Compression (recommended for text files)
   - Encryption (requires password)
   - Error correction (adjust symbols as needed)
4. Submit the form to process
5. Download both the DNA sequence file (.dna) and metadata file (.json)

### Decoding a File

1. Click "Decode File" on the homepage
2. Upload the DNA sequence file (.dna)
3. Upload the metadata file (.json)
4. Enter the encryption password if the file was encrypted
5. Submit to decode and download the original file

### Text Processing

1. Click "Text Processing" on the homepage
2. Enter text in the input box
3. Configure options (compression, encryption, error correction)
4. Click "Encode Text to DNA" to generate the DNA sequence and metadata
5. To decode, ensure DNA sequence and metadata are present, enter password if needed, and click "Decode DNA to Text"

## Important Notes

- **Remember Your Password**: If you encrypt your data, there is no way to recover it without the password
- **Keep Your Metadata**: The metadata file contains crucial information needed for decoding
- **Compression Suitability**: Compression works best for text files and may not be beneficial for already compressed formats

## Technical Details

- **Encoding Method**: Each pair of bits is represented by a nucleotide (A=00, C=01, G=10, T=11)
- **Error Correction**: Reed-Solomon codes provide protection against corrupted nucleotides
- **Encryption**: AES-256 in CBC mode with PBKDF2 key derivation
- **Password Storage**: Only a hash of the password is stored, ensuring security

## License

[MIT License](LICENSE)

## Acknowledgements

- This project was created as part of the "How to Grow Almost Anything" course
- Reed-Solomon implementation uses the `reedsolo` library
- Encryption uses the Python `cryptography` package