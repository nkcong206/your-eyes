import os
import requests
import speech_recognition as sr
from pydub import AudioSegment
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import time
import base64

# Khóa API của Google Gemini
os.environ["GOOGLE_API_KEY"] = "AIzaSyCbHQIqUpqxs-IucTkPVSTATauGLt9gE40"

app = Flask(__name__)
socketio = SocketIO(app)

# Đường dẫn lưu tệp nhận được và tệp phản hồi
ANSWERS_FOLDER = '/home/nkcong206/Desktop/server/answers'
QUESTIONS_FOLDER = '/home/nkcong206/Desktop/server/questions'

answer_path = os.path.join(ANSWERS_FOLDER, 'answer.mp3')

# Dictionary để lưu trạng thái kết nối của client
clients = {}

# Biến lưu câu hỏi và câu trả lời
answer = ""
question = ""

# Khởi tạo mô hình Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)

class AudioProcessor:
    def __init__(self, audio_data_path):
        self.audio_data_path = audio_data_path

    def convert_mp3_to_wav(self):
        sound = AudioSegment.from_mp3(self.audio_data_path)
        wav_path = self.audio_data_path.replace(".mp3", ".wav")
        sound.export(wav_path, format="wav")
        return wav_path

    def audio_to_text(self):
        # Chuyển đổi MP3 sang WAV
        wav_file = self.convert_mp3_to_wav()

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="vi")
                return text
            except sr.UnknownValueError:
                return "Google Speech Recognition không thể hiểu âm thanh"
            except sr.RequestError as e:
                return f"Không thể kết nối với Google Speech Recognition service; {e}"

# Hàm gọi API FPT.AI để chuyển script thành MP3 và tải file MP3 về
def text_to_speech_fpt(script):
    url = 'https://api.fpt.ai/hmi/tts/v5'
    
    headers = {
        'api-key': 'yqYMtKL9zFAFdQgIJqFuVK53BPMvnn6h',  # Thay thế bằng API key của bạn
        'speed': '-0.5',
        'voice': 'banmai'
    }

    # Gọi API FPT để chuyển script thành MP3
    response = requests.request('POST', url, data=script.encode('utf-8'), headers=headers)
    if response.status_code == 200:
        # Lấy link async để tải file MP3
        async_url = response.json().get('async')
        if async_url:
            # Đợi một vài giây để file MP3 sẵn sàng
            time.sleep(1)
            # Tải file MP3 từ link async
            mp3_response = requests.get(async_url)
            if mp3_response.status_code == 200:
                # Lưu file thành answer.mp3
                with open(answer_path, 'wb') as f:
                    f.write(mp3_response.content)
            else:
                print(f"Failed to download MP3 file. Status code: {mp3_response.status_code}")
        else:
            print("No async URL found in the response.")
    else:
        print(f"Failed to generate speech. Status code: {response.status_code}, {response.text}")


# Phân loại yêu cầu
def classify_request(input_text):
    messages = [
        (
            "system",
            "Bạn là một AI giúp phân loại các yêu cầu của người khiếm thị thành hai loại: "
            "1. trò chuyện bình thường, "
            "2. xác định chữ, vật trước mặt. "
            "Hãy phân loại yêu cầu của người dùng vào một trong hai loại này."
        ),
        ("human", input_text),
    ]
    ai_msg = llm.invoke(messages)
    classification = ai_msg.content.strip().lower()

    if "trò chuyện" in classification:
        return 0
    elif "chữ" in classification or "vật" in classification:
        return 1
    else:
        return -1
    
# Hàm gọi Langchain (Gemini) để trả về câu trả lời (script)
def generate_script_with_langchain(input_text):
    # Tạo thông điệp cho mô hình
    messages = [
        (
            "system",
            "Bạn là trợ lý ảo hữu ích hỗ trợ người mù, hãy tạo ra nội dung để phản hồi văn bản của người dùng một cách ngắn gọn nhất."
        ),
        ("human", input_text),
    ]
    
    # Nhận script từ Gemini
    ai_msg = llm.invoke(messages)
    return ai_msg.content


def gemini_answer(input_text):
    # Tạo script từ text sử dụng Langchain (Gemini)
    output = generate_script_with_langchain(input_text)

    # Chuyển script thành audio MP3 và lưu thành answer.mp3
    text_to_speech_fpt(output)
    return output

