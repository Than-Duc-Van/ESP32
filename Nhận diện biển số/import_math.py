import serial
import time
import cv2
import numpy as np
import math
import Preprocess
 
# --- CẤU HÌNH ---
SERIAL_PORT = 'COM8'
BAUD_RATE = 115200
CAMERA_SOURCE = 'http://192.168.2.84:8080/video' # Nguồn camera của bạn
RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30
 
# --- HÀM NHẬN DIỆN BIỂN SỐ  ---
def recognize_license_plate(frame, kNearest):
    
    # 1. Tiền xử lý ảnh đầu vào
    imgGrayscaleplate, imgThreshplate = Preprocess.preprocess(frame)
    canny_image = cv2.Canny(imgThreshplate, 250, 255)
    kernel = np.ones((3, 3), np.uint8)
    dilated_image = cv2.dilate(canny_image, kernel, iterations=1)
 
    # 2. Tìm các đường viền và lọc ra các vùng nghi là biển số
    contours, hierarchy = cv2.findContours(dilated_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
   
    screenCnt_list = []
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.06 * peri, True)
        if len(approx) == 4:
            [x, y, w, h] = cv2.boundingRect(approx)
            ratio = w / h
            # Tinh chỉnh lại ratio cho phù hợp với cả biển dài và biển vuông
            if (0.8 <= ratio <= 1.5) or (3.5 <= ratio <= 6.5):
                screenCnt_list.append(approx)
 
    if not screenCnt_list:
        print("-> Buoc 2: Khong tim thay vung bien so kha nghi.")
        return None
 
    # 3. Lặp qua các vùng khả nghi để xử lý
    for screenCnt in screenCnt_list:
       
        # ---  TÍNH TOÁN VÀ KHỬ GÓC NGHIÊNG ---
        # Sắp xếp các điểm của contour xác định thứ tự 4 góc hình chữ nhật
        points = screenCnt.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
 
        s = points.sum(axis=1)
        rect[0] = points[np.argmin(s)]  # trên - trái
        rect[2] = points[np.argmax(s)]  #trên - phải
 
        diff = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diff)]   #dưới - trái
        rect[3] = points[np.argmax(diff)]   #dưới - phải
       
        (tl, tr, br, bl) = rect
       
        # Tính toán chiều rộng, chiều cao mới của ảnh sau khi làm thẳng
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
 
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
       
        # Tạo ma trận chuyển đổi và áp dụng để khử nghiêng làm thẳng ảnh
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
       
        M = cv2.getPerspectiveTransform(rect, dst)
        # Cắt và làm thẳng biển số từ ảnh gốc (frame)
        straightened_plate = cv2.warpPerspective(frame, M, (maxWidth, maxHeight))
        #------------------------------------------------------------
 
        # 4. Phân đoạn và nhận diện ký tự trên biển số ĐÃ LÀM THẲNG
        if straightened_plate.shape[0] == 0 or straightened_plate.shape[1] == 0:
            continue # Bỏ qua nếu biển số bị lỗi sau khi warp
 
        # Tiền xử lý lại biển số đã được làm thẳng để tăng độ chính xác
        _, plate_thresh = Preprocess.preprocess(straightened_plate)
       
        # Tăng cường độ nét cho ký tự
        kerel3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thre_mor = cv2.morphologyEx(plate_thresh, cv2.MORPH_DILATE, kerel3)
        cont, hier = cv2.findContours(thre_mor, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
 
        char_x_ind = {}
        char_x = []
        height, width, _ = straightened_plate.shape
        roiarea = height * width
 
        for ind, cnt in enumerate(cont):
            area = cv2.contourArea(cnt)
            (x_char, y_char, w_char, h_char) = cv2.boundingRect(cont[ind])
            if h_char == 0: continue
            ratiochar = w_char / h_char
           
            # Các hằng số lọc ký tự
            MIN_CHAR_AREA_RATIO = 0.01
            MAX_CHAR_AREA_RATIO = 0.09
            MIN_CHAR_RATIO = 0.2
            MAX_CHAR_RATIO = 0.8
 
            if (MIN_CHAR_AREA_RATIO * roiarea < area < MAX_CHAR_AREA_RATIO * roiarea) and (MIN_CHAR_RATIO < ratiochar < MAX_CHAR_RATIO):
                if x_char in char_x: x_char += 1
                char_x.append(x_char)
                char_x_ind[x_char] = ind
 
        if len(char_x) in range(7, 10):
            print(f"-> Buoc 3: Tim thay vung co {len(char_x)} ky tu. Dang nhan dien...")
           
            char_x = sorted(char_x)
            first_line, second_line = "", ""
 
            for i in char_x:
                (x, y, w, h) = cv2.boundingRect(cont[char_x_ind[i]])
                imgROI = thre_mor[y:y + h, x:x + w]
               
                imgROIResized = cv2.resize(imgROI, (RESIZED_IMAGE_WIDTH, RESIZED_IMAGE_HEIGHT))
                npaROIResized = imgROIResized.reshape((1, RESIZED_IMAGE_WIDTH * RESIZED_IMAGE_HEIGHT))
                npaROIResized = np.float32(npaROIResized)
               
                _, npaResults, _, _ = kNearest.findNearest(npaROIResized, k=3)
                strCurrentChar = str(chr(int(npaResults[0][0])))
               
                if (y < height / 2): # Dùng tách dòng chính xác 
                    first_line += strCurrentChar
                else:
                    second_line += strCurrentChar
           
            # Ghép và làm sạch biển số
            strFinalString = (first_line + second_line).replace("-", "").replace(".", "")
            print(f"-> Buoc 4: Ket qua nhan dien: {first_line} - {second_line}")
           
            if len(strFinalString) > 6:
                return strFinalString # *** Trả về kết quả ngay khi tìm thấy ***
 
    # Nếu lặp qua tất cả các contour mà không tìm thấy biển số hợp lệ
    print("-> Buoc 5: Khong tim thay bien so hop le sau khi xu ly cac vung.")
    return None
 
def main():
    # --- KHỞI TẠO ---
    # 1. Load KNN model
    try:
        
        npaClassifications = np.loadtxt("classifications1.txt", np.float32)
        npaFlattenedImages = np.loadtxt("flattened_images1.txt", np.float32)
        npaClassifications = npaClassifications.reshape((npaClassifications.size, 1))
        kNearest = cv2.ml.KNearest_create()
        kNearest.train(npaFlattenedImages, cv2.ml.ROW_SAMPLE, npaClassifications)
        print("Da load model KNN thanh cong.")
    except Exception as e:
        print(f"Loi: Khong the load model KNN. Vui long kiem tra file .txt. {e}")
        return
 
    # 2. Khởi tạo kết nối Serial (Giữ nguyên)
    try:
        esp32 = serial.Serial(port=SERIAL_PORT, baudrate=BAUD_RATE, timeout=2)
        print(f"Dang mo cong {SERIAL_PORT} voi toc do {BAUD_RATE}...")
    except serial.SerialException as e:
        print(f"Loi: Khong the mo cong {SERIAL_PORT}. {e}")
        return
 
    # 3. Khởi tạo camera (Giữ nguyên)
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        print(f"Loi: Khong the mo camera tu nguon: {CAMERA_SOURCE}")
        esp32.close()
        return
 
    # --- GIAI ĐOẠN HANDSHAKE (Giữ nguyên) ---
    is_esp32_ready = False
    while not is_esp32_ready:
        if esp32.in_waiting > 0:
            line = esp32.readline().decode('utf-8').strip()
            if line == "ESP32_READY":
                print(">>> Da ket noi thanh cong voi ESP32! <<<")
                print(">>> Camera da bat. He thong san sang. <<<")
                is_esp32_ready = True
        else:
            print("Dang cho tin hieu tu ESP32...")
            time.sleep(1)
 
    # --- VÒNG LẶP CHÍNH (Giữ nguyên) ---
    try:
        while True:
            ret, frame = cap.read()
            if ret:
                display_frame = cv2.resize(frame, (800, 600)) # Resize để hiển thị nhỏ hơn
                cv2.imshow('He thong giam sat bai do xe - Cho yeu cau...', display_frame)
           
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
 
            if esp32.in_waiting > 0:
                request = esp32.readline().decode('utf-8').strip()
                print(f"\n[NHAN YEU CAU] Tu ESP32: {request}")
 
                if request == "TRIGGER_CAPTURE":
                    ret, frame_to_process = cap.read()
                   
                    if ret:
                        # Gọi hàm nhận diện NÂNG CẤP
                        plate = recognize_license_plate(frame_to_process, kNearest)
 
                        if plate:
                            response = f"BIENSO:{plate}\n"
                            print(f"[GUI PHAN HOI] Da gui bien so: {plate}")
                        else:
                            response = "NO_PLATE\n"
                            print("[GUI PHAN HOI] Khong nhan dien duoc, da gui NO_PLATE.")
                       
                        esp32.write(response.encode('utf-8'))
                        print(f"----------------------------------------")
                    else:
                        print("Loi: Khong the chup anh tu camera de xu ly.")
                        esp32.write("CAPTURE_FAIL\n".encode('utf-8'))
 
    except KeyboardInterrupt:
        print("Dung chuong trinh.")
    finally:
        esp32.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Da dong cong Serial va giai phong camera.")
 
if __name__ == '__main__':
    main()