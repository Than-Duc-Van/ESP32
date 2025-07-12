import numpy as np
import cv2
import sys


# khai báo ban đầu 
MIN_CONTOUR_AREA = 40   #Lọc bỏ các đường viền (contour)

#Chuẩn hóa kích thước ký tự
RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30


def main():
    import os
    img_path = os.path.join(os.path.dirname(__file__), "training_chars.png")
    imgTrainingNumbers = cv2.imread(img_path)


    
    imgGray = cv2.cvtColor(imgTrainingNumbers, cv2.COLOR_BGR2GRAY)          # lấy ảnh thang độ xám
    imgBlurred = cv2.GaussianBlur(imgGray, (5,5), 0)                        # làm mờ

    # phân tách kí tự ra khỏi nềnnền
    imgThresh = cv2.adaptiveThreshold(imgBlurred,                           # ảnh đầu vào
                                      255,                                  # làm cho các pixel vượt qua ngưỡng thành màu trắng hoàn toàn
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,       
                                      cv2.THRESH_BINARY_INV,                # đảo ngược để nền trước có màu trắng, nền sau có màu đen
                                      11,                                   # kích thước của vùng lân cận pixel được sử dụng để tính giá trị ngưỡng
                                      2)                                    # hằng số trừ khỏi giá trị trung bình hoặc giá trị trung bình có trọng số

    cv2.imshow("imgThresh", imgThresh)      

    imgThreshCopy = imgThresh.copy()        


    npaContours, hierarchy = cv2.findContours(imgThreshCopy,        #tìm đường bao của từng kí tựự
                                                 cv2.RETR_EXTERNAL,                 
                                                 cv2.CHAIN_APPROX_SIMPLE)           

                                
    npaFlattenedImages =  np.empty((0, RESIZED_IMAGE_WIDTH * RESIZED_IMAGE_HEIGHT))
   

    intClassifications = []         

                                    #các kí tự có thể nhận diện
    intValidChars = [ord('0'), ord('1'), ord('2'), ord('3'), ord('4'), ord('5'), ord('6'), ord('7'), ord('8'), ord('9'),
                     ord('A'), ord('B'), ord('C'), ord('D'), ord('E'), ord('F'), ord('G'), ord('H'), ord('I'), ord('J'),
                     ord('K'), ord('L'), ord('M'), ord('N'), ord('O'), ord('P'), ord('Q'), ord('R'), ord('S'), ord('T'),
                     ord('U'), ord('V'), ord('W'), ord('X'), ord('Y'), ord('Z')] #Là mã ascii của mấy chữ này

    #tạokhung quanh đối tượng (ký tự) quanh bao, cắt và gán nhãn kí tự
    for npaContour in npaContours:                          
        if cv2.contourArea(npaContour) > MIN_CONTOUR_AREA:          
            [intX, intY, intW, intH] = cv2.boundingRect(npaContour)         

                                                
            cv2.rectangle(imgTrainingNumbers,           
                          (intX, intY),                
                          (intX+intW,intY+intH),        
                          (0, 0, 255),                 
                          2)                            

            imgROI = imgThresh[intY:intY+intH, intX:intX+intW]                                  
            imgROIResized = cv2.resize(imgROI, (RESIZED_IMAGE_WIDTH, RESIZED_IMAGE_HEIGHT))     

            cv2.imshow("imgROI", imgROI)                    # ảnh gốc cắt ra ký tự
            cv2.imshow("imgROIResized", imgROIResized)      # ảnh đã chuẩn hóa kích thước
            
            cv2.imshow("training_numbers.png", imgTrainingNumbers)      # ảnh gốc

            intChar = cv2.waitKey(0)                     # gõ phím tương ứngứng

            if intChar == 27:                   # nhấn ESC (mã 27) → thoát chương trình
                sys.exit() 
            elif intChar in intValidChars:      # ký tự nhập nằm trong danh sách 0–9 hoặc A–Z thì Thêm mã ASCII vào danh sách intClassifications

                intClassifications.append(intChar)       
                #Là file chứa label của tất cả các ảnh mẫu, tổng cộng có 32 x 5 = 160 mẫu.
                #Làm phẳng ảnh và lưu
                npaFlattenedImage = imgROIResized.reshape((1, RESIZED_IMAGE_WIDTH * RESIZED_IMAGE_HEIGHT))  
                
                npaFlattenedImages = np.append(npaFlattenedImages, npaFlattenedImage, 0)                    
                
            # end if
        # end if
    # end for

    #Chuyển danh sách nhãn sang numpy array, rồi reshape thành vector cột
    fltClassifications = np.array(intClassifications, np.float32)                   
    npaClassifications = fltClassifications.reshape((fltClassifications.size, 1))   

    print ("\n\ntraining complete !!\n")

    np.savetxt("classifications1.txt", npaClassifications)           # lưu dữ liệu vào filefile
    np.savetxt("flattened_images1.txt", npaFlattenedImages)          

    cv2.destroyAllWindows()             

    return


if __name__ == "__main__":
    main()
# end if
