# #️⃣ difffusion PhotoBoothAI 📺 🐟 🧶

## Cerințe

### Hardware
*   Raspberry Pi (recomandat Pi 4 Model B sau mai nou pentru performanță optimă cu streaming audio)
*   Ecran de televizor cu intrare HDMI
*   Cameră wide-angle compatibilă cu Raspberry Pi (ex: Camera Module v2/v3 sau USB webcam de calitate)
*   Placă de sunet externă USB (recomandată pentru calitate audio bună și pentru a evita problemele cu microfoanele onboard/simple)
*   Microfon (conectat la placa de sunet externă sau direct, dacă este de calitate)
*   Boxă/Difuzor (conectat la placa de sunet externă sau la ieșirea audio a Pi-ului)

### Software
*   Sistem de operare pentru Raspberry Pi (ex: Raspberry Pi OS - Bullseye sau mai nou, 64-bit recomandat)
*   Python 3.8+ (recomandat 3.9+ pentru compatibilitate optimă cu bibliotecile)
*   Manager de pachete `pip`
*   Librării de sistem (vezi `Instalare Dependințe` mai jos)

### Servicii Externe
*   **Cont Google Cloud Platform:**
    *   API Text-to-Speech activat
    *   API Speech-to-Text activat
    *   Fișier JSON cu cheia de cont de serviciu (Service Account Key) cu rolurile necesare.
*   **Cont AWS (Amazon Web Services):**
    *   Bucket S3 pentru stocarea fotografiilor
    *   Credentiale AWS (Access Key ID & Secret Access Key) configurate cu permisiuni de scriere/citire pe bucket (ex: `s3:PutObject`, `s3:GetObject`).
*   **Endpoint REST API:** Un API dezvoltat de tine pentru validarea codurilor QR ale biletelor și returnarea informațiilor despre deținător/cumpărător.

## Configurare și Setare

1.  **Clonează/Descarcă Proiectul:**
    Obține codul sursă al proiectului pe Raspberry Pi.
    ```bash
    git clone <URL_PROIECT> photobooth_ai 
    cd photobooth_ai
    ```
    Sau descarcă arhiva și extrage-o.

2.  **Creează Structura de Directoare (dacă nu există):**
    Asigură-te că ai directorul `photobooth_ai` și în interiorul lui subdirectorul `assets`. Directorul `temp/` va fi creat automat la prima rulare.

3.  **Adaugă Logo-ul:**
    Plasează fișierul logo-ului tău (ex: `logo.png`) în directorul `photobooth_ai/assets/`.

