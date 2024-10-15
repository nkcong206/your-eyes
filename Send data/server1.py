import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app)

# Đường dẫn lưu tệp nhận được và tệp phản hồi
UPLOAD_FOLDER = '/home/nkcong206/Desktop/'
RETURN_FILE = os.path.join(UPLOAD_FOLDER, 'server.mp3')

# Dictionary để lưu trạng thái kết nối của client
clients = {}

# API nhận file
# API nhận file
@app.route('/upload', methods=['POST'])
def upload_file():
    client_id = request.args.get('client_id')
    
    # Log thông tin về client_id và các kết nối hiện tại
    logging.info(f"Upload attempt for client ID: {client_id}. Current connected clients: {clients}")

    if not client_id or client_id not in clients:
        logging.error(f"Upload failed: Client ID {client_id} không hợp lệ hoặc không kết nối.")
        return jsonify({"error": "Client ID không hợp lệ hoặc không kết nối"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Lưu tệp vào đường dẫn đã định nghĩa
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    logging.info(f"File {file.filename} uploaded successfully by client {client_id}")

    # Trả về thành công
    return jsonify({"success": True}), 200


# API để gửi file server.mp3 xuống client thông qua HTTP
@app.route('/download', methods=['GET'])
def download_file():
    try:
        # Kiểm tra sự tồn tại của tệp
        if os.path.exists(RETURN_FILE):
            logging.info(f"Sending file {RETURN_FILE} to client")
            return send_file(RETURN_FILE, as_attachment=True)
        else:
            logging.error("File not found")
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logging.error(f"Error sending file: {e}")
        return jsonify({"error": str(e)}), 500

# WebSocket event to handle new connection with client ID
@socketio.on('connect')
def handle_connect():
    client_id = request.args.get('client_id')
    if client_id:
        clients[client_id] = request.sid
        logging.info(f"Client {client_id} connected with session ID {request.sid}.")
    else:
        logging.error("Connection attempt without client_id.")
        return False  # Ngắt kết nối nếu không có client_id

# WebSocket event to handle disconnect
@socketio.on('disconnect')
def handle_disconnect():
    for client_id, sid in clients.items():
        if sid == request.sid:
            logging.info(f"Client {client_id} disconnected.")
            del clients[client_id]
            break

# Function to send file to client_1234 via WebSocket
def send_file_to_client():
    client_id = 'client_1234'  # Luôn gửi tới client_1234
    sid = clients.get(client_id)

    logging.info(f"Preparing to send file to {client_id}")
    
    if sid:
        try:
            with open(RETURN_FILE, "rb") as audio_file:
                audio_data = audio_file.read()
                # Sử dụng socketio.emit() thay vì emit() để gửi từ thread
                socketio.emit('receive_file', {'filename': 'server.mp3', 'file': audio_data}, room=sid)
            logging.info(f"Sent file to client {client_id}")
        except Exception as e:
            logging.error(f"Error sending file to {client_id}: {e}")
    else:
        logging.warning(f"Client {client_id} is not connected.")

# Hàm lắng nghe bàn phím để nhận lệnh và gửi file
def keyboard_listener():
    while True:
        command = input("Enter 'send' to send the file to client_1234: ")
        if command == "send":
            logging.info("Sending file command received.")
            send_file_to_client()  # Luôn gửi file đến client_1234
        else:
            logging.warning("Unknown command")

if __name__ == '__main__':
    # Chạy thread để lắng nghe lệnh từ bàn phím
    logging.info("Starting keyboard listener...")
    threading.Thread(target=keyboard_listener, daemon=True).start()
    
    # Chạy server với SocketIO trên cổng 5000
    logging.info("Starting server...")
    socketio.run(app, host='0.0.0.0', port=5000)

