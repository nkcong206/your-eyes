package com.example.myapplication

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Environment
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
import com.example.myapplication.network.RetrofitClient
import com.example.myapplication.ui.theme.MyApplicationTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

class MainActivity : ComponentActivity() {

    private val TAG = "MainActivity"
    private val FILE_PATH = "/storage/emulated/0/Music/Alone.mp3"
    private val REQUEST_CODE_STORAGE_PERMISSION = 1

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
            startSendingFile()
        }
    }

    // Xử lý kết quả sau khi yêu cầu quyền
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_STORAGE_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                addLog("Storage permission granted!")
                startSendingFile()
            } else {
                addLog("Storage permission denied!")
            }
        }
    }

    // Hàm bắt đầu gửi tệp sau khi có quyền
    private fun startSendingFile() {
        addLog("Starting file sending process...")

        // Sử dụng lifecycleScope để khởi chạy một coroutine
        lifecycleScope.launch(Dispatchers.IO) {
            // Gọi hàm suspend sendFileToServer() từ bên trong coroutine
            val result = sendFileToServer()
            addLog(result) // Thêm kết quả của quá trình gửi file vào logs
        }
    }

    // Hàm gửi file tới server
    private suspend fun sendFileToServer(): String {
        return try {
            // Truy xuất tệp Alone.mp3 từ thư mục /storage/emulated/0/Music
            val file = File(FILE_PATH)

            // Kiểm tra tệp có tồn tại hay không
            if (!file.exists()) {
                addLog("File not found: ${file.absolutePath}")
                return "File not found!"
            }

            addLog("File found: ${file.absolutePath}")

            // Tạo RequestBody và MultipartBody cho file
            val requestFile = RequestBody.create("audio/mpeg".toMediaTypeOrNull(), file)
            val multipartBody = MultipartBody.Part.createFormData("file", file.name, requestFile)

            // Gửi yêu cầu upload file tới server Flask
            val response = RetrofitClient.instance.uploadFile(multipartBody).execute()

            // Kiểm tra phản hồi từ server
            if (response.isSuccessful) {
                addLog("Upload successful, receiving file from server...")
                val responseBody = response.body() ?: return "No file received"
                saveFileFromServer(responseBody.byteStream())
                return "File received and saved!"
            } else {
                addLog("Failed to upload: ${response.message()}")
                return "Failed to upload: ${response.message()}"
            }
        } catch (e: Exception) {
            e.printStackTrace()
            addLog("Exception: ${e.message}")
            return "Error: ${e.message}"
        }
    }

    // Hàm để lưu file Sunset.mp3 vào thư mục công cộng Music
    private fun saveFileFromServer(inputStream: InputStream) {
        val musicDir = File("/storage/emulated/0/Music")
        if (!musicDir.exists()) {
            musicDir.mkdirs() // Tạo thư mục nếu nó chưa tồn tại
        }

        val file = File(musicDir, "Sunset.mp3")
        try {
            FileOutputStream(file).use { output ->
                val buffer = ByteArray(4 * 1024) // buffer để đọc file
                var bytesRead: Int
                while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                    output.write(buffer, 0, bytesRead)
                }
                output.flush()
            }
            addLog("File Sunset.mp3 saved successfully to ${file.absolutePath}")
        } catch (e: Exception) {
            e.printStackTrace()
            addLog("Error saving file: ${e.message}")
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
