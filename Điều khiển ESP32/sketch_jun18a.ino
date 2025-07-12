#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h> // Sử dụng thư viện servo dành riêng cho ESP32

// --- CẤU HÌNH PHẦN CỨNG ---
#define RST_PIN 22
#define SS_PIN  21
#define SERVO_PIN 13

MFRC522 rfid(SS_PIN, RST_PIN);
Servo myServo;

// Tốc độ Baud phải khớp với Python
#define UART_BAUDRATE 115200

// --- LOGIC QUẢN LÝ XE ---
const int NUM_CARDS = 4;
byte validUID[NUM_CARDS][4] = {
  {0xF4, 0x75, 0xF9, 0x04},
  {0x7F, 0xDC, 0x94, 0x1F},
  {0x03, 0xAA, 0xF8, 0x04},
  {0xFF, 0xC7, 0x98, 0xC2}
};

bool isInside[NUM_CARDS] = {false};
int availableSpots = 3;

//  Tạo một mảng để lưu biển số tương ứng với mỗi thẻ
String plateNumbers[NUM_CARDS];

// Biến quản lý trạng thái
bool waitingForPlate = false;
int lastScannedCardIndex = -1; // Lưu lại thẻ đang chờ xử lý

// --- HÀM HỖ TRỢ (Giữ nguyên) ---
String uidToString(byte *uid, byte len) {
  String uidStr = "";
  for (byte i = 0; i < len; i++) {
    if (uid[i] < 0x10) uidStr += "0";
    uidStr += String(uid[i], HEX);
  }
  return uidStr;
}

int getCardIndex(byte *uid) {
  for (int i = 0; i < NUM_CARDS; i++) {
    bool match = true;
    for (int j = 0; j < 4; j++) {
      if (uid[j] != validUID[i][j]) {
        match = false;
        break;
      }
    }
    if (match) return i;
  }
  return -1;
}

void openGate() {
  myServo.write(90);
  delay(3000);
  myServo.write(0);
}

void setup() {
  Serial.begin(UART_BAUDRATE);
  SPI.begin();
  rfid.PCD_Init();
  myServo.attach(SERVO_PIN);
  myServo.write(0);
  
  // Khởi tạo mảng biển số là các chuỗi rỗng
  for (int i = 0; i < NUM_CARDS; i++) {
    plateNumbers[i] = "";
  }
  
  while(!Serial); // Chờ cổng Serial sẵn sàng
  Serial.println("ESP32_READY");
  Serial.flush(); // Đảm bảo tín hiệu được gửi đi ngay
  
  Serial.println("He thong bai do xe AN NINH CAO san sang...");
  Serial.println("Cho trong: " + String(availableSpots));
}

//  Nâng cấp toàn bộ logic trong loop()
void loop() {
  // 1. Ưu tiên xử lý phản hồi từ Python khi đang chờ
  if (Serial.available() > 0 && waitingForPlate) {
    String data = Serial.readStringUntil('\n');
    data.trim();
    
    String receivedPlate = "";
    if (data.startsWith("BIENSO:")) {
      receivedPlate = data.substring(7); // Lấy phần biển số sau "BIENSO:"
    }
    
    // Logic được quyết định dựa trên trạng thái của thẻ TẠI THỜI ĐIỂM QUÉT
    // ---- XE VÀO ----
    if (isInside[lastScannedCardIndex] == false) { 
      if (receivedPlate != "") {
        Serial.println("Xe vao. Bien so da luu: " + receivedPlate);
        
        // Cập nhật trạng thái
        isInside[lastScannedCardIndex] = true;
        plateNumbers[lastScannedCardIndex] = receivedPlate;
        availableSpots--;
        
        openGate();
        Serial.println("Cho trong con lai: " + String(availableSpots));
      } else {
        Serial.println("Khong the vao do khong nhan dien duoc bien so.");
        // Không làm gì cả, xe không được vào.
      }
    }
    // ---- XE RA ----
    else { 
      if (receivedPlate != "") {
        Serial.println("Kiem tra xe ra. Bien so quet duoc: " + receivedPlate);
        Serial.println("   -> Bien so da luu tu truoc: " + plateNumbers[lastScannedCardIndex]);

        // *** SO SÁNH BIỂN SỐ ***
        if (receivedPlate == plateNumbers[lastScannedCardIndex]) {
          Serial.println("BIEN SO KHOP! Mo barie cho xe ra.");
          
          // Reset trạng thái
          isInside[lastScannedCardIndex] = false;
          plateNumbers[lastScannedCardIndex] = ""; // Xóa biển số đã lưu
          availableSpots++;
          
          openGate();
          Serial.println("Cho trong con lai: " + String(availableSpots));
        } else {
          Serial.println("SAI THE GUI XE! Bien so khong khop. Khong mo barie!");
          // Không làm gì cả, barie không mở, trạng thái xe vẫn là "đang ở trong"
        }
      } else {
        Serial.println(" Khong the ra do khong nhan dien duoc bien so. Vui long thu lai.");
      }
    }
    
    // Reset trạng thái chờ sau khi đã xử lý xong
    waitingForPlate = false;
    lastScannedCardIndex = -1;
  }

  // 2. Nếu đang chờ Python xử lý, không quét thẻ mới
  if (waitingForPlate) {
    return;
  }

  // 3. Quét thẻ mới
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  int index = getCardIndex(rfid.uid.uidByte);
  Serial.println("--------------------");
  Serial.print("Da quet the UID: ");
  Serial.println(uidToString(rfid.uid.uidByte, rfid.uid.size));

  if (index != -1) {
    // Luôn gửi yêu cầu nhận diện dù là xe vào hay xe ra
    if ( (isInside[index] == false && availableSpots > 0) || (isInside[index] == true) ) {
        waitingForPlate = true;
        lastScannedCardIndex = index;
        Serial.println("-> Dang gui yeu cau nhan dien bien so den PC...");
        Serial.println("TRIGGER_CAPTURE");
    } else if (isInside[index] == false && availableSpots <= 0) {
        Serial.println("Bai xe day! Khong the vao.");
    }
  } else {
    Serial.println("The khong hop le!");
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}