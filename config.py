# photobooth_ai/config.py
import os

# --- Display Settings ---
SCREEN_WIDTH = 1920  # Lățimea ecranului televizorului (ex: 1920 pentru Full HD)
SCREEN_HEIGHT = 1080 # Înălțimea ecranului televizorului (ex: 1080 pentru Full HD)
FULLSCREEN = True    # Rulează în mod fullscreen? (True/False)

# --- Camera Settings ---
CAMERA_INDEX = 0  # Indexul camerei (de obicei 0 sau -1). Poate necesita ajustare (ex: `v4l2-ctl --list-devices`).
CAMERA_RESOLUTION_WIDTH = 1280 # Rezoluția dorită pentru cameră
CAMERA_RESOLUTION_HEIGHT = 720 # Rezoluția dorită pentru cameră

# --- Paths ---
# Asigură-te că ai directorul 'assets' și 'temp' în rădăcina proiectului 'photobooth_ai'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # Rădăcina directorului photobooth_ai
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")

LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png") # Pune logo.png în assets/
CAPTURED_PHOTO_FILENAME_BASE = "captured_photo" # Numele de bază, extensia va fi .jpg
CAPTURED_PHOTO_PATH = os.path.join(TEMP_DIR, f"{CAPTURED_PHOTO_FILENAME_BASE}.jpg")
DOWNLOAD_QR_FILENAME_BASE = "download_qr" # Numele de bază, extensia va fi .png
DOWNLOAD_QR_PATH = os.path.join(TEMP_DIR, f"{DOWNLOAD_QR_FILENAME_BASE}.png")


# --- API Endpoint for Tickets ---
# Endpoint-ul REST care validează codul QR și returnează datele biletului
# Exemplu de răspuns așteptat: {"ticket_holder_name": "Nume Detinator", "purchaser_name": "Nume Cumparator"}
TICKET_API_ENDPOINT = "YOUR_TICKET_API_ENDPOINT_HERE" # Ex: "https://api.example.com/validate_ticket"
# TICKET_API_TIMEOUT_SECONDS = 10 # Timeout pentru cererea API


# --- Google Cloud Settings ---
# Asigură-te că variabila de mediu GOOGLE_APPLICATION_CREDENTIALS este setată la calea fișierului JSON cu cheia de serviciu.
# Alternativ, poți decomenta și seta calea aici (nerecomandat pentru producție):
# GOOGLE_SERVICE_ACCOUNT_JSON = "/calea/absoluta/catre/fisierul-tau-google-serviciu.json"

# Text-to-Speech (TTS) Settings
TTS_LANGUAGE_CODE = "ro-RO"     # Codul limbii pentru Google TTS
TTS_VOICE_NAME = "ro-RO-Wavenet-A" # Vocea Google TTS. Verifică disponibilitatea pentru limba ta.
                                   # Alte opțiuni Wavenet pentru ro-RO: B, C, D. Standard: ro-RO-Standard-A

# Speech-to-Text (STT) Settings - pentru streaming
STT_LANGUAGE_CODE = "ro-RO"     # Codul limbii pentru Google STT
STT_MODEL = None                # Model specific STT (ex: "command_and_search", "telephony", "phone_call"). None folosește default.
STT_USE_ENHANCED = False        # Folosește model "enhanced" (poate fi mai scump, dar mai precis). (True/False)
# Context pentru STT - ajută la recunoașterea frazelor specifice
COMMON_SPEECH_CONTEXT = ["fotografie", "brânză", "start", "stop", "ajutor", "poză"]


# --- AWS S3 Settings ---
# Numele bucket-ului va fi obținut din output-ul stack-ului CDK.
# Completează-l aici după ce ai deployat infrastructura CDK.
AWS_S3_BUCKET_NAME = "NUMELE-BUCKETULUI-GENERAT-DE-CDK-AICI"
AWS_S3_REGION = "eu-central-1" # SAU REGIUNEA TA AWS UNDE AI DEPLOYAT STACK-UL CDK. Asigură-te că e aceeași cu cea folosită pentru `cdk bootstrap` și `cdk deploy`.
S3_PHOTO_PREFIX = "photobooth_images/" # Directorul virtual în bucket pentru poze (ex: "evenimentX/")
S3_LINK_EXPIRATION_SECONDS = 3600 # Timpul de expirare pentru link-urile de download (1 oră = 3600s)
# Credentialele AWS (Access Key ID, Secret Access Key) ar trebui configurate prin AWS CLI (`aws configure`)
# sau prin variabile de mediu pe Raspberry Pi, NU direct în acest fișier.

# --- Timings ---
QR_DISPLAY_TIME_SECONDS = 30  # Cât timp se afișează QR-ul de download (în secunde)
COUNTDOWN_SECONDS = 3       # Numărătoarea inversă pentru poză
# Timeout pentru așteptarea comenzii vocale "suntem gata"
VOICE_CONFIRMATION_TIMEOUT_SECONDS = 20 # Câte secunde se ascultă activ pentru confirmare

