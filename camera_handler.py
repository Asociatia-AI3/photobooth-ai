# photobooth_ai/camera_handler.py
import cv2
import config
import time

class CameraHandler:
    def __init__(self):
        self.camera_index = config.CAMERA_INDEX
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            raise IOError(f"Cannot open webcam at index {self.camera_index}")

        # Setează rezoluția dorită
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_RESOLUTION_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_RESOLUTION_HEIGHT)
        
        # Verifică rezoluția setată (camera poate să nu suporte exact ce ai cerut)
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Camera initialized. Requested resolution: {config.CAMERA_RESOLUTION_WIDTH}x{config.CAMERA_RESOLUTION_HEIGHT}, "
              f"Actual resolution: {actual_width}x{actual_height}")

        self.qr_detector = cv2.QRCodeDetector()

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Can't receive frame (stream end?).")
            return None
        return frame

    def detect_qr_code(self, frame):
        """
        Detects a QR code in the given frame.
        Returns the decoded data as a string if a QR code is found and decoded, otherwise None.
        """
        if frame is None:
            return None
            
        # Convert to grayscale for better QR detection (optional, detector might do it)
        # gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        try:
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            if bbox is not None and data:
                # bbox is an array of vertices of the found QR code
                # data is the decoded string
                # print(f"QR Detected: {data}") # For debugging
                return data
        except Exception as e:
            print(f"Error during QR code detection: {e}")
        return None

    def capture_photo(self, filename=config.CAPTURED_PHOTO_FILENAME):
        frame = self.get_frame()
        if frame is not None:
            try:
                cv2.imwrite(filename, frame)
                print(f"Photo captured and saved to {filename}")
                return filename
            except Exception as e:
                print(f"Error saving photo: {e}")
                return None
        return None

    def release(self):
        self.cap.release()
        print("Camera released.")

if __name__ == '__main__':
    # Test camera handler (needs a working camera)
    # Acest test va încerca să deschidă camera, să afișeze feed-ul și să detecteze QR-uri.
    # Apasă 'q' pentru a închide fereastra de test.
    
    # Mock config for testing if not run from main project
    class MockConfig:
        CAMERA_INDEX = 0
        CAMERA_RESOLUTION_WIDTH = 640
        CAMERA_RESOLUTION_HEIGHT = 480
        CAPTURED_PHOTO_FILENAME = "test_capture.jpg"
        TEMP_DIR = "temp" # Asigură-te că există directorul 'temp'

    # Use actual config if available, else mock
    try:
        import config as app_config
    except ImportError:
        app_config = MockConfig()
        print("Using MockConfig for camera_handler test.")
        import os
        if not os.path.exists(app_config.TEMP_DIR):
            os.makedirs(app_config.TEMP_DIR)
        app_config.CAPTURED_PHOTO_FILENAME = os.path.join(app_config.TEMP_DIR, "test_capture.jpg")


    try:
        cam = CameraHandler()
        print("CameraHandler initialized for testing.")
        
        start_time = time.time()
        frames_processed = 0
        
        cv2.namedWindow("Camera Test - Press 'q' to quit, 'c' to capture", cv2.WINDOW_NORMAL)

        while True:
            frame = cam.get_frame()
            if frame is None:
                print("Failed to get frame. Exiting test.")
                break

            display_frame = frame.copy() # Lucrează pe o copie pentru a nu modifica frame-ul original
            
            qr_data = cam.detect_qr_code(frame)
            if qr_data:
                # Desenează un chenar în jurul QR-ului detectat dacă bbox este disponibil
                # (bbox nu este direct returnat de funcția mea simplificată, dar qr_detector.detectAndDecode returnează)
                # Pentru simplitate, doar printăm datele.
                # Pentru a desena:
                # _, bbox_points, _ = cam.qr_detector.detectAndDecode(frame)
                # if bbox_points is not None:
                #    nr_points = len(bbox_points[0])
                #    for i in range(nr_points):
                #        pt1 = tuple(map(int, bbox_points[0][i]))
                #        pt2 = tuple(map(int, bbox_points[0][(i + 1) % nr_points]))
                #        cv2.line(display_frame, pt1, pt2, (0, 255, 0), 3)

                cv2.putText(display_frame, f"QR: {qr_data}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Camera Test - Press 'q' to quit, 'c' to capture", display_frame)
            frames_processed += 1

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                photo_path = cam.capture_photo(filename=app_config.CAPTURED_PHOTO_FILENAME)
                if photo_path:
                    print(f"Photo captured to {photo_path} during test.")
                else:
                    print("Failed to capture photo during test.")

        end_time = time.time()
        duration = end_time - start_time
        fps = frames_processed / duration if duration > 0 else 0
        print(f"Test finished. Processed {frames_processed} frames in {duration:.2f} seconds ({fps:.2f} FPS).")

    except IOError as e:
        print(f"Camera Test Error: {e}. Make sure a camera is connected and accessible.")
    except Exception as e:
        print(f"An unexpected error occurred during camera test: {e}")
    finally:
        if 'cam' in locals() and cam:
            cam.release()
        cv2.destroyAllWindows()
        print("Camera test resources released.")
