# photobooth_ai/voice_interaction.py
import os
import sys # Pentru stderr
import time
import pygame # Pentru redare audio
import sounddevice as sd
import soundfile as sf # Doar pentru TTS, înregistrarea e acum în stream
from google.cloud import texttospeech
from google.cloud import speech
import config # Asigură-te că ai toate constantele necesare aici
import threading
import queue

class VoiceInteraction:
    def __init__(self):
        self.tts_client = texttospeech.TextToSpeechClient()
        self.stt_client = speech.SpeechClient()
        
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Pygame mixer init error: {e}. Audio playback might not work.", file=sys.stderr)
            # Decide dacă aplicația poate continua fără audio sau ar trebui să iasă.
            # Pentru un photobooth, vocea este importantă.
            # raise RuntimeError("Failed to initialize Pygame mixer for audio.") from e

        self.audio_file_path = os.path.join(config.TEMP_DIR, "response.mp3") # Pentru TTS

        # Atribute pentru streaming STT
        self._stt_thread = None
        self._keyword_monitor_thread = None
        self._audio_stream = None # Obiectul sounddevice.InputStream
        self._stop_streaming_event = threading.Event()
        self._transcript_queue = queue.Queue() # Coadă pentru a primi transcrierile de la thread-ul STT
        
        self.sample_rate = 16000  # Hz, standard pentru majoritatea modelelor STT
        self.chunk_size = int(self.sample_rate / 10)  # 100ms chunks

    def _play_audio_file(self, file_path):
        if not pygame.mixer.get_init():
            print("Pygame mixer not initialized. Cannot play audio.", file=sys.stderr)
            return
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except pygame.error as e:
            print(f"Pygame error playing audio {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error playing audio file {file_path}: {e}", file=sys.stderr)

    def speak(self, text_to_speak, wait_to_finish=True):
        if not text_to_speak: return
        print(f"AI Speaking: {text_to_speak}")
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=config.TTS_LANGUAGE_CODE,
            name=config.TTS_VOICE_NAME
        )
        audio_config_tts = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        try:
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config_tts
            )
            with open(self.audio_file_path, "wb") as out:
                out.write(response.audio_content)
            
            self._play_audio_file(self.audio_file_path)
            if os.path.exists(self.audio_file_path):
                 try: os.remove(self.audio_file_path)
                 except OSError: pass # Ignoră dacă nu se poate șterge imediat
        except Exception as e:
            print(f"Error during Text-to-Speech: {e}", file=sys.stderr)
            print(f"[TTS Fallback] AI: {text_to_speak}") # Fallback la print
            if wait_to_finish: time.sleep(len(text_to_speak) / 10) # Simulează timpul de vorbire


    def _audio_generator(self):
        """Un generator care preia chunk-uri audio de la microfon (via o coadă internă)
           și le trimite către API-ul Google Speech-to-Text.
           Rulează în contextul thread-ului _stt_thread.
        """
        audio_input_queue = queue.Queue()

        def mic_callback(indata, frame_count, time_info, status):
            """Callback pentru sounddevice.InputStream. Rulează într-un thread separat (creat de PortAudio)."""
            if status:
                print(f"Microphone status: {status}", file=sys.stderr)
            audio_input_queue.put(bytes(indata))

        # Inițializează și pornește stream-ul audio de la microfon
        try:
            self._audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size, # sounddevice va apela callback-ul cu acest nr de frame-uri
                channels=1,
                dtype='int16',
                callback=mic_callback
            )
            self._audio_stream.start()
            print("Microphone stream started for STT.")
        except Exception as e:
            print(f"Failed to start microphone stream: {e}", file=sys.stderr)
            # Semnalează thread-ului principal că a apărut o eroare
            self._transcript_queue.put({"type": "error", "text": f"Mic stream error: {e}"})
            return # Oprește generatorul

        while not self._stop_streaming_event.is_set():
            try:
                # Preia un chunk din coada alimentată de microfon
                chunk = audio_input_queue.get(block=True, timeout=0.1) 
                if chunk:
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)
            except queue.Empty:
                # Timeout, verifică dacă trebuie să ne oprim și continuă
                if self._stop_streaming_event.is_set():
                    break
                continue
            except Exception as e:
                print(f"Error in audio_generator: {e}", file=sys.stderr)
                break # Ieși din buclă la eroare
        
        if self._audio_stream:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
                print("Microphone stream stopped and closed.")
            except Exception as e:
                print(f"Error stopping microphone stream: {e}", file=sys.stderr)
            self_audio_stream = None


    def _process_stt_responses(self, responses):
        """Procesează răspunsurile de la API-ul STT și le pune în _transcript_queue."""
        try:
            for response in responses:
                if self._stop_streaming_event.is_set():
                    break # Verifică dacă trebuie să ne oprim

                if not response.results:
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript.strip()

                if result.is_final:
                    # print(f"STT Final: '{transcript}' (Confidence: {result.alternatives[0].confidence:.2f})")
                    if transcript: # Doar dacă nu e gol
                        self._transcript_queue.put({"type": "final", "text": transcript})
                else:
                    # print(f"STT Interim: '{transcript}'")
                    if transcript:
                        self._transcript_queue.put({"type": "interim", "text": transcript})
        
        except StopIteration: # Generatorul s-a oprit
            print("STT response stream ended (StopIteration).")
        except Exception as e:
            # O eroare comună aici este grpc._channel._Rendezvous: StatusCode.OUT_OF_RANGE
            # dacă stream-ul audio se termină brusc sau durează prea mult fără date.
            if "OUT_OF_RANGE" in str(e):
                 print(f"STT stream closed by Google (likely due to audio stream ending or timeout): {e}", file=sys.stderr)
            else:
                 print(f"Error processing STT responses: {e}", file=sys.stderr)
            self._transcript_queue.put({"type": "error", "text": str(e)})
        finally:
            print("STT response processing loop finished.")


    def _run_stt_streaming_session(self):
        """Funcția principală pentru thread-ul STT. Configurează și rulează streaming_recognize."""
        speech_contexts = [speech.SpeechContext(phrases=[config.CONFIRMATION_PHRASE] + getattr(config, 'COMMON_SPEECH_CONTEXT', []))]

        recognition_config_stt = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate,
            language_code=config.STT_LANGUAGE_CODE,
            model=getattr(config, 'STT_MODEL', None), # Permite specificarea unui model (ex: "telephony", "command_and_search")
            use_enhanced=getattr(config, 'STT_USE_ENHANCED', False), # Pentru modele enhanced
            speech_contexts=speech_contexts,
            enable_automatic_punctuation=True, # Ajută la fraze mai clare
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=recognition_config_stt,
            interim_results=True
        )

        audio_requests_generator = self._audio_generator()
        
        try:
            # `streaming_recognize` este un apel blocant până la închiderea stream-ului sau eroare
            responses = self.stt_client.streaming_recognize(
                config=streaming_config,
                requests=audio_requests_generator
            )
            self._process_stt_responses(responses)
        except Exception as e:
            print(f"Exception in stt_client.streaming_recognize: {e}", file=sys.stderr)
            self._transcript_queue.put({"type": "error", "text": f"STT recognize error: {e}"})
        finally:
            print("STT streaming session function finished.")


    def _monitor_transcripts_for_keyword(self, keyword, on_keyword_detected_callback, timeout_seconds=None):
        """Rulează într-un thread separat, monitorizează _transcript_queue pentru un cuvânt cheie."""
        print(f"Monitoring for keyword: '{keyword.lower()}'")
        start_time = time.time()
        keyword_found = False

        while not self._stop_streaming_event.is_set() and not keyword_found:
            try:
                item = self._transcript_queue.get(block=True, timeout=0.5) # Verifică periodic
                
                # Procesează doar transcrierile finale pentru cuvântul cheie
                if item.get("type") == "final":
                    transcript = item.get("text", "").lower()
                    # print(f"Keyword monitor received final: '{transcript}'") # Debug
                    if keyword.lower() in transcript:
                        print(f"Keyword '{keyword.lower()}' DETECTED in: '{transcript}'")
                        keyword_found = True
                        if on_keyword_detected_callback:
                            on_keyword_detected_callback() # Execută callback-ul
                        break # Ieși din bucla de monitorizare
                elif item.get("type") == "error":
                    print(f"Keyword monitor received error: {item.get('text')}", file=sys.stderr)
                    # Poate ar trebui să oprească sesiunea aici sau să semnaleze o eroare mai gravă
                    break 

            except queue.Empty:
                # Timeout, verifică dacă s-a depășit timpul total de așteptare
                if timeout_seconds and (time.time() - start_time) > timeout_seconds:
                    print(f"Keyword monitoring timed out after {timeout_seconds} seconds.")
                    # Aici ai putea apela un callback de timeout dacă e necesar
                    break
                continue # Continuă așteptarea
            except Exception as e:
                print(f"Exception in keyword monitor: {e}", file=sys.stderr)
                break
        
        if not keyword_found and not self._stop_streaming_event.is_set():
            print(f"Keyword '{keyword.lower()}' not detected before monitor ended (possibly timeout).")
        
        print("Keyword monitoring thread finished.")


    def start_listening_for_keyword(self, keyword_to_detect, on_keyword_callback, listen_timeout_seconds=None):
        """Pornește o sesiune de ascultare continuă în stream pentru un cuvânt cheie.
           Această metodă pornește thread-urile și returnează imediat.
        """
        if self._stt_thread and self._stt_thread.is_alive():
            print("STT session already active. Please stop it first.", file=sys.stderr)
            return

        self._stop_streaming_event.clear()
        self._transcript_queue = queue.Queue() # Golește coada pentru noua sesiune

        # Pornește thread-ul pentru sesiunea STT (care include _audio_generator)
        self._stt_thread = threading.Thread(target=self._run_stt_streaming_session, daemon=True)
        self._stt_thread.start()
        print("STT streaming thread initiated.")

        # Pornește thread-ul pentru monitorizarea cuvântului cheie
        self._keyword_monitor_thread = threading.Thread(
            target=self._monitor_transcripts_for_keyword,
            args=(keyword_to_detect, on_keyword_callback, listen_timeout_seconds),
            daemon=True
        )
        self._keyword_monitor_thread.start()
        print("Keyword monitoring thread initiated.")

    def stop_listening(self):
        """Oprește sesiunea de streaming STT și thread-urile asociate."""
        print("Attempting to stop listening session...")
        if not self._stop_streaming_event.is_set():
            self._stop_streaming_event.set() # Semnalează tuturor thread-urilor să se oprească

        # Oprirea stream-ului audio este gestionată în _audio_generator când _stop_streaming_event este setat.
        # Așteaptă thread-ul STT să se termine
        if self._stt_thread and self._stt_thread.is_alive():
            print("Joining STT thread...")
            self._stt_thread.join(timeout=5.0) # Așteaptă max 5 secunde
            if self._stt_thread.is_alive():
                print("STT thread did not join in time.", file=sys.stderr)
            else:
                print("STT thread joined.")
        self._stt_thread = None

        # Așteaptă thread-ul de monitorizare a cuvântului cheie
        if self._keyword_monitor_thread and self._keyword_monitor_thread.is_alive():
            print("Joining keyword monitor thread...")
            self._keyword_monitor_thread.join(timeout=2.0)
            if self._keyword_monitor_thread.is_alive():
                print("Keyword monitor thread did not join in time.", file=sys.stderr)
            else:
                print("Keyword monitor thread joined.")
        self._keyword_monitor_thread = None
        
        # Eliberează referința la stream-ul audio dacă nu s-a făcut deja
        if self._audio_stream:
            try:
                if not self._audio_stream.closed: # Verifică dacă nu e deja închis
                    self._audio_stream.stop()
                    self._audio_stream.close()
            except Exception as e:
                print(f"Error during explicit audio stream stop/close: {e}", file=sys.stderr)
            self._audio_stream = None

        # Golește coada de transcrieri pentru a nu afecta sesiuni viitoare
        while not self._transcript_queue.empty():
            try: self._transcript_queue.get_nowait()
            except queue.Empty: break

        print("Listening session stopped.")

    def cleanup(self):
        """Metodă de curățare generală, de apelat la închiderea aplicației."""
        self.stop_listening() # Asigură-te că totul este oprit
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        print("VoiceInteraction cleanup complete.")