4.  **Instalează Dependințele:**

    a.  **Librării de Sistem:**
        Acestea sunt necesare pentru funcționarea corectă a unora dintre pachetele Python.
        ```bash
        sudo apt-get update
        sudo apt-get install -y python3-pip portaudio19-dev libsm6 libxext6 libxrender-dev libatlas-base-dev libjpeg-dev libtiff-dev libavcodec-dev libavformat-dev libswscale-dev libgtk2.0-dev pkg-config
        # portaudio19-dev este pentru sounddevice (alternativ libportaudio2)
        # libatlas-base-dev este pentru performanță NumPy/OpenCV
        # Celelalte sunt dependențe comune pentru OpenCV și Pygame pe sisteme headless sau minimal
        # S-ar putea să fie necesare și altele în funcție de configurația exactă a Raspberry Pi OS.
        ```
        Dacă folosești Raspberry Pi OS cu desktop, multe dintre acestea ar putea fi deja instalate.

    b.  **Pachete Python:**
        Este **puternic recomandat** să folosești un mediu virtual Python.
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate 
        # Acum ești în mediul virtual. Promptul tău ar trebui să se schimbe.
        
        pip install -r requirements.txt
        
        # Pentru a ieși din mediul virtual (când ai terminat):
        # deactivate
        ```
        Rulează `pip install -r requirements.txt` din directorul `photobooth_ai` (unde se află `requirements.txt`).

5.  **Configurează `config.py`:**
    Editează fișierul `photobooth_ai/config.py` și completează toate valorile placeholder cu setările tale specifice:
    *   Setări ecran (`SCREEN_WIDTH`, `SCREEN_HEIGHT`, `FULLSCREEN`)
    *   Setări cameră (`CAMERA_INDEX`, `CAMERA_RESOLUTION_WIDTH`, `CAMERA_RESOLUTION_HEIGHT`)
    *   `TICKET_API_ENDPOINT`
    *   Setări Google Cloud Voice (`TTS_LANGUAGE_CODE`, `TTS_VOICE_NAME`, `STT_LANGUAGE_CODE`, `STT_MODEL`, `STT_USE_ENHANCED`, `COMMON_SPEECH_CONTEXT`)
    *   Setări AWS S3 (`AWS_S3_BUCKET_NAME`, `AWS_S3_REGION`, `S3_PHOTO_PREFIX`)
    *   Timeout-uri (ex: `QR_DISPLAY_TIME_SECONDS`, `VOICE_CONFIRMATION_TIMEOUT_SECONDS`)
    *   Texte și prompt-uri vocale.

6.  **Configurează Credentialele Google Cloud:**
    *   Descarcă fișierul JSON cu cheia contului de serviciu din Google Cloud Console.
    *   Setează variabila de mediu `GOOGLE_APPLICATION_CREDENTIALS` la calea acestui fișier:
        ```bash
        export GOOGLE_APPLICATION_CREDENTIALS="/calea/catre/fisierul-tau-cheie.json"
        ```
        Pentru a o face permanentă, adaugă această linie în `~/.bashrc` (sau `~/.zshrc`) și rulează `source ~/.bashrc`.

7.  **Configurează Credentialele AWS:**
    *   Instalează AWS CLI dacă nu este deja prezent: `pip install awscli` (preferabil în afara venv dacă îl vrei global, sau în venv).
    *   Configurează credentialele rulând: `aws configure`
        Vei fi întrebat de AWS Access Key ID, AWS Secret Access Key, Default region name și Default output format. Asigură-te că regiunea implicită corespunde cu `AWS_S3_REGION` din `config.py`.

## Rularea Aplicației

1.  Activează mediul virtual (dacă folosești unul):
    ```bash
    cd /calea/catre/photobooth_ai
    source .venv/bin/activate 
    ```
2.  Rulează scriptul principal:
    ```bash
    python3 main.py
    ```
    Aplicația ar trebui să pornească, afișând ecranul inițial și începând scanarea pentru coduri QR.

## Depanare / Note Adiționale

*   **Index Cameră/Microfon:** Dacă hardware-ul nu este detectat corect, verifică setările din `config.py` și asigură-te că dispozitivele sunt corect selectate în sistemul de operare. Pentru `sounddevice`, poți folosi `sd.query_devices()` pentru a lista dispozitivele audio disponibile și indexurile lor.
*   **Permisiuni:** Asigură-te că scriptul are permisiunile necesare pentru acces la cameră, microfon și pentru scrierea în directorul `temp/`.
*   **Conexiune Internet:** Este esențială o conexiune la internet stabilă.
*   **Full Screen (Pygame):** Ieșirea din modul fullscreen (dacă este activat) se face de obicei cu `Alt+F4` sau prin oprirea programului (Ctrl+C în terminal).
*   **Loguri și Erori:** Fii atent la mesajele din consolă. Redirecționarea output-ului într-un fișier log poate fi utilă pentru sesiuni lungi: `python3 main.py > photobooth.log 2>&1 &`

## Prezentare Generală Module

*   `main.py`: Orchestrează întregul flux al aplicației, gestionează stările și evenimentele principale.
*   `config.py`: Centralizează toate setările configurabile, de la dimensiuni de ecran la chei API și texte.
*   `camera_handler.py`: Interfața cu camera video (OpenCV), captura de frame-uri și detecția codurilor QR.
*   `display_manager.py`: Responsabil pentru afișarea pe ecranul TV (Pygame): logo, instrucțiuni, feed cameră, numărătoare inversă, cod QR.
*   `api_client.py`: Trimite cereri către endpoint-ul REST extern pentru validarea biletelor.
*   `voice_interaction.py`: Modul avansat pentru interacțiunea vocală. Utilizează Google Text-to-Speech pentru redare și Google Speech-to-Text în mod **streaming** pentru recunoaștere vocală continuă și detectarea cuvintelor cheie (ex: "suntem gata"). Gestionează thread-uri multiple pentru a asigura o experiență fluidă.
*   `s3_uploader.py`: Încarcă fișierele foto pe un bucket AWS S3 și generează URL-uri presigned pentru descărcare.
*   `qr_generator.py`: Generează imagini de coduri QR pe baza datelor furnizate (link-ul de download al fotografiei).

---

Sperăm ca acest photobooth AI să aducă o experiență memorabilă la evenimentul tău!
