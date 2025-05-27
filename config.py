# photobooth_ai/config.py

# --- Display Settings ---
SCREEN_WIDTH = 1920  # Lățimea ecranului televizorului (ex: 1920 pentru Full HD)
SCREEN_HEIGHT = 1080 # Înălțimea ecranului televizorului (ex: 1080 pentru Full HD)
FULLSCREEN = True    # Rulează în mod fullscreen?

# --- Camera Settings ---
CAMERA_INDEX = 0  # Indexul camerei (de obicei 0 sau -1). Poate necesita ajustare.
CAMERA_RESOLUTION_WIDTH = 1280 # Rezoluția dorită pentru cameră
CAMERA_RESOLUTION_HEIGHT = 720 # Rezoluția dorită pentru cameră

# --- Paths ---
LOGO_PATH = "assets/logo.png"
TEMP_DIR = "temp"
CAPTURED_PHOTO_FILENAME = f"{TEMP_DIR}/captured_photo.jpg"
DOWNLOAD_QR_FILENAME = f"{TEMP_DIR}/download_qr.png"

# --- API Endpoint for Tickets ---
# Endpoint-ul REST care validează codul QR și returnează datele biletului
# Exemplu de răspuns așteptat: {"ticket_holder_name": "Nume Detinator", "purchaser_name": "Nume Cumparator"}
TICKET_API_ENDPOINT = "YOUR_TICKET_API_ENDPOINT_HERE" # Ex: "https://api.example.com/validate_ticket"

# --- Google Cloud Settings ---
# Asigură-te că variabila de mediu GOOGLE_APPLICATION_CREDENTIALS este setată
# sau specifică calea către fișierul JSON cu cheia de serviciu aici.
# GOOGLE_SERVICE_ACCOUNT_JSON = "/path/to/your/service-account-file.json" # Opțional
TTS_LANGUAGE_CODE = "ro-RO" # Codul limbii pentru Text-to-Speech
# Google nu are o voce numită "Zephyr" în mod standard. Alege una disponibilă pentru ro-RO.
# Poți lista voci cu `gcloud text-to-speech voices list` sau verifică documentația.
# Exemplu: "ro-RO-Standard-A" sau "ro-RO-Wavenet-A" (Wavenet sunt mai calitative dar pot costa mai mult)
TTS_VOICE_NAME = "ro-RO-Wavenet-A"
STT_LANGUAGE_CODE = "ro-RO" # Codul limbii pentru Speech-to-Text

# --- AWS S3 Settings ---
AWS_S3_BUCKET_NAME = "your-s3-bucket-name-for-photos"
AWS_S3_REGION = "your-s3-bucket-region" # ex: "eu-central-1"
# Asigură-te că ai configurat credentialele AWS (ex: via ~/.aws/credentials sau variabile de mediu)
# AWS_ACCESS_KEY_ID = "YOUR_AWS_ACCESS_KEY_ID" # Nu este recomandat în cod, folosește metode standard
# AWS_SECRET_ACCESS_KEY = "YOUR_AWS_SECRET_ACCESS_KEY" # Nu este recomandat în cod
S3_PHOTO_PREFIX = "photobooth_images/" # Directorul virtual în bucket pentru poze
S3_LINK_EXPIRATION_SECONDS = 3600 # Timpul de expirare pentru link-urile de download (1 oră)

# --- Timings ---
QR_DISPLAY_TIME_SECONDS = 30  # Cât timp se afișează QR-ul de download (în secunde)
COUNTDOWN_SECONDS = 3 # Numărătoarea inversă pentru poză

# --- Texts ---
# Poți externaliza acestea într-un fișier JSON/YAML pentru traduceri facile dacă e nevoie
TEXT_INITIAL_INSTRUCTIONS_LINE1 = "Scanează codul QR al biletului pentru a începe."
TEXT_INITIAL_INSTRUCTIONS_LINE2 = "Privește spre cameră."
TEXT_CAMERA_FEED_INSTRUCTIONS = "Așezați-vă pentru poză. Spuneți 'SUNTEM GATA!' când sunteți pregătiți."
TEXT_PROCESSING = "Procesare..."
TEXT_QR_DOWNLOAD_INSTRUCTIONS = "Scanează codul QR pentru a descărca fotografia."

# --- Voice Prompts ---
VOICE_GREETING_TEMPLATE = "Salut {ticket_holder_name}, deținătorul biletului cumpărat de către {purchaser_name}."
VOICE_INSTRUCTION_POSITION = "Minunat! Acum, așezați-vă pentru fotografie."
VOICE_INSTRUCTION_CONFIRM = "Când sunteți gata, spuneți tare și clar 'SUNTEM GATA!'"
VOICE_CONFIRMATION_ACKNOWLEDGED = "Perfect! Pregătiți-vă!"
VOICE_CONFIRMATION_NOT_HEARD = "Nu am înțeles. Vă rog, repetați 'SUNTEM GATA!'."
VOICE_PHOTO_SUCCESS = "Fotografia a fost realizată!"
VOICE_ERROR_GENERIC = "A apărut o eroare. Vă rugăm încercați din nou."
VOICE_ERROR_TICKET_INVALID = "Codul QR al biletului nu este valid sau nu a putut fi verificat."

# --- Confirmation Keywords ---
CONFIRMATION_PHRASE = "suntem gata" # Phrase to listen for, converted to lowercase

# Create temp directory if it doesn't exist
import os
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

print(f"Config loaded. Temp directory: {os.path.abspath(TEMP_DIR)}")