if __name__ == '__main__':
    # --- Testare Modul Voce cu Streaming ---
    print("--- Voice Interaction Streaming Test ---")

    # Mock config pentru testare
    class MockConfig:
        TEMP_DIR = "temp"
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        TTS_LANGUAGE_CODE = "ro-RO"
        TTS_VOICE_NAME = "ro-RO-Wavenet-A" 
        
        STT_LANGUAGE_CODE = "ro-RO"
        CONFIRMATION_PHRASE = "suntem gata" # Cuvântul cheie de test
        # Opțional: adaugă context suplimentar pentru a ajuta STT
        COMMON_SPEECH_CONTEXT = ["fotografie", "start", "photobooth", "brânză"] 
        STT_MODEL = None # Folosește modelul implicit
        STT_USE_ENHANCED = False
        
        # GOOGLE_SERVICE_ACCOUNT_JSON = "calea/catre/cheia.json" # Setează dacă e necesar
        # if GOOGLE_SERVICE_ACCOUNT_JSON and os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
        #    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_SERVICE_ACCOUNT_JSON
        # else:
        #    print("WARNING: GOOGLE_SERVICE_ACCOUNT_JSON not set or file not found for test.")
        #    print("Ensure GOOGLE_APPLICATION_CREDENTIALS is set in your environment.")

    config = MockConfig() # Suprascrie config-ul importat cu cel de test

    voice_interaction_test = VoiceInteraction()
    
    print(f"\nDispozitive audio disponibile (sounddevice):")
    try:
        print(sd.query_devices())
        # Poți seta un dispozitiv specific dacă default-ul nu e corect:
        # sd.default.device = [INDEX_INTRARE, INDEX_IESIRE] # Ex: sd.default.device = [1, 3]
        print(f"Dispozitiv de intrare implicit: {sd.query_devices(kind='input')}")
    except Exception as e:
        print(f"Nu am putut interoga dispozitivele audio: {e}")

    voice_interaction_test.speak(f"Salut! Acesta este un test al modulului de voce cu streaming. Te rog, spune '{config.CONFIRMATION_PHRASE}'. Ai 15 secunde.")

    keyword_detected_event = threading.Event()

    def on_test_keyword_detected():
        print("CALLBACK: Cuvântul cheie a fost detectat în test!")
        keyword_detected_event.set()
        # Într-o aplicație reală, aici ai opri ascultarea și ai continua fluxul
        # voice_interaction_test.stop_listening() # Oprește imediat după detecție

    voice_interaction_test.start_listening_for_keyword(
        keyword_to_detect=config.CONFIRMATION_PHRASE,
        on_keyword_callback=on_test_keyword_detected,
        listen_timeout_seconds=20 # Timp maxim de așteptare pentru cuvântul cheie
    )

    # Așteaptă ca evenimentul să fie setat sau să treacă un timp
    # Într-o aplicație reală, bucla principală ar continua să ruleze (ex: afișând feed-ul camerei)
    print("Aștept detectarea cuvântului cheie sau timeout...")
    
    # Buclă de așteptare pentru test, pentru a nu închide programul imediat
    timeout_test_total = 22 # Puțin mai mult decât listen_timeout_seconds
    start_wait_time = time.time()
    while not keyword_detected_event.is_set() and (time.time() - start_wait_time) < timeout_test_total:
        if not voice_interaction_test._stt_thread.is_alive() and not voice_interaction_test._keyword_monitor_thread.is_alive():
            print("Firele de execuție pentru ascultare s-au oprit prematur.")
            break
        time.sleep(0.5)

    if keyword_detected_event.is_set():
        voice_interaction_test.speak("Am auzit confirmarea. Excelent!")
    else:
        voice_interaction_test.speak("Nu am auzit confirmarea în timpul alocat.")

    print("Opresc sesiunea de ascultare (dacă nu s-a oprit deja)...")
    voice_interaction_test.stop_listening() # Asigură oprirea

    voice_interaction_test.speak("Testul s-a încheiat.")
    
    voice_interaction_test.cleanup()
    print("--- Test Voice Interaction Streaming Încheiat ---")

