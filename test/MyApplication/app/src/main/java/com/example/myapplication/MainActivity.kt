package com.example.myapplication

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.ui.theme.MyApplicationTheme
import io.socket.client.IO
import io.socket.client.Socket
import io.socket.emitter.Emitter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import java.io.File
import java.io.FileOutputStream

class MainActivity : ComponentActivity() {

    private val TAG = "MainActivity"
    private val FILE_PATH = "/storage/emulated/0/Music/client.mp3"
    private val SERVER_MP3_PATH = "/storage/emulated/0/Music/server.mp3"
    private val REQUEST_CODE_STORAGE_PERMISSION = 1
    private lateinit var mSocket: Socket // Socket object

    // Tạo danh sách log để hiển thị trên UI
    private val logs = mutableStateListOf<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Kiểm tra và yêu cầu quyền truy cập bộ nhớ
        checkStoragePermission()

        setContent {
            MyApplicationTheme {
                // Hiển thị danh sách các log trên UI
                DisplayLogs(logs)
            }
        }

        // Cấu hình kết nối Socket.IO để nhận file qua WebSocket
        try {
            val options = IO.Options()
            options.transports = arrayOf("websocket")  // Sử dụng WebSocket thay vì polling
            options.reconnection = true
            options.query = "client_id=client_1234"  // Gán client_id

            mSocket = IO.socket("http://192.168.1.9:5000", options)
        } catch (e: Exception) {
            addLog("Error while creating socket: ${e.message}")
            e.printStackTrace()
            return
        }

        // Lắng nghe sự kiện kết nối thành công
        mSocket.on(Socket.EVENT_CONNECT, Emitter.Listener {
            addLog("Socket connected")
            // Sau khi kết nối thành công WebSocket, mới upload file
            uploadFileToServer() // Gửi tệp đến server qua API
        })

        // Lắng nghe sự kiện nhận tệp từ server qua WebSocket
        mSocket.on("receive_file", Emitter.Listener { args ->
            try {
                if (args.isNotEmpty()) {
                    val fileData = args[0] as ByteArray
                    saveFileFromServer(fileData) // Lưu file server.mp3
                }
            } catch (e: Exception) {
                addLog("Error receiving file: ${e.message}")
                e.printStackTrace()
            }
        })

        // Lắng nghe lỗi kết nối
        mSocket.on(Socket.EVENT_CONNECT_ERROR, Emitter.Listener { args ->
            addLog("Connection error: ${args.joinToString()}")
        })

        // Lắng nghe khi kết nối bị ngắt
        mSocket.on(Socket.EVENT_DISCONNECT, Emitter.Listener {
            addLog("Socket disconnected")
        })

        // Kết nối socket
        try {
            mSocket.connect()
        } catch (e: Exception) {
            addLog("Error connecting socket: ${e.message}")
            e.printStackTrace()
        }

        // Gửi file sau khi có quyền lưu trữ
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
            == PackageManager.PERMISSION_GRANTED) {
            uploadFileToServer() // Gửi tệp đến server qua API
        }
    }

    // Hàm để thêm log và cập nhật UI
    private fun addLog(message: String) {
        logs.add(message) // Thêm log vào danh sách logs
        Log.d(TAG, message) // Ghi log ra Logcat
    }

    // Kiểm tra quyền truy cập bộ nhớ ngoài
    private fun checkStoragePermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
            != PackageManager.PERMISSION_GRANTED) {
            addLog("Requesting storage permission")
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE), REQUEST_CODE_STORAGE_PERMISSION)
        } else {
            addLog("Storage permission already granted")
        }
    }

    // Xử lý kết quả sau khi yêu cầu quyền
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_STORAGE_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                addLog("Storage permission granted!")
                uploadFileToServer()
            } else {
                addLog("Storage permission denied!")
            }
        }
    }

    // Hàm để upload file qua API POST /upload
    private fun uploadFileToServer() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val file = File(FILE_PATH)
                if (!file.exists()) {
                    addLog("File not found: ${file.absolutePath}")
                    return@launch
                }

                // Tạo RequestBody và MultipartBody cho file
                val requestFile = RequestBody.create("audio/mpeg".toMediaTypeOrNull(), file)
                val multipartBody = MultipartBody.Part.createFormData("file", file.name, requestFile)

                // Gửi yêu cầu upload file tới server Flask
                val retrofit = Retrofit.Builder()
                    .baseUrl("http://192.168.1.9:5000/")  // Thay bằng địa chỉ IP server của bạn
                    .build()

                val service = retrofit.create(UploadService::class.java)
                val call = service.uploadFile(multipartBody)

                // Xử lý phản hồi từ server
                call.enqueue(object : Callback<ResponseBody> {
                    override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                        if (response.isSuccessful) {
                            addLog("File uploaded successfully")
                        } else {
                            addLog("File upload failed: ${response.message()}")
                        }
                    }

                    override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                        addLog("Upload error: ${t.message}")
                    }
                })

            } catch (e: Exception) {
                e.printStackTrace()
                addLog("Exception: ${e.message}")
            }
        }
    }

    // Interface cho Retrofit để gửi tệp đến API Flask
    interface UploadService {
        @Multipart
        @POST("upload?client_id=client_1234")
        fun uploadFile(@Part file: MultipartBody.Part): Call<ResponseBody>
    }

    // Hàm để lưu file server.mp3 vào thư mục công cộng Music
    private fun saveFileFromServer(fileData: ByteArray) {
        try {
            val musicDir = File("/storage/emulated/0/Music")
            if (!musicDir.exists()) {
                musicDir.mkdirs() // Tạo thư mục nếu nó chưa tồn tại
            }

            val file = File(musicDir, "server.mp3")
            FileOutputStream(file).use { output ->
                output.write(fileData)
                output.flush()
            }
            addLog("File server.mp3 saved successfully to ${file.absolutePath}")
        } catch (e: Exception) {
            addLog("Error saving file: ${e.message}")
            e.printStackTrace()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            mSocket.disconnect() // Ngắt kết nối socket khi ứng dụng bị hủy
        } catch (e: Exception) {
            addLog("Error disconnecting socket: ${e.message}")
        }
    }
}

@Composable
fun DisplayLogs(logs: List<String>) {
    Column {
        for (log in logs) {
            Text(text = log) // Hiển thị từng dòng log
        }
    }
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    MyApplicationTheme {
        DisplayLogs(listOf("Log 1", "Log 2", "Log 3")) // Preview với các log mẫu
    }
}