# Xử lý yêu cầu với hình ảnh và câu hỏi
def gemini_answer_with_image(question, image_path):
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    content = [
        {"type": "text", "text": question},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
        },
    ]

    message = HumanMessage(content=content)
    response = llm.invoke([message])
    output = response.content
    text_to_speech_fpt(output)
    return output

# Hàm sinh câu trả lời từ Langchain và chuyển thành file MP3, sau đó gửi tới client
def process_answer(client_id):
    global question, answer

    answer = gemini_answer(question)
    # Gửi file và script tới client nếu kết nối tồn tại
    send_file_and_script_to_client(client_id)

def process_answer_with_image(client_id, image_path):
    global question, answer
    answer = gemini_answer_with_image(question,image_path)

    send_file_and_script_to_client(client_id)

# WebSocket event to handle new connection with client ID
@socketio.on('connect')
def handle_connect():
    client_id = request.args.get('id')
    if client_id:
        clients[client_id] = request.sid
        print(f"Client {client_id} connected.")

# WebSocket event to handle disconnect
@socketio.on('disconnect')
def handle_disconnect():
    for client_id, sid in clients.items():
        if sid == request.sid:
            print(f"Client {client_id} disconnected.")
            del clients[client_id]
            break

# API nhận file MP3 từ client và xử lý phân loại yêu cầu
@app.route('/upload', methods=['POST'])
def upload_file():
    global question
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Lưu file âm thanh
    file_path = os.path.join(QUESTIONS_FOLDER, file.filename)
    file.save(file_path)

    # Chuyển âm thanh thành văn bản
    processor = AudioProcessor(file_path)
    question = processor.audio_to_text()

    # Phân loại yêu cầu
    request_type = classify_request(question)

    client_id = request.args.get('client_id')
    if client_id not in clients:
        return jsonify({"error": f"Client {client_id} not connected"}), 400

    if request_type == 0:
        # Nếu là trò chuyện bình thường, trả về câu trả lời ngay lập tức
        threading.Thread(target=process_answer, args=(client_id,)).start()
        return jsonify({"script": question}), 200
    elif request_type == 1:
        # Nếu là xác định chữ hoặc vật, yêu cầu client gửi hình ảnh
        return jsonify({"script": question, "request": "upload an image"}), 200
    else:
        return jsonify({"error": "Could not classify request."}), 400

# API để nhận hình ảnh từ client
@app.route('/upload_image', methods=['POST'])
def upload_image():
    global question
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Lưu tệp vào đường dẫn đã định nghĩa
    image_path = os.path.join(QUESTIONS_FOLDER, file.filename)
    file.save(image_path)
    
    client_id = request.args.get('client_id')
    if client_id not in clients:
        return jsonify({"error": f"Client {client_id} not connected"}), 400
    
    threading.Thread(target=process_answer_with_image, args=(client_id,image_path,)).start()
    return jsonify({"success": 'true'}), 200
    
# API để gửi tệp answer.mp3 đến client
@app.route('/download', methods=['GET'])
def download_file():
    # Kiểm tra sự tồn tại của file answer.mp3
    if os.path.exists(answer_path):
        return send_file(answer_path, as_attachment=True)
    else:
        print("File not found")
        return jsonify({"error": "File not found"}), 404

# Function to send file and script to a client by ID
def send_file_and_script_to_client(client_id):
    global answer
    sid = clients.get(client_id)
    
    if sid:
        # Gửi cả file MP3 và script (câu trả lời) về cho client qua WebSocket
        socketio.emit('receive_file', {'filename': 'answer.mp3', 'script': answer}, room=sid)
        print(f"Sent file and script to client {client_id}")
    else:
        print(f"Client {client_id} not found.")

# Hàm lắng nghe bàn phím để nhận lệnh gửi file và script
def keyboard_listener():
    while True:
        command = input("Enter 'send' to send the response: ")
        if command == "send":
            try:
                client_id = input("Enter the client_id to send response to: ")
                if client_id in clients:
                    send_file_and_script_to_client(client_id)
                else:
                    print(f"Client {client_id} is not connected.")
            except ValueError:
                print("Invalid command.")
        else:
            print("Unknown command")

if __name__ == '__main__':
    # Chạy server trên luồng riêng
    threading.Thread(target=keyboard_listener, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)

