# photobooth_ai/main.py
import time
import os
import sys
import signal # Pentru a prinde CTRL+C

# Adaugă directorul curent în sys.path pentru a permite importurile relative
# dacă rulezi direct main.py și structura de directoare este corectă.
# current_dir = os.path.dirname(os.path.abspath(__file__))
# if current_dir not in sys.path:
#    sys.path.append(current_dir)

try:
    import config
    import display_manager
    import camera_handler
    import api_client
    import voice_interaction
    import s3_uploader
    import qr_generator
except ImportError as e:
    print(f"Critical Import Error: {e}. One or more modules are missing or not installed.")
    print("Please ensure all dependencies are installed (pygame, opencv-python, google-cloud-texttospeech, google-cloud-speech, boto3, qrcode[pil], sounddevice, soundfile, requests).")
    print("Also, ensure all .py files (config.py, display_manager.py, etc.) are in the same directory or PYTHONPATH is set correctly.")
    sys.exit(1) # Termină programul dacă modulele esențiale lipsesc


class PhotoboothApp:
    def __init__(self):
        print("Initializing Photobooth AI...")
        try:
            self.display = display_manager.DisplayManager()
            self.camera = camera_handler.CameraHandler()
            self.voice = voice_interaction.VoiceInteraction()
            self.s3 = s3_uploader.S3Uploader()
            # qr_generator este folosit ca modul, nu neapărat ca o clasă cu stare
        except Exception as e:
            print(f"Error during initialization of components: {e}")
            # Încearcă să închizi ce s-a deschis
            if hasattr(self, 'display') and self.display: self.display.quit()
            if hasattr(self, 'camera') and self.camera: self.camera.release()
            sys.exit(1)

        self.running = True
        self.session_active = False # Indică dacă o sesiune cu un utilizator este în desfășurare

        # Handle SIGINT (Ctrl+C) gracefully
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        print("\nCtrl+C detected. Shutting down gracefully...")
        self.running = False
        # Dacă suntem într-o sesiune, încercăm să o oprim mai curat, dar pentru simplitate aici doar oprim loop-ul principal.
        # O oprire mai complexă ar putea implica anularea task-urilor curente.

    def run_initial_state(self):
        self.display.show_initial_screen()
        qr_code_data = None
        while self.running and not qr_code_data:
            frame = self.camera.get_frame()
            if frame is None:
                time.sleep(0.1) # Așteaptă puțin dacă nu primește frame
                continue
            
            # Afișează feed-ul camerei cu instrucțiunile inițiale (opțional, sau doar logo)
            # Pentru acest flow, logo-ul și instrucțiunile sunt deja afișate de show_initial_screen.
            # Dacă vrei să arăți și camera în acest stadiu, decomentează:
            # self.display.show_camera_feed(frame, instructions=config.TEXT_INITIAL_INSTRUCTIONS_LINE1)
            
            qr_code_data = self.camera.detect_qr_code(frame)
            if qr_code_data:
                print(f"QR Code detected: {qr_code_data}")
                break # Ieși din bucla de scanare QR
            
            # Verifică evenimentele Pygame (ex: închiderea ferestrei)
            for event in pygame.event.get(): # Necesită `import pygame` în acest fișier sau în display_manager
                if event.type == pygame.QUIT:
                    self.running = False
                    break
            if not self.running: break
            
            time.sleep(0.05) # Mică pauză pentru a nu suprasolicita CPU
        
        return qr_code_data

    def process_photo_session(self, ticket_info):
        self.session_active = True
        
        # 1. Salut vocal
        greeting = config.VOICE_GREETING_TEMPLATE.format(
            ticket_holder_name=ticket_info.get("ticket_holder_name", "Participant"),
            purchaser_name=ticket_info.get("purchaser_name", "Cumpărătorul")
        )
        self.voice.speak(greeting)
        time.sleep(0.5) # Pauză scurtă după salut

        # 2. Instrucțiuni vocale pentru poziționare
        self.voice.speak(config.VOICE_INSTRUCTION_POSITION)
        self.voice.speak(config.VOICE_INSTRUCTION_CONFIRM)

        # 3. Afișează feed-ul camerei pe TV
        confirmation_received = False
        max_confirmation_attempts = 3
        attempts = 0

        while self.running and self.session_active and attempts < max_confirmation_attempts and not confirmation_received:
            frame_for_display = self.camera.get_frame() # Ia un frame nou pentru afișare
            if frame_for_display is not None:
                 self.display.show_camera_feed(frame_for_display, instructions=config.TEXT_CAMERA_FEED_INSTRUCTIONS)
            
            # Ascultă pentru confirmare
            # S-ar putea să vrei să rulezi ascultarea într-un thread separat dacă e blocantă
            # și vrei ca feed-ul camerei să se actualizeze continuu.
            # Pentru simplitate, aici este secvențial.
            if self.voice.listen_for_confirmation(duration_seconds=5): # Ascultă pentru 5 secunde
                self.voice.speak(config.VOICE_CONFIRMATION_ACKNOWLEDGED)
                confirmation_received = True
                break
            else:
                attempts += 1
                if attempts < max_confirmation_attempts:
                    self.voice.speak(config.VOICE_CONFIRMATION_NOT_HEARD)
                else:
                    self.voice.speak("Nu am primit confirmarea după mai multe încercări. Sesiunea se încheie.")
                    self.session_active = False # Încheie sesiunea dacă nu se primește confirmare
                    return # Ieși din funcția de procesare a sesiunii

            # Verifică evenimentele Pygame (ex: închiderea ferestrei)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False; self.session_active = False; break
            if not self.running or not self.session_active: break
        
        if not self.running or not self.session_active or not confirmation_received:
            print("Session ended prematurely or confirmation not received.")
            return

        # 4. Numărătoare inversă și captură foto
        for i in range(config.COUNTDOWN_SECONDS, 0, -1):
            current_frame_for_countdown = self.camera.get_frame() # Ia frame-ul curent
            self.display.show_countdown(i, current_frame=current_frame_for_countdown)
            # Redă un sunet scurt pentru fiecare număr (opțional)
            # self.voice.speak(str(i)) # Poate fi prea lent, mai bine un sunet preînregistrat
            time.sleep(1)
            if not self.running: return

        self.display.show_message("ZÂMBIIIIȚI!", duration_ms=500) # Sau un flash de ecran
        
        photo_path = self.camera.capture_photo()
        if not photo_path:
            self.voice.speak(config.VOICE_ERROR_GENERIC + " Nu am putut captura fotografia.")
            self.display.show_message("Eroare la captură foto!", duration_ms=3000)
            self.session_active = False
            return
        
        self.voice.speak(config.VOICE_PHOTO_SUCCESS)
        self.display.show_message(config.TEXT_PROCESSING, duration_ms=1000)

        # 5. Upload pe S3 și obținere link
        download_url = self.s3.upload_file(photo_path)
        
        if not download_url:
            self.voice.speak(config.VOICE_ERROR_GENERIC + " Nu am putut încărca fotografia.")
            self.display.show_message("Eroare la upload S3!", duration_ms=3000)
            # Poți decide să oferi o opțiune de reîncercare sau să salvezi local
            self.session_active = False
            return

        # 6. Generează QR pentru download și afișează-l
        # Poți folosi logo-ul evenimentului și în QR-ul de download
        qr_image_path = qr_generator.generate_qr_code_image(download_url, 
                                                            filename=config.DOWNLOAD_QR_FILENAME,
                                                            add_logo=True, # Opțional
                                                            logo_path=config.LOGO_PATH if os.path.exists(config.LOGO_PATH) else None)
        
        if qr_image_path:
            self.display.show_qr_code(qr_image_path)
            time.sleep(config.QR_DISPLAY_TIME_SECONDS)
        else:
            self.voice.speak(config.VOICE_ERROR_GENERIC + " Nu am putut genera codul QR pentru download.")
            self.display.show_message("Eroare generare QR!", "Link: " + download_url, duration_ms=5000) # Afișează link-ul text

        # Curăță fotografia locală și QR-ul temporar (opțional, dar bun pentru spațiu)
        try:
            if os.path.exists(photo_path): os.remove(photo_path)
            if os.path.exists(config.DOWNLOAD_QR_FILENAME): os.remove(config.DOWNLOAD_QR_FILENAME)
        except OSError as e:
            print(f"Error deleting temporary files: {e}")

        self.session_active = False
        print("Photo session finished.")


    def main_loop(self):
        while self.running:
            self.session_active = False # Resetează starea sesiunii
            self.display.show_initial_screen() # Asigură-te că ecranul inițial e afișat

            qr_data = self.run_initial_state() # Așteaptă scanarea QR-ului biletului
            
            if not self.running: break # Dacă s-a oprit în timpul scanării
            if not qr_data:
                print("No QR data received, or shutdown initiated. Restarting scan.")
                continue # Revino la scanare dacă nu s-a detectat nimic (sau a fost oprit)

            self.display.show_message(config.TEXT_PROCESSING, duration_ms=1000) # "Se verifică biletul..."
            
            ticket_info = api_client.get_ticket_info(qr_data)
            
            if ticket_info:
                print(f"Ticket valid: {ticket_info}")
                self.process_photo_session(ticket_info)
            else:
                print("Invalid ticket or API error.")
                self.voice.speak(config.VOICE_ERROR_TICKET_INVALID)
                self.display.show_message("Bilet invalid sau eroare server.", duration_ms=3000)
                # Așteaptă puțin înainte de a reveni la ecranul inițial
                time.sleep(2) 

            if not self.running: break # Verifică din nou după o sesiune
        
        print("Photobooth application is shutting down.")

    def cleanup(self):
        print("Cleaning up resources...")
        if hasattr(self, 'display') and self.display:
            self.display.quit()
        if hasattr(self, 'camera') and self.camera:
            self.camera.release()
        # VoiceInteraction și S3Uploader nu au metode specifice de release/cleanup în implementarea curentă,
        # dar dacă ar avea (ex: închiderea clientului Google/AWS explicit), s-ar adăuga aici.
        # pygame.mixer.quit() este apelat în voice_interaction la finalul testului,
        # dar ar trebui apelat și aici dacă VoiceInteraction este instanțiat și folosit.
        if 'pygame' in sys.modules and pygame.mixer.get_init(): # Verifică dacă mixerul e inițializat
             pygame.mixer.quit()
        print("Cleanup finished.")

if __name__ == "__main__":
    # Asigură-te că directorul temp există (config.py ar trebui să-l creeze, dar verificăm)
    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR)
        print(f"Created temp directory: {os.path.abspath(config.TEMP_DIR)}")

    # Import pygame aici pentru a-l putea folosi în bucla de evenimente și la cleanup.
    # Acest lucru este necesar deoarece Pygame este folosit pentru a gestiona fereastra principală și evenimentele de ieșire.
    try:
        import pygame
    except ImportError:
        print("Pygame nu este instalat. Este necesar pentru display_manager și pentru bucla principală de evenimente.")
        print("Rulează: pip install pygame")
        sys.exit(1)


    app = None
    try:
        app = PhotoboothApp()
        app.main_loop()
    except Exception as e:
        print(f"An unhandled exception occurred in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if app:
            app.cleanup()
        print("Application terminated.")
