from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
import os
from werkzeug.utils import secure_filename
from test2 import (
    initialize_nucleotides, read_file, generate_key, encrypt_data,
    convert_to_nucleotides, decode_nucleotides, binary_to_bytes,
    decrypt_data, rs_encode, rs_decode, save_metadata, load_metadata,
    serialize_huffman_info, deserialize_huffman_info, 
    derive_key_iv_from_password, encrypt_data_with_password, decrypt_data_with_password
)
import tempfile
import shutil
import json
import uuid
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['GET', 'POST'])
def encode():
    if request.method == 'POST':
        # Check if file part is present
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user submits empty form
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Create unique ID for this process
            process_id = str(uuid.uuid4())
            process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
            os.makedirs(process_dir, exist_ok=True)
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            file_path = os.path.join(process_dir, filename)
            file.save(file_path)
            
            # Get configuration from form
            config = {
                'use_compression': request.form.get('use_compression') == 'on',
                'use_encryption': request.form.get('use_encryption') == 'on',
                'use_error_correction': request.form.get('use_error_correction') == 'on',
                'ecc_symbols': int(request.form.get('ecc_symbols', 20))
            }
            
            # Process the file
            try:
                # Initialize mappings
                nucleotides, inverse_nucleotides = initialize_nucleotides()
                
                # Read file data
                data = read_file(file_path)
                
                # Process data based on configuration
                processed_data = data
                original_encoded_length = len(data)
                info = None
                
                # Step 1: Compression (optional)
                if config['use_compression']:
                    processed_data, info = huffman_encode(processed_data)
                    original_encoded_length = len(processed_data)
                
                # Step 2: Encryption (optional)
                encryption_salt = None
                if config['use_encryption']:
                    # Get password from form
                    password = request.form.get('encryption_password', '')
                    if not password:
                        flash('Encryption password is required when encryption is enabled')
                        return redirect(request.url)
                        
                    processed_data, encryption_salt = encrypt_data_with_password(processed_data, password)
                
                # Step 3: Error correction (optional)
                if config['use_error_correction']:
                    ecc_symbols = config['ecc_symbols']
                    processed_data = rs_encode(bytes(processed_data), ecc_symbols)
                
                # Convert to DNA sequence
                dna_sequence = convert_to_nucleotides(processed_data, nucleotides)
                
                # Create metadata - store encryption salt but not the password
                metadata = {
                    'config': config,
                    'original_file_name': filename,
                    'original_size': len(data),
                    'processed_size': original_encoded_length,
                    'encryption_salt': base64.b64encode(encryption_salt).decode('utf-8') if encryption_salt else None,
                    'huffman_info': serialize_huffman_info(info),
                    'dna_sequence_length': len(dna_sequence)
                }
                
                # Save DNA sequence and metadata
                dna_file = os.path.join(process_dir, f"{os.path.splitext(filename)[0]}.dna")
                metadata_file = os.path.join(process_dir, f"{os.path.splitext(filename)[0]}_metadata.json")
                
                with open(dna_file, 'w') as f:
                    f.write(dna_sequence)
                
                save_metadata(metadata, metadata_file)
                
                # Don't save the encryption key file anymore since we're using password-based encryption
                
                # Return success with process ID for download
                flash('File encoded successfully!')
                return redirect(url_for('result', process_id=process_id))
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}')
                return redirect(request.url)
        else:
            flash('File type not allowed')
            return redirect(request.url)
            
    return render_template('encode.html')

