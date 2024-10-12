# Send mp3 file



Code trong có 2 phần:

server và client



Để chạy được code, cần làm những bước sau:

1. Cài đặt các thư viện để run code server python từ Pip là Flask, request, jsonify, send_file

2. cấu hình firewall cho phép cổng `5000` để k bị chặn, cấu hình trên win thì phải tự tìm thôi

3. chạy server  bằng lệnh: python server.py

4. Check địa chỉ IP trên máy tính dùng để run code Server, sửa địa chỉ này bên trong code android

5. Sửa đường dẫn bên trong 2 file Server vì đường dẫn trên linux khác
   
   lưu file Alone.mp3 vào trong folder /storage/emulated/0/Music trên android
   
   Trong code Kotlin đã sửa những file sau: AndroidManifest.xml, network_security_config.xml, build.gradle.kts 
   
   