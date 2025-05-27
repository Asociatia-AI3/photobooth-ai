
## Cerințe

### Hardware
*   Raspberry Pi (recomandat Pi 4 sau mai nou pentru performanță)
*   Ecran de televizor cu intrare HDMI
*   Cameră wide-angle compatibilă cu Raspberry Pi (ex: Camera Module sau USB webcam)
*   Placă de sunet externă USB (dacă microfonul/boxa nu sunt direct compatibile sau pentru calitate mai bună)
*   Microfon
*   Boxă (difuzor)

### Software
*   Sistem de operare pentru Raspberry Pi (ex: Raspberry Pi OS)
*   Python 3.7+
*   Biblioteci Python (vezi `Instalare Dependințe` mai jos)

### Servicii Externe
*   **Cont Google Cloud Platform:**
    *   API Text-to-Speech activat
    *   API Speech-to-Text activat
    *   Fișier JSON cu cheia de cont de serviciu (Service Account Key)
*   **Cont AWS (Amazon Web Services):**
    *   Bucket S3 pentru stocarea fotografiilor
    *   Credentiale AWS (Access Key ID & Secret Access Key) configurate cu permisiuni de scriere/citire pe bucket.
*   **Endpoint REST API:** Un API dezvoltat de tine pentru validarea codurilor QR ale biletelor și returnarea informațiilor despre deținător/cumpărător.

## Configurare și Setare

1.  **Clonează/Descarcă Proiectul:**
    Obține codul sursă al proiectului pe Raspberry Pi.

2.  **Creează Structura de Directoare:**
    Asigură-te că ai directorul `photobooth_ai` și în interiorul lui subdirectorul `assets`.

3.  **Adaugă Logo-ul:**
    Plasează fișierul logo-ului tău (`logo.png`) în directorul `photobooth_ai/assets/`.

4.  **Instalează Dependințele:**
    Deschide un terminal pe Raspberry Pi și rulează:
    ```bash
    sudo apt-get update
    sudo apt-get install python3-pip libportaudio2  # libportaudio2 este pentru sounddevice
    # Alte dependențe de sistem pot fi necesare pentru OpenCV sau Pygame în funcție de instalarea ta
    # de ex: sudo apt-get install libopencv-dev python3-opencv libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

    cd photobooth_ai
    pip3 install -r requirements.txt 
    ```
    *Notă: Este recomandat să folosești un mediu virtual Python (`venv`).*

    **Conținut `requirements.txt` (creează acest fișier):**
    ```txt
    pygame
    opencv-python
    numpy
    google-cloud-texttospeech
    google-cloud-speech
    boto3
    qrcode[pil]
    sounddevice
    soundfile
    requests
    ```

5.  **Configurează `config.py`:**
    Editează fișierul `photobooth_ai/config.py` și completează toate valorile placeholder cu setările tale specifice:
    *   `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `FULLSCREEN`
    *   `CAMERA_INDEX`, `CAMERA_RESOLUTION_WIDTH`, `CAMERA_RESOLUTION_HEIGHT`
    *   `TICKET_API_ENDPOINT` (endpoint-ul tău REST pentru bilete)
    *   `TTS_LANGUAGE_CODE`, `TTS_VOICE_NAME` (ex: "ro-RO-Wavenet-A")
    *   `STT_LANGUAGE_CODE`
    *   `AWS_S3_BUCKET_NAME`, `AWS_S3_REGION`
    *   `S3_PHOTO_PREFIX` (opțional, pentru organizare în bucket)
    *   Texte și prompt-uri vocale (pot fi personalizate)

6.  **Configurează Credentialele Google Cloud:**
    *   Descarcă fișierul JSON cu cheia contului de serviciu din Google Cloud Console.
    *   Setează variabila de mediu `GOOGLE_APPLICATION_CREDENTIALS` la calea acestui fișier:
        ```bash
        export GOOGLE_APPLICATION_CREDENTIALS="/calea/catre/fisierul-tau-cheie.json"
        ```
        Pentru a o face permanentă, adaugă această linie în `~/.bashrc` și rulează `source ~/.bashrc`.
    *   Alternativ (mai puțin recomandat pentru producție), poți seta calea direct în `config.py` la variabila `GOOGLE_SERVICE_ACCOUNT_JSON`, deși utilizarea variabilei de mediu este preferată.

7.  **Configurează Credentialele AWS:**
    *   Instalează AWS CLI: `pip3 install awscli`
    *   Configurează credentialele rulând: `aws configure`
        Vei fi întrebat de AWS Access Key ID, AWS Secret Access Key, Default region name și Default output format. Asigură-te că regiunea implicită corespunde cu `AWS_S3_REGION` din `config.py`.
    *   Aceste credentiale vor fi stocate în `~/.aws/credentials` și `~/.aws/config` și vor fi folosite automat de `boto3`.

## Rularea Aplicației

1.  Navighează în directorul proiectului:
    ```bash
    cd /calea/catre/photobooth_ai
    ```
2.  Rulează scriptul principal:
    ```bash
    python3 main.py
    ```
    Aplicația ar trebui să pornească, afișând ecranul inițial și începând scanarea pentru coduri QR.

## Depanare / Note Adiționale

*   **Index Cameră:** Dacă camera nu pornește, s-ar putea să fie nevoie să ajustezi `CAMERA_INDEX` în `config.py` (de obicei 0, -1, sau 1).
*   **Microfon:** Asigură-te că microfonul corect este selectat ca dispozitiv de intrare implicit în sistemul de operare al Raspberry Pi sau că este detectat corect de `sounddevice`. Poți lista dispozitivele cu `sd.query_devices()` (necesită adăugarea temporară a `import sounddevice as sd; print(sd.query_devices())` în `voice_interaction.py` sau `main.py` pentru test).
*   **Permisiuni:** Verifică permisiunile pentru acces la cameră, microfon, și pentru scrierea în directorul `temp/`.
*   **Conexiune Internet:** Este necesară o conexiune la internet stabilă pentru API-urile Google Cloud, AWS S3 și API-ul de bilete.
*   **Full Screen (Pygame):** Ieșirea din modul fullscreen (dacă este activat) se face de obicei cu `Alt+F4` sau prin oprirea programului (Ctrl+C în terminal). Dacă aplicația se blochează, s-ar putea să fie nevoie să te conectezi prin SSH pentru a opri procesul.
*   **Testarea Modulelor:** Pentru a depana mai ușor, poți testa funcționalitatea fiecărui modul individual rulându-l direct (ex: `python3 camera_handler.py`). Blocurile `if __name__ == '__main__':` din fiecare fișier conțin cod de testare de bază.

## Prezentare Generală Module

*   `main.py`: Orchestrează întregul flux al aplicației.
*   `config.py`: Centralizează toate setările configurabile.
*   `camera_handler.py`: Interfața cu camera video, captura de frame-uri și detecția codurilor QR folosind OpenCV.
*   `display_manager.py`: Responsabil pentru tot ce se afișează pe ecranul TV, folosind Pygame (logo, instrucțiuni, feed cameră, numărătoare inversă, cod QR de download).
*   `api_client.py`: Trimite cereri către endpoint-ul REST extern pentru validarea biletelor.
*   `voice_interaction.py`: Gestionează sinteza vocală (Text-to-Speech) și recunoașterea vocală (Speech-to-Text) prin serviciile Google Cloud. Redă și înregistrează audio.
*   `s3_uploader.py`: Încarcă fișierele foto pe un bucket AWS S3 și generează URL-uri presigned pentru descărcare.
*   `qr_generator.py`: Generează imagini de coduri QR pe baza datelor furnizate (link-ul de download al fotografiei).

---

Sperăm ca acest photobooth să aducă multă distracție la evenimentul tău!
