# photobooth_ai/display_manager.py
import pygame
import cv2
import numpy as np
import config

class DisplayManager:
    def __init__(self):
        pygame.init()
        pygame.font.init() # Inițializează modulul font
        
        if config.FULLSCREEN:
            self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("AI Photobooth")
        
        self.font_large = pygame.font.Font(None, 100) # Font mai mare pentru countdown
        self.font_medium = pygame.font.Font(None, 74) # Font mediu pentru instrucțiuni
        self.font_small = pygame.font.Font(None, 50)  # Font mic
        
        self.logo_image = None
        if config.LOGO_PATH:
            try:
                self.logo_image = pygame.image.load(config.LOGO_PATH)
                # Scale logo to fit, e.g., max 1/3 of screen width or height, maintaining aspect ratio
                logo_rect = self.logo_image.get_rect()
                scale_w = (config.SCREEN_WIDTH / 3) / logo_rect.width
                scale_h = (config.SCREEN_HEIGHT / 3) / logo_rect.height
                scale = min(scale_w, scale_h)
                self.logo_image = pygame.transform.smoothscale(self.logo_image, 
                                                               (int(logo_rect.width * scale), int(logo_rect.height * scale)))
            except pygame.error as e:
                print(f"Error loading logo image: {e}")
                self.logo_image = None
        
        self.background_color = (0, 0, 0) # Negru
        self.text_color = (255, 255, 255) # Alb

    def _render_text(self, text, font, color, center_x, center_y):
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(center_x, center_y))
        self.screen.blit(text_surface, text_rect)

    def show_initial_screen(self):
        self.screen.fill(self.background_color)
        if self.logo_image:
            logo_rect = self.logo_image.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 3))
            self.screen.blit(self.logo_image, logo_rect)
        
        self._render_text(config.TEXT_INITIAL_INSTRUCTIONS_LINE1, self.font_medium, self.text_color,
                          config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT * 2 // 3)
        self._render_text(config.TEXT_INITIAL_INSTRUCTIONS_LINE2, self.font_small, self.text_color,
                          config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT * 2 // 3 + 60)
        pygame.display.flip()

    def show_camera_feed(self, frame, instructions=None):
        # Convertește frame-ul OpenCV (BGR) în format Pygame (RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = np.rot90(frame_rgb) # Rotește frame-ul dacă este necesar din cauza orientării camerei
        frame_surface = pygame.surfarray.make_surface(frame_rgb)
        
        # Redimensionează frame-ul pentru a se potrivi pe ecran, păstrând aspect ratio
        frame_rect = frame_surface.get_rect()
        screen_rect = self.screen.get_rect()
        
        scaled_frame = pygame.transform.smoothscale(frame_surface, screen_rect.size)
        self.screen.blit(scaled_frame, (0,0))

        if instructions:
            self._render_text(instructions, self.font_medium, self.text_color,
                              config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 80) # Jos pe ecran
        pygame.display.flip()

    def show_countdown(self, number, current_frame=None):
        if current_frame is not None:
            self.show_camera_feed(current_frame) # Afișează feed-ul camerei în fundal
        else:
            self.screen.fill(self.background_color)

        # Overlay pentru a face textul mai vizibil
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,128)) # Semi-transparent black
        self.screen.blit(overlay, (0,0))

        self._render_text(str(number), self.font_large, self.text_color,
                          config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        pygame.display.flip()

    def show_message(self, message_line1, message_line2="", duration_ms=0):
        self.screen.fill(self.background_color)
        self._render_text(message_line1, self.font_medium, self.text_color,
                          config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 30)
        if message_line2:
            self._render_text(message_line2, self.font_small, self.text_color,
                              config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 30)
        pygame.display.flip()
        if duration_ms > 0:
            pygame.time.wait(duration_ms)

    def show_qr_code(self, qr_image_path):
        self.screen.fill(self.background_color)
        try:
            qr_img = pygame.image.load(qr_image_path)
            # Redimensionează QR code dacă e nevoie, ex: 1/2 din înălțimea ecranului
            qr_rect = qr_img.get_rect()
            scale_factor = (config.SCREEN_HEIGHT / 2) / qr_rect.height
            scaled_size = (int(qr_rect.width * scale_factor), int(qr_rect.height * scale_factor))
            qr_img = pygame.transform.smoothscale(qr_img, scaled_size)
            
            qr_img_rect = qr_img.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))
            self.screen.blit(qr_img, qr_img_rect)
            
            self._render_text(config.TEXT_QR_DOWNLOAD_INSTRUCTIONS, self.font_small, self.text_color,
                              config.SCREEN_WIDTH // 2, qr_img_rect.bottom + 50)
        except pygame.error as e:
            print(f"Error loading QR image for display: {e}")
            self._render_text("Eroare la afișare QR.", self.font_medium, self.text_color,
                              config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        pygame.display.flip()

    def clear_screen(self):
        self.screen.fill(self.background_color)
        pygame.display.flip()

    def quit(self):
        pygame.quit()

if __name__ == '__main__':
    # Test basic display functions
    # Asigură-te că ai un 'logo.png' în 'assets/' și directorul 'temp/' creat
    # Creează un fișier dummy QR pentru test
    if not os.path.exists(config.TEMP_DIR): os.makedirs(config.TEMP_DIR)
    try:
        import qrcode
        qr_test_img = qrcode.make("test_data")
        qr_test_img.save(config.DOWNLOAD_QR_FILENAME)
    except ImportError:
        print("pip install qrcode[pil] for testing qr generation")
    except Exception as e:
        print(f"Error creating dummy QR for test: {e}")


    display = DisplayManager()
    display.show_initial_screen()
    pygame.time.wait(3000)

    # Simulează un frame de cameră (doar un array negru)
    dummy_frame = np.zeros((config.CAMERA_RESOLUTION_HEIGHT, config.CAMERA_RESOLUTION_WIDTH, 3), dtype=np.uint8)
    
    display.show_camera_feed(dummy_frame, instructions="Test instructions for camera feed.")
    pygame.time.wait(3000)

    for i in range(3, 0, -1):
        display.show_countdown(i, dummy_frame)
        pygame.time.wait(1000)

    display.show_message("Test Message Line 1", "Test Message Line 2", duration_ms=3000)
    
    if os.path.exists(config.DOWNLOAD_QR_FILENAME):
        display.show_qr_code(config.DOWNLOAD_QR_FILENAME)
        pygame.time.wait(5000) # Afișează pentru 5 secunde în test
    else:
        print(f"Skipping QR display test, {config.DOWNLOAD_QR_FILENAME} not found.")

    display.quit()
    print("DisplayManager test finished.")
