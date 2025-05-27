# photobooth_ai/main.py
import time
import os
import sys
import signal # Pentru a prinde CTRL+C
import threading # Necesar pentru a gestiona evenimentul de confirmare vocală

# Adaugă directorul curent în sys.path pentru a permite importurile relative
# current_dir = os.path.dirname(os.path.abspath(__file__))
# if current_dir not in sys.path:
#    sys.path.append(current_dir)

try:
    import config
    import display_manager
    import camera_handler
    import api_client
    # Folosește noua versiune a voice_interaction
    import voice_interaction # type: ignore 
    import s3_uploader
    import qr_generator
except ImportError as e:
    print(f"Critical Import Error: {e}. One or more modules are missing or not installed.", file=sys.stderr)
    print("Please ensure all dependencies are installed (pygame, opencv-python, google-cloud-texttospeech, google-cloud-speech, boto3, qrcode[pil], sounddevice, soundfile, requests).", file=sys.stderr)
    print("Also, ensure all .py files (config.py, display_manager.py, etc.) are in the same directory or PYTHONPATH is set correctly.", file=sys.stderr)
    sys.exit(1)

# Pygame trebuie importat aici pentru bucla de evenimente din main
try:
    import pygame
except ImportError:
    print("Pygame nu este instalat. Este necesar pentru display_manager și pentru bucla principală de evenimente.", file=sys.stderr)
    print("Rulează: pip install pygame", file=sys.stderr)
    sys.exit(1)