@app.route('/decode', methods=['GET', 'POST'])
def decode():
    if request.method == 'POST':
        # Check if files are present
        if 'dna_file' not in request.files or 'metadata_file' not in request.files:
            flash('Both DNA and metadata files are required')
            return redirect(request.url)
        
        dna_file = request.files['dna_file']
        metadata_file = request.files['metadata_file']
        
        # If user submits empty form
        if dna_file.filename == '' or metadata_file.filename == '':
            flash('Both files must be selected')
            return redirect(request.url)
        
        # Create unique ID for this process
        process_id = str(uuid.uuid4())
        process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
        os.makedirs(process_dir, exist_ok=True)
        
        # Save uploaded files
        dna_path = os.path.join(process_dir, secure_filename(dna_file.filename))
        metadata_path = os.path.join(process_dir, secure_filename(metadata_file.filename))
        
        dna_file.save(dna_path)
        metadata_file.save(metadata_path)
        
        try:
            # Initialize mappings
            nucleotides, inverse_nucleotides = initialize_nucleotides()
            
            # Load DNA sequence and metadata
            with open(dna_path, 'r') as f:
                dna_sequence = f.read().strip()
            
            metadata = load_metadata(metadata_path)
            
            # Extract configuration and needed information
            config = metadata['config']
            original_encoded_length = metadata['processed_size']
            
            # Get encryption password if needed
            if config['use_encryption']:
                # Check if we have a salt in the metadata
                if 'encryption_salt' not in metadata or not metadata['encryption_salt']:
                    flash("Encryption salt not found in metadata. Cannot decrypt.")
                    return redirect(request.url)
                    
                encryption_password = request.form.get('encryption_password', '')
                if not encryption_password:
                    flash('Encryption password is required for decoding this file')
                    return redirect(request.url)
                    
                encryption_salt = base64.b64decode(metadata['encryption_salt'])
            
            huffman_info = deserialize_huffman_info(metadata['huffman_info'])
            output_file = metadata['original_file_name']
            
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
            
            # Step 2: Decryption (optional) - reverse
            if config['use_encryption']:
                try:
                    retrieved_data = decrypt_data_with_password(
                        retrieved_data, encryption_password, encryption_salt, original_encoded_length)
                    # Ensure output is the right length
                    retrieved_data = retrieved_data[:original_encoded_length]
                except Exception as e:
                    flash(f'Decryption failed, possibly due to an incorrect password: {str(e)}')
                    return redirect(request.url)
            
            # Step 3: Decompression (optional) - reverse
            if config['use_compression']:
                retrieved_data = huffman_decode(bytes(retrieved_data), huffman_info)
            
            # Save the decoded output to a file
            output_path = os.path.join(process_dir, f"decoded_{output_file}")
            with open(output_path, "wb") as f:
                f.write(retrieved_data)
            
            # Return success with process ID for download
            flash('File decoded successfully!')
            return redirect(url_for('result', process_id=process_id))
            
        except Exception as e:
            flash(f'Error decoding file: {str(e)}')
            return redirect(request.url)
            
    return render_template('decode.html')

@app.route('/result/<process_id>')
def result(process_id):
    process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
    if not os.path.exists(process_dir):
        flash('Process not found')
        return redirect(url_for('index'))
    
    # Get list of files in the process directory
    files = os.listdir(process_dir)
    
    # Organize files by type - no more encryption_keys in the output
    file_info = {
        'original': [],
        'dna': [],
        'metadata': [],
        'decoded': []
    }
    
    for file in files:
        if file.startswith('decoded_'):
            file_info['decoded'].append(file)
        elif file.endswith('.dna'):
            file_info['dna'].append(file)
        elif file.endswith('_metadata.json'):
            file_info['metadata'].append(file)
        else:
            file_info['original'].append(file)
    
    return render_template('result.html', process_id=process_id, file_info=file_info)

@app.route('/download/<process_id>/<filename>')
def download(process_id, filename):
    process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
    return send_file(os.path.join(process_dir, filename), as_attachment=True)

@app.route('/clean/<process_id>', methods=['POST'])
def clean(process_id):
    process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
    if os.path.exists(process_dir):
        shutil.rmtree(process_dir)
    return jsonify({'success': True})