# --- Texts ---
# Poți externaliza acestea într-un fișier JSON/YAML pentru traduceri facile dacă e nevoie
TEXT_INITIAL_INSTRUCTIONS_LINE1 = "Scanează codul QR al biletului pentru a începe."
TEXT_INITIAL_INSTRUCTIONS_LINE2 = "Privește spre cameră și zâmbește!"
TEXT_CAMERA_FEED_INSTRUCTIONS = "Așezați-vă pentru poză. Spuneți 'SUNTEM GATA!' când sunteți pregătiți."
TEXT_PROCESSING = "Procesare..."
TEXT_PROCESSING_TICKET = "Verificare bilet..."
TEXT_QR_DOWNLOAD_INSTRUCTIONS = "Scanează codul QR pentru a descărca fotografia."
TEXT_PHOTO_CAPTURE_SMILE = "ZÂMBIIIIȚI!"
TEXT_ERROR_GENERIC_DISPLAY = "A apărut o eroare."
TEXT_ERROR_TICKET_INVALID_DISPLAY = "Bilet invalid sau eroare server."
TEXT_ERROR_CONFIRMATION_TIMEOUT_DISPLAY = "Confirmare neprimita."
TEXT_ERROR_CAPTURE_DISPLAY = "Eroare la captură foto!"
TEXT_ERROR_UPLOAD_DISPLAY = "Eroare la upload S3!"
TEXT_ERROR_QR_GEN_DISPLAY = "Eroare generare QR!"


# --- Voice Prompts (Textul care va fi redat de TTS) ---
VOICE_GREETING_TEMPLATE = "Salut {ticket_holder_name}, deținătorul biletului cumpărat de către {purchaser_name}."
VOICE_INSTRUCTION_POSITION = "Minunat! Acum, așezați-vă pentru fotografie cum doriți."
VOICE_INSTRUCTION_CONFIRM = f"Când sunteți gata, spuneți tare și clar 'SUNTEM GATA!'" # Frază actualizată
VOICE_CONFIRMATION_ACKNOWLEDGED = "Perfect! Pregătiți-vă pentru numărătoarea inversă!"
VOICE_CONFIRMATION_NOT_HEARD = "Nu am înțeles confirmarea." # Mesaj scurt pentru timeout sau eșec STT
VOICE_SESSION_END_NO_CONFIRM = "Nu am primit confirmarea. Sesiunea se va încheia. Puteți încerca din nou."
VOICE_PHOTO_SUCCESS = "Super! Fotografia a fost realizată!"
VOICE_ERROR_GENERIC = "Din păcate, a apărut o problemă tehnică."
VOICE_ERROR_TICKET_INVALID = "Codul QR al biletului nu este valid sau nu a putut fi verificat. Te rog, încearcă cu un alt bilet."
VOICE_ERROR_CAPTURE = "Nu am reușit să fac fotografia."
VOICE_ERROR_UPLOAD = "Nu am putut încărca fotografia pe server."
VOICE_ERROR_QR_GEN = "Nu am putut genera codul QR pentru descărcare."

# --- Confirmation Keywords ---
# Fraza exactă pe care o ascultă Speech-to-Text. Trebuie să corespundă cu instrucțiunea vocală.
CONFIRMATION_PHRASE = "suntem gata" # Convertit la minuscule în logică.


# --- Audio Settings (pentru sounddevice în voice_interaction.py) ---
AUDIO_SAMPLE_RATE = 16000       # Hz, standard pentru majoritatea modelelor STT Google
AUDIO_CHUNK_DURATION_MS = 100   # Durata unui chunk audio trimis la STT (în milisecunde)


# --- Creare director temporar ---
# Asigură-te că directorul TEMP_DIR (definit mai sus) există.
if not os.path.exists(TEMP_DIR):
    try:
        os.makedirs(TEMP_DIR)
        print(f"Successfully created temp directory: {os.path.abspath(TEMP_DIR)}")
    except OSError as e:
        print(f"Error creating temp directory {TEMP_DIR}: {e}. Please create it manually.", file=sys.stderr)
        # Consideră oprirea aplicației dacă directorul temp nu poate fi creat,
        # deoarece este esențial pentru fișierele audio și imaginile QR.
        # sys.exit(1) # Decomentează dacă vrei să oprești aici.

# Verifică dacă AWS_S3_BUCKET_NAME este placeholder și emite un avertisment
if AWS_S3_BUCKET_NAME == "NUMELE-BUCKETULUI-GENERAT-DE-CDK-AICI":
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
    print("!!! WARNING: AWS_S3_BUCKET_NAME in config.py is still set to its           !!!", file=sys.stderr)
    print("!!!          placeholder value. Please update it with the bucket name      !!!", file=sys.stderr)
    print("!!!          obtained from the CDK deployment output. S3 uploads will fail.!!!", file=sys.stderr)
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)

if TICKET_API_ENDPOINT == "YOUR_TICKET_API_ENDPOINT_HERE":
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
    print("!!! WARNING: TICKET_API_ENDPOINT in config.py is set to its placeholder.   !!!", file=sys.stderr)
    print("!!!          Ticket validation will use mock data or fail.                 !!!", file=sys.stderr)
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)

print(f"Config loaded. Temp directory: {os.path.abspath(TEMP_DIR)}")
print(f"Project root: {PROJECT_ROOT}")
