import os
import requests
import socketio

# Thiết lập socket client
sio = socketio.Client()

# Đường dẫn thư mục để lưu file nhận được
ANSWERS_FOLDER = '/home/nkcong206/Desktop/client/answers'
QUESTIONS_FOLDER = '/home/nkcong206/Desktop/client/questions'

id = 'client_1234'
# Kết nối đến server và gửi ID
@sio.event
def connect():
    print("Connected to server!!!")
    sio.emit('connect', {'id': id})

# Nhận file và script từ server
@sio.on('receive_file')
def on_receive_file(data):
    print(f"Bot: {data['script']}")

    # URL để tải file từ server
    download_url = f"http://localhost:5000/download"

    # Tải file từ server
    response = requests.get(download_url)

    if response.status_code == 200:
        # Đường dẫn đầy đủ để lưu file
        file_path = os.path.join(ANSWERS_FOLDER, data['filename'])
        
        # Lưu file vào thư mục
        with open(file_path, 'wb') as f:
            f.write(response.content)
    else:
        print(f"Failed to download file. Status code: {response.status_code}")

# Xử lý khi mất kết nối
@sio.event
def disconnect():
    print("Disconnected from server")

# Function để gửi file lên server
def send_file_to_server(file_name):
    file_path = os.path.join(QUESTIONS_FOLDER, file_name + ".mp3")
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(file_path):
        print(f"File '{file_name}' does not exist in {QUESTIONS_FOLDER}")
        return

    # Gửi file lên server với tham số client_id
    with open(file_path, 'rb') as f:
        files = {'file': f}
        # Thêm client_id vào tham số request
        params = {'client_id': id}
        response = requests.post('http://localhost:5000/upload', files=files, params=params)
        if response.status_code == 200:
            server_response = response.json()
            if 'script' in server_response:
                print(f"User: {server_response['script']}")
            # Kiểm tra nếu có yêu cầu upload ảnh
            if "request" in server_response and server_response["request"] == "upload an image":
                image_file_name = 'table.png'
                upload_image_to_server(image_file_name)
        else:
            print(f"Failed to upload file. Status code: {response.status_code}")

# Function để gửi ảnh lên server
def upload_image_to_server(image_file_name):
    image_path = os.path.join(QUESTIONS_FOLDER, image_file_name)

    # Kiểm tra xem file ảnh có tồn tại không
    if not os.path.exists(image_path):
        print(f"Image file '{image_file_name}' does not exist in {QUESTIONS_FOLDER}")
        return

    # Gửi ảnh lên server với client_id
    with open(image_path, 'rb') as f:
        files = {'file': f}
        params = {'client_id': id}
        response = requests.post('http://localhost:5000/upload_image', files=files, params=params)
        if response.status_code != 200:
            print(f"Failed to upload image. Status code: {response.status_code}")


if __name__ == '__main__':
    # Kết nối đến server WebSocket
    sio.connect(f'http://localhost:5000?id={id}')

    while True:
        # Người dùng nhập tên file muốn gửi
        file_name = input("")
        # Gửi file lên server theo tên file đã nhập
        send_file_to_server(file_name)

    sio.wait()