class PhotoboothApp:
    def __init__(self):
        print("Initializing Photobooth AI...")
        try:
            self.display = display_manager.DisplayManager()
            self.camera = camera_handler.CameraHandler()
            self.voice = voice_interaction.VoiceInteraction() # Noua clasă
            self.s3 = s3_uploader.S3Uploader()
            # qr_generator este folosit ca modul
        except Exception as e:
            print(f"Error during initialization of components: {e}", file=sys.stderr)
            if hasattr(self, 'display') and self.display: self.display.quit()
            if hasattr(self, 'camera') and self.camera: self.camera.release()
            if hasattr(self, 'voice') and self.voice: self.voice.cleanup()
            sys.exit(1)

        self.running = True
        self.session_active = False
        self.confirmation_event = threading.Event() # Pentru a semnala detectarea confirmării vocale

        signal.signal(signal.SIGINT, self.signal_handler)
        print("Photobooth AI Initialized. Press Ctrl+C to exit.")

    def signal_handler(self, signum, frame):
        print("\nCtrl+C detected. Shutting down gracefully...")
        self.running = False
        self.session_active = False # Oprește orice sesiune activă
        self.voice.stop_listening() # Oprește orice ascultare activă
        self.confirmation_event.set() # Deblochează orice așteptare pe acest eveniment

    def run_initial_state(self):
        self.display.show_initial_screen()
        qr_code_data = None
        last_frame_time = time.time()

        while self.running and not qr_code_data:
            current_time = time.time()
            # Limitează procesarea la ~20 FPS pentru a nu suprasolicita CPU
            if (current_time - last_frame_time) < (1.0 / 20.0): 
                time.sleep((1.0 / 20.0) - (current_time - last_frame_time))
            last_frame_time = time.time()
            
            frame = self.camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            # În starea inițială, ecranul arată logo & instrucțiuni (setat de show_initial_screen)
            # Camera doar scanează în fundal, nu afișăm feed-ul aici decât dacă dorim explicit
            
            qr_code_data = self.camera.detect_qr_code(frame)
            if qr_code_data:
                print(f"QR Code detected: {qr_code_data}")
                break
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
            if not self.running: break
        
        return qr_code_data

    def _handle_voice_confirmation(self):
        """Callback apelat de voice_interaction când cuvântul cheie este detectat."""
        print("MAIN_CALLBACK: Confirmare vocală primită!")
        # Nu opri ascultarea aici, deoarece s-ar putea să vrem să prindem și alte comenzi ulterior
        # sau să lăsăm voice_interaction să-și gestioneze propriul ciclu de viață per apel.
        # Dar pentru acest flow, vrem să oprim ascultarea pentru "suntem gata" după ce a fost detectat.
        self.voice.stop_listening() 
        self.voice.speak(config.VOICE_CONFIRMATION_ACKNOWLEDGED, wait_to_finish=True)
        self.confirmation_event.set() # Semnalează firului principal că s-a primit confirmarea

    def process_photo_session(self, ticket_info):
        self.session_active = True
        self.confirmation_event.clear() # Resetează evenimentul pentru noua sesiune

        greeting = config.VOICE_GREETING_TEMPLATE.format(
            ticket_holder_name=ticket_info.get("ticket_holder_name", "Participant"),
            purchaser_name=ticket_info.get("purchaser_name", "Cumpărătorul")
        )
        self.voice.speak(greeting, wait_to_finish=True)
        if not self.running or not self.session_active: return

        time.sleep(0.5)
        self.voice.speak(config.VOICE_INSTRUCTION_POSITION, wait_to_finish=True)
        if not self.running or not self.session_active: return
        
        self.voice.speak(config.VOICE_INSTRUCTION_CONFIRM, wait_to_finish=False) # Nu aștepta aici, lasă utilizatorul să vorbească

        # Timeout pentru ascultarea confirmării (ex: 20 secunde)
        listen_timeout = getattr(config, 'VOICE_CONFIRMATION_TIMEOUT_SECONDS', 20)
        
        self.voice.start_listening_for_keyword(
            keyword_to_detect=config.CONFIRMATION_PHRASE,
            on_keyword_callback=self._handle_voice_confirmation,
            listen_timeout_seconds=listen_timeout 
        )
        
        print(f"MAIN: Aștept confirmarea vocală ('{config.CONFIRMATION_PHRASE}') pentru max {listen_timeout}s...")
        
        # Buclă pentru afișarea feed-ului camerei în timp ce se așteaptă confirmarea
        start_wait_for_confirmation_time = time.time()
        confirmed_by_voice = False

        while self.running and self.session_active and not self.confirmation_event.is_set():
            frame_for_display = self.camera.get_frame()
            if frame_for_display is not None:
                self.display.show_camera_feed(frame_for_display, instructions=config.TEXT_CAMERA_FEED_INSTRUCTIONS)
            
            # Verifică dacă a trecut timeout-ul general, independent de cel din voice_interaction
            if (time.time() - start_wait_for_confirmation_time) > (listen_timeout + 2): # +2s buffer
                print("MAIN: Timeout general pentru așteptarea confirmării vocale.")
                break 

            # Verifică evenimentele Pygame (ex: închiderea ferestrei)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False; self.session_active = False; break
            if not self.running or not self.session_active: break
            
            time.sleep(0.05) # Menține bucla reactivă

        # Oprește ascultarea dacă nu s-a oprit deja (ex, la timeout general)
        self.voice.stop_listening()

        if self.confirmation_event.is_set():
            confirmed_by_voice = True
        
        if not self.running or not self.session_active:
            print("Sesiune întreruptă în timpul așteptării confirmării.")
            self.session_active = False
            return

        if not confirmed_by_voice:
            print("MAIN: Confirmarea vocală nu a fost primită.")
            self.voice.speak(config.VOICE_CONFIRMATION_NOT_HEARD + " Sesiunea se va încheia.", wait_to_finish=True)
            self.display.show_message("Confirmare neprimita.", duration_ms=3000)
            self.session_active = False
            return

        # --- Confirmarea a fost primită, continuă cu fotografia ---
        
        # Numărătoare inversă
        for i in range(config.COUNTDOWN_SECONDS, 0, -1):
            current_frame_for_countdown = self.camera.get_frame()
            self.display.show_countdown(i, current_frame=current_frame_for_countdown)
            # self.voice.speak(str(i), wait_to_finish=True) # Poate fi prea lent, mai bine un sunet
            time.sleep(1)
            if not self.running or not self.session_active: return

        self.display.show_message("ZÂMBIIIIȚI!", duration_ms=500)
        
        photo_path = self.camera.capture_photo()
        if not photo_path:
            self.voice.speak(config.VOICE_ERROR_GENERIC + " Nu am putut captura fotografia.", wait_to_finish=True)
            self.display.show_message("Eroare la captură foto!", duration_ms=3000)
            self.session_active = False
            return
        
        self.voice.speak(config.VOICE_PHOTO_SUCCESS, wait_to_finish=True)
        self.display.show_message(config.TEXT_PROCESSING, duration_ms=1000)

        download_url = self.s3.upload_file(photo_path)
        if not download_url:
            self.voice.speak(config.VOICE_ERROR_GENERIC + " Nu am putut încărca fotografia.", wait_to_finish=True)
            self.display.show_message("Eroare la upload S3!", duration_ms=3000)
            self.session_active = False
            return

        qr_image_path = qr_generator.generate_qr_code_image(
            download_url, 
            filename=config.DOWNLOAD_QR_FILENAME,
            add_logo=True, 
            logo_path=config.LOGO_PATH if os.path.exists(config.LOGO_PATH) else None
        )
        
        if qr_image_path:
            self.display.show_qr_code(qr_image_path)
            # Păstrează afișajul QR pentru timpul specificat, permițând ieșirea cu Ctrl+C
            qr_display_start_time = time.time()
            while self.running and (time.time() - qr_display_start_time) < config.QR_DISPLAY_TIME_SECONDS:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: self.running = False; break
                if not self.running: break
                time.sleep(0.1)
        else:
            self.voice.speak(config.VOICE_ERROR_GENERIC + " Nu am putut genera codul QR pentru download.", wait_to_finish=True)
            self.display.show_message("Eroare generare QR!", "Link: " + download_url, duration_ms=5000)

        try:
            if os.path.exists(photo_path): os.remove(photo_path)
            if os.path.exists(config.DOWNLOAD_QR_FILENAME): os.remove(config.DOWNLOAD_QR_FILENAME)
        except OSError as e:
            print(f"Error deleting temporary files: {e}", file=sys.stderr)

        self.session_active = False
        print("Photo session finished.")

    def main_loop(self):
        while self.running:
            self.session_active = False # Resetează starea sesiunii
            self.display.show_initial_screen()

            qr_data = self.run_initial_state()
            
            if not self.running: break
            if not qr_data:
                print("No QR data received, or shutdown initiated. Restarting scan.")
                continue

            self.display.show_message(config.TEXT_PROCESSING, "Verificare bilet...", duration_ms=500)
            
            ticket_info = api_client.get_ticket_info(qr_data)
            
            if ticket_info:
                print(f"Ticket valid: {ticket_info}")
                self.process_photo_session(ticket_info)
            else:
                print("Invalid ticket or API error.")
                self.voice.speak(config.VOICE_ERROR_TICKET_INVALID, wait_to_finish=True)
                self.display.show_message("Bilet invalid sau eroare server.", duration_ms=3000)
                time.sleep(2) 

            if not self.running: break
        
        print("Photobooth application main loop ended.")

    def cleanup(self):
        print("Cleaning up resources...")
        if hasattr(self, 'voice') and self.voice:
            self.voice.cleanup() # Asigură-te că se opresc thread-urile și mixerul din voice_interaction
        if hasattr(self, 'display') and self.display:
            self.display.quit()
        if hasattr(self, 'camera') and self.camera:
            self.camera.release()
        
        # Pygame quit general, deși display.quit() ar trebui să o facă.
        if pygame.get_init(): # Verifică dacă Pygame este încă inițializat
             pygame.quit()
        print("Cleanup finished.")

if __name__ == "__main__":
    if not os.path.exists(config.TEMP_DIR):
        try:
            os.makedirs(config.TEMP_DIR)
            print(f"Created temp directory: {os.path.abspath(config.TEMP_DIR)}")
        except OSError as e:
            print(f"Error creating temp directory {config.TEMP_DIR}: {e}", file=sys.stderr)
            sys.exit(1)
    
    app = None
    try:
        app = PhotoboothApp()
        app.main_loop()
    except KeyboardInterrupt: # Deși avem signal_handler, prindem și aici pentru siguranță
        print("\nKeyboardInterrupt caught in __main__. Shutting down...")
        if app: app.running = False # Semnalează oprirea
    except Exception as e:
        print(f"An unhandled exception occurred in main: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if app:
            app.cleanup()
        print("Application terminated.")
        