@app.route('/text', methods=['GET', 'POST'])
def text():
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Get configuration from form
        config = {
            'use_compression': request.form.get('use_compression') == 'on',
            'use_encryption': request.form.get('use_encryption') == 'on',
            'use_error_correction': request.form.get('use_error_correction') == 'on',
            'ecc_symbols': int(request.form.get('ecc_symbols', 20))
        }
        
        try:
            # Initialize nucleotide mappings
            nucleotides, inverse_nucleotides = initialize_nucleotides()
            
            if action == 'encode':
                # Get input text
                input_text = request.form.get('input_text', '')
                if not input_text:
                    flash('Please enter some text to encode')
                    return redirect(url_for('text'))
                
                # Convert text to bytes
                data = input_text.encode('utf-8')
                
                # Process data based on configuration
                processed_data = data
                original_encoded_length = len(data)
                info = None
                
                # Step 1: Compression (optional)
                if config['use_compression']:
                    processed_data, info = huffman_encode(processed_data)
                    original_encoded_length = len(processed_data)
                
                # Step 2: Encryption (optional)
                encryption_salt = None
                if config['use_encryption']:
                    # Get password from form
                    password = request.form.get('encryption_password', '')
                    if not password:
                        flash('Encryption password is required when encryption is enabled')
                        return redirect(url_for('text'))
                        
                    processed_data, encryption_salt = encrypt_data_with_password(processed_data, password)
                
                # Step 3: Error correction (optional)
                if config['use_error_correction']:
                    ecc_symbols = config['ecc_symbols']
                    processed_data = rs_encode(bytes(processed_data), ecc_symbols)
                
                # Convert to DNA sequence
                dna_sequence = convert_to_nucleotides(processed_data, nucleotides)
                
                # Create metadata - include encryption salt but not the password
                metadata = {
                    'config': config,
                    'original_size': len(data),
                    'processed_size': original_encoded_length,
                    'encryption_salt': base64.b64encode(encryption_salt).decode('utf-8') if encryption_salt else None,
                    'huffman_info': serialize_huffman_info(info),
                    'dna_sequence_length': len(dna_sequence)
                }
                
                # Convert metadata to JSON string
                metadata_json = json.dumps(metadata, indent=2)
                
                # Return the result with DNA and metadata in the text boxes
                return render_template('text.html', 
                                      input_text=input_text, 
                                      dna_text=dna_sequence, 
                                      metadata_text=metadata_json,
                                      config=config,
                                      show_password_info=config['use_encryption'])
            
            elif action == 'decode':
                # Get DNA and metadata
                dna_sequence = request.form.get('dna_text', '').strip()
                metadata_json = request.form.get('metadata_text', '').strip()
                encryption_password = request.form.get('encryption_password', '').strip()
                
                if not dna_sequence or not metadata_json:
                    flash('Both DNA sequence and metadata are required for decoding')
                    return redirect(url_for('text'))
                
                # Parse metadata
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    flash('Invalid metadata JSON format')
                    return redirect(url_for('text'))
                
                # Extract configuration and needed information
                config = metadata['config']
                original_encoded_length = metadata['processed_size']
                
                # Get encryption password if needed
                if config['use_encryption']:
                    # Check if we have a salt in the metadata
                    if 'encryption_salt' not in metadata or not metadata['encryption_salt']:
                        flash("Encryption salt not found in metadata. Cannot decrypt.")
                        return redirect(url_for('text'))
                        
                    if not encryption_password:
                        flash('Encryption password is required for decoding')
                        return redirect(url_for('text'))
                        
                    encryption_salt = base64.b64decode(metadata['encryption_salt'])
                
                huffman_info = deserialize_huffman_info(metadata['huffman_info'])
                
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
                
                # Step 2: Decryption (optional) - reverse
                if config['use_encryption']:
                    try:
                        retrieved_data = decrypt_data_with_password(
                            retrieved_data, encryption_password, encryption_salt, original_encoded_length)
                        # Ensure output is the right length
                        retrieved_data = retrieved_data[:original_encoded_length]
                    except Exception as e:
                        flash(f'Decryption failed, possibly due to an incorrect password: {str(e)}')
                        return redirect(url_for('text'))
                
                # Step 3: Decompression (optional) - reverse
                if config['use_compression']:
                    retrieved_data = huffman_decode(bytes(retrieved_data), huffman_info)
                
                # Convert bytes back to text
                output_text = retrieved_data.decode('utf-8', errors='replace')
                
                return render_template('text.html', 
                                      output_text=output_text, 
                                      dna_text=dna_sequence, 
                                      metadata_text=metadata_json,
                                      config=config,
                                      show_password_info=config['use_encryption'])
            
        except Exception as e:
            flash(f'Error processing: {str(e)}')
            return redirect(url_for('text'))
    
    # Default configuration for GET request
    config = {
        'use_compression': True,
        'use_encryption': True,
        'use_error_correction': True,
        'ecc_symbols': 20
    }
    
    return render_template('text.html', config=config, show_password_info=False)

if __name__ == '__main__':
    app.run(debug=True)
