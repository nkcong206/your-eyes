from flask import Flask, request, jsonify, send_file
import os

app = Flask(__name__)

# Đường dẫn lưu tệp nhận được và tệp phản hồi
UPLOAD_FOLDER = '/home/nkcong206/Desktop/'
RETURN_FILE = os.path.join(UPLOAD_FOLDER, 'Sunset.mp3')

# API nhận file
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Lưu tệp vào đường dẫn đã định nghĩa
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Trả về file 'Sunset.mp3'
    return send_file(RETURN_FILE, as_attachment=True)

if __name__ == '__main__':
    # Chạy server trên 0.0.0.0 để có thể truy cập từ các thiết bị khác
    app.run(host='0.0.0.0', port=5000)

