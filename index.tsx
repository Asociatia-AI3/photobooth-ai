/* tslint:disable */
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  GoogleGenAI,
  LiveServerMessage,
  Modality,
  Session,
  FunctionResponse,
  Type,
  Tool,
} from "@google/genai";
import { LitElement, PropertyValues, css, html } from "lit";
import { customElement, state } from "lit/decorators.js";
import { createBlob, decode, decodeAudioData } from "./utils";
import "./visual-3d";
import { Html5Qrcode, Html5QrcodeScannerState } from "html5-qrcode";
import { Html5QrcodeErrorTypes } from "html5-qrcode/src/core";
import { Webcam, WebcamError } from "ts-webcam";
import QrCreator from "qr-creator";

interface Visitor {
  id: string;
  name: string;
  email: string;
  ticketQr: string;
}

function dataURLtoBlob(dataurl: string): Blob {
  const arr = dataurl.split(",");
  const mimeMatch = arr[0].match(/:(.*?);/);
  if (!mimeMatch) {
    throw new Error("Invalid data URL format: MIME type not found.");
  }
  const mime = mimeMatch[1];
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new Blob([u8arr], { type: mime });
}

@customElement("gdm-live-audio")
export class GdmLiveAudio extends LitElement {
  @state() isRecording = false;
  @state() status = "";
  @state() error = "";

  private client?: GoogleGenAI | undefined;
  private session?: Session | undefined;
  private inputAudioContext?: AudioContext | undefined;
  private outputAudioContext?: AudioContext | undefined;
  @state() inputNode?: GainNode | undefined;
  @state() outputNode?: GainNode | undefined;
  private nextStartTime = 0;
  private mediaStream?: MediaStream | undefined;
  private sourceNode?: MediaStreamAudioSourceNode | undefined;
  private scriptProcessorNode?: ScriptProcessorNode | undefined;
  private sources = new Set<AudioBufferSourceNode>();
  private qrScanner?: Html5Qrcode | undefined;
  private visitor: Visitor | undefined;
  private photoUrl: string | undefined;

  private ai3SessionToken: string | undefined;
  private graphqlEndpoint = "https://api.ai3.ro/api/graphql";

  static styles = css`
    img#logo {
      display: block;
      top: 3em;
      position: fixed;
      z-index: 1;
      width: 300px;
      left: 50%;
      transform: translate(-50%, 0%);
    }
    #begin {
      position: absolute;
      top: 10em;
      left: 0;
      width: 100%;
      z-index: 1;
      color: white;
      font-family: monospace;
      font-weight: bold;
      text-align: center;
    }
    #container {
      position: relative;
      width: 100vw;
      height: 100vh;
    }
    #status {
      position: absolute;
      bottom: 5vh;
      left: 0;
      right: 0;
      z-index: 10;
      text-align: center;
      color: orange;
      font-family: monospace;
      font-size: 7pt;
    }
  `;

  constructor() {
    super();
  }

  protected async firstUpdated(
    _changedProperties: PropertyValues
  ): Promise<void> {
    super.firstUpdated(_changedProperties);
    const [u, p] = [process.env.AI3_LOGIN, process.env.AI3_PW];
    if (!u || !p) {
      this.updateError("Could not retrieve AI3 credentials");
      return;
    }
    const loginSuccessful = await this.loginUser(u, p);
    if (!loginSuccessful) return;
    await this.startQrScanner();
    this.inputAudioContext = new window.AudioContext({ sampleRate: 16000 });
    this.inputNode = this.inputAudioContext.createGain();
    this.outputAudioContext = new window.AudioContext({ sampleRate: 24000 });
    this.outputNode = this.outputAudioContext.createGain();
  }

  /**
   * Efectuează o cerere de autentificare (login) la API-ul GraphQL.
   *
   * @param {string} email Email-ul utilizatorului.
   * @param {string} password Parola utilizatorului.
   */
  async loginUser(email: string, password: string): Promise<boolean> {
    const loginMutation = `mutation Login($email: String!, $password: String!) {
        authenticateUserWithPassword(email: $email, password: $password) {
          ... on UserAuthenticationWithPasswordSuccess {
            sessionToken
            item {
              id
              name
              email
              role
              __typename
            }
            __typename
          }
          ... on UserAuthenticationWithPasswordFailure {
            message
            __typename
          }
          __typename
        }
      }
    `;

    try {
      const response = await fetch(this.graphqlEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          operationName: "Login",
          query: loginMutation,
          variables: {
            email: email,
            password: password,
          },
        }),
        redirect: "error",
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP error! status: ${response.status}, message: ${errorText}`
        );
      }

      const result = await response.json();

      if (result.errors) {
        console.error("GraphQL Errors during login:", result.errors);
        throw new Error("GraphQL login query failed.");
      }

      const authResult = result.data.authenticateUserWithPassword;

      if (authResult.__typename === "UserAuthenticationWithPasswordFailure") {
        throw new Error("Login failed:" + authResult.message);
      }

      // Login reușit
      this.ai3SessionToken = authResult.sessionToken;
      console.debug("set token", this.ai3SessionToken);
      return true;
    } catch (error) {
      console.error("Error during login:", error);
      this.updateError("Failed to get AI3 session token");
      return false;
    }
  }

  protected async startQrScanner() {
    if (!this.qrScanner)
      this.qrScanner = new Html5Qrcode("ticketScanner", false);
    document.getElementById("ticketScanner")?.classList.toggle("hidden");
    await this.qrScanner?.start(
      { facingMode: "environment" },
      { fps: 5, qrbox: { width: 150, height: 150 } },
      async (txt, _) => {
        await this.syncVisitor(txt);
        if (this.qrScanner?.getState() === Html5QrcodeScannerState.SCANNING) {
          await this.qrScanner?.stop();
          document.getElementById("ticketScanner")?.classList.toggle("hidden");
        }
        this.initClient();
        this.startRecording();
      },
      (errTxt, err) => {
        this.updateStatus("Scanning for ticket..");
        if (err.type === Html5QrcodeErrorTypes.IMPLEMENTATION_ERROR) {
          this.updateError(errTxt);
        }
      }
    );
  }

  async syncVisitor(ticketCode: string) {
    const query = `
      query GetTicketByCode($code: String!) {
        festivalTickets(where: { code: { equals: $code } }) {
          id
          code
          attendant {
            id
            name
            email
          }
        }
      }
    `;

    try {
      if (!this.ai3SessionToken) {
        throw new Error("No AI3 session token found");
      }
      const response = await fetch(this.graphqlEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${this.ai3SessionToken}`,
        },
        body: JSON.stringify({
          query: query,
          variables: {
            code: ticketCode,
          },
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP error! status: ${response.status}, message: ${errorText}`
        );
      }

      const result = await response.json();

      if (result.errors) {
        console.error("GraphQL Errors:", result.errors);
        throw new Error("GraphQL query failed.");
      }

      // GraphQL typically returns an array for queries like festivalTickets.
      // Assuming you expect at most one ticket per unique code:
      const ticket = result.data.festivalTickets[0];

      if (!ticket) {
        console.log(`No ticket found for code: ${ticketCode}`);
        throw new Error(`No ticket found for code: ${ticketCode}`);
      }

      this.visitor = {
        id: ticket.attendant.id,
        name: ticket.attendant.name,
        email: ticket.attendant.email,
        ticketQr: ticket.code,
      };
    } catch (error) {
      console.error("Error fetching ticket:", error);
      this.updateError(`${error}`);
      return;
    }
  }

  private initAudio() {
    if (!this.outputAudioContext) {
      return;
    }
    this.nextStartTime = this.outputAudioContext?.currentTime;
  }

  private async initClient() {
    if (!this.outputAudioContext) {
      return;
    }
    this.initAudio();

    if (!this.client)
      this.client = new GoogleGenAI({
        apiKey: process.env.GEMINI_API_KEY,
      });

    this.outputNode?.connect(this.outputAudioContext?.destination);

    this.initSession();
  }

  private async initSession() {
    if (
      this.isRecording ||
      !this.inputNode ||
      !this.outputNode ||
      !this.inputAudioContext ||
      !this.outputAudioContext
    ) {
      return;
    }
    // const model = "gemini-2.5-flash-preview-native-audio-dialog";
    const model = "models/gemini-2.0-flash-live-001";
    const tools: Tool[] = [
      {
        functionDeclarations: [
          {
            name: "capture_snapshot",
            description: "Take webcam photo for the user at the photobooth. Response is an object with a nullable photo url prop. Never read this url.",
            parameters: { type: Type.OBJECT, properties: {}, required: [] },
          },
          {
            name: "generate_qr",
            description: "Display a QR code for the photo taken from the webcam so that the user can download it. Response is a boolean",
            parameters: {},
          },
          {
            name: "terminate_session",
            description: "If the user seems to want to end the conversation, terminate the current session",
            parameters: {},
          },
        ],
      },
      {
        googleSearch: {},
      },
    ];

    try {
      this.session = await this.client?.live.connect({
        model: model,
        callbacks: {
          onopen: () => {
            this.updateStatus("Opened");
          },
          onmessage: async (message: LiveServerMessage) => {
            if (message.toolCall) {
              console.log("tool call", message.toolCall);
              const toolCalls = message.toolCall.functionCalls;
              if (!toolCalls) return;
              const responses: FunctionResponse[] = [];

              for (const toolCall of toolCalls) {
                let { id, name, args } = toolCall;
                let response;
                AnalyserNode;

                if (name === "capture_snapshot") {
                  const snap = await this.captureSnapshot();
                  response = {"snapshot": snap}
                } else if (name === "generate_qr") {
                  response = {"qrSuccess": await this.displayQR()};
                }else if (name === "terminate_session") {
                  response = {"sessionTerminated": true};
                  setTimeout(() => this.reset(), 2000);
                }
                console.log("responding to ", id, name, args);
                responses.push({ id, name, response: { output: response } });
              }
              await this.session?.sendToolResponse({
                functionResponses: responses,
              });
              return;
            }
            const audio = message.serverContent?.modelTurn?.parts
              ? message.serverContent?.modelTurn?.parts[0]?.inlineData
              : undefined;

            if (audio && this.outputAudioContext && this.outputNode) {
              this.nextStartTime = Math.max(
                this.nextStartTime,
                this.outputAudioContext.currentTime
              );

              const audioBuffer = await decodeAudioData(
                decode(audio.data),
                this.outputAudioContext,
                24000,
                1
              );
              const source = this.outputAudioContext.createBufferSource();
              source.buffer = audioBuffer;
              source.connect(this.outputNode);
              source.addEventListener("ended", () => {
                this.sources.delete(source);
              });

              source.start(this.nextStartTime);
              this.nextStartTime = this.nextStartTime + audioBuffer.duration;
              this.sources.add(source);
            }

            const interrupted = message.serverContent?.interrupted;
            if (interrupted) {
              for (const source of this.sources.values()) {
                source.stop();
                this.sources.delete(source);
              }
              this.nextStartTime = 0;
            }
          },
          onerror: (e: ErrorEvent) => {
            this.updateError(e.message);
          },
          onclose: (e: CloseEvent) => {
            this.updateStatus("Close:" + e.reason);
          },
        },
        config: {
          responseModalities: [Modality.AUDIO],
          tools: tools,

          systemInstruction: `
            Esti un agent de photobooth la festivalul diffusion (pronuntat ca in engleza) si vorbesti cu 
            ${this.visitor?.name} care doreste sa faca o poza. Incepe tu sa vorbesti cu utilizatorul, spunand-ui despre difffusion, un festival
            digital in Alba Iulia, Romania. Ii spui de asemenea despre rolul tau. Te folosesti de apelurile de functii aflate la dispozitie pentru
            a raspunde solicitarilor utilizatorului. Vei vorbi in limba engleza. Niciodata nu citesti URL-ul unei fotografii cu vocea, intreaba
            intotdeauna daca sa afisezi un cod QR. Daca utilizatorul face o pauza lunga, il intrebi daca mai e acolo si daca nu confirma poti inchide sesiunea.`,
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: "Zephyr" } },
            languageCode: "en-US",
          },
        },
      });
    } catch (e) {
      console.error(e);
    }
  }

  private updateStatus(msg: string) {
    this.status = msg;
  }

  private updateError(msg: string) {
    this.error = msg;
  }

  private async startRecording() {
    if (
      this.isRecording ||
      !this.inputNode ||
      !this.outputNode ||
      !this.inputAudioContext ||
      !this.outputAudioContext
    ) {
      return;
    }

    this.inputAudioContext?.resume();

    this.updateStatus("Requesting microphone access...");

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });

      this.updateStatus("Microphone access granted. Starting capture...");

      this.sourceNode = this.inputAudioContext?.createMediaStreamSource(
        this.mediaStream
      );
      this.sourceNode?.connect(this.inputNode);

      const bufferSize = 256;
      this.scriptProcessorNode = this.inputAudioContext?.createScriptProcessor(
        bufferSize,
        1,
        1
      );

      if (!this.scriptProcessorNode) {
        return;
      }

      this.scriptProcessorNode.onaudioprocess = (audioProcessingEvent) => {
        if (!this.isRecording) return;

        const inputBuffer = audioProcessingEvent.inputBuffer;
        const pcmData = inputBuffer.getChannelData(0);

        this.session?.sendRealtimeInput({ media: createBlob(pcmData) });
      };

      this.sourceNode?.connect(this.scriptProcessorNode);
      this.scriptProcessorNode.connect(this.inputAudioContext.destination);

      this.isRecording = true;
      this.updateStatus("🔴 Recording... Capturing PCM chunks.");
    } catch (err) {
      console.error("Error starting recording:", err);
      if (!(err instanceof Error)) {
        this.updateStatus(`Error: ${err}`);
      } else {
        this.updateStatus(`Error: ${err.message}`);
      }
      this.stopRecording();
    }
  }

  private stopRecording() {
    if (!this.isRecording && !this.mediaStream && !this.inputAudioContext)
      return;

    this.updateStatus("Stopping recording...");

    this.isRecording = false;

    if (this.scriptProcessorNode && this.sourceNode && this.inputAudioContext) {
      this.scriptProcessorNode.disconnect();
      this.sourceNode.disconnect();
    }

    this.scriptProcessorNode = undefined;
    this.sourceNode = undefined;

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = undefined;
    }

    this.updateStatus("Recording stopped. Click Start to begin again.");
  }

  private reset() {
    this.session?.close();
    this.stopRecording();
    this.startQrScanner();
  }

  private async captureSnapshot() {
    const bc = document.getElementById("boothCam") as HTMLVideoElement;
    try {
      // 1. Capturați imaginea de la webcam
      // Create Webcam instance
      const webcam = new Webcam();

      // Get available video devices
      const videoDevices = await webcam.getVideoDevices();
      const selectedDevice = videoDevices[0]; // or let user select
      bc.classList.toggle("hidden");
      webcam.setupConfiguration({
        deviceInfo: selectedDevice,
        allowFallbackResolution: true,
        videoElement: bc,
        debug: true, // Enable debug logging to console
        onStart: () => console.log("Webcam started"),
        onError: (error: WebcamError) => {
          console.error("Error code:", error.code);
          console.error("Error message:", error.message);
        },
      });
      await webcam.start(); // Asigură-te că webcam-ul este pornit înainte de a captura
      await new Promise(resolve => setTimeout(resolve, 2000));
      const imageDataUrl = await webcam.captureImage({
        scale: 1.0,
        mediaType: "image/jpeg",
        quality: 0.9,
      });

      // 2. Extrageți tipul de fișier și generați un nume unic
      const blob = dataURLtoBlob(imageDataUrl);
      const fileType = blob.type; // ex: 'image/jpeg'
      const fileName = `webcam-capture-${Date.now()}.jpeg`; // Nume unic pentru fișier

      // 3. Obțineți URL-ul pre-signed de la serverul Vite (sau API-ul de backend)
      console.log("Solicităm URL pre-signed de la server...");
      const response = await fetch(
        `/api/presigned-url?fileName=${fileName}&fileType=${fileType}`
      );
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          `Eroare la obținerea URL-ului pre-signed: ${errorData.error}`
        );
      }
      const data = await response.json();
      const presignedUrl = data.presignedUrl;
      console.log("URL pre-signed primit:", presignedUrl);

      // 4. Încarcă imaginea direct în S3 folosind URL-ul pre-signed
      console.log("Încărcăm imaginea în S3...");
      const uploadResponse = await fetch(presignedUrl, {
        method: "PUT",
        headers: {
          "Content-Type": fileType,
        },
        body: blob,
      });

      if (uploadResponse.ok) {
        console.log("Imaginea a fost încărcată cu succes în S3!");
        // Aici poți afișa un mesaj de succes sau face alte acțiuni
        webcam.stop(); // Oprește webcam-ul după upload
        bc.classList.toggle("hidden");
        this.photoUrl = `https://${process.env.S3_BUCKET_NAME}.s3.eu-central-1.amazonaws.com/uploads/${fileName}`;
        console.log(this.photoUrl);
        return this.photoUrl;
      } else {
        const uploadErrorText = await uploadResponse.text();
        throw new Error(
          `Eroare la încărcarea în S3: ${uploadResponse.status} ${uploadResponse.statusText} - ${uploadErrorText}`
        );
      }
    } catch (error) {
      const errStr = (error instanceof Error) ? error.message : `${error}`;
      console.error("Eroare generală la procesul de upload:", error);
      this.updateError(errStr);
      bc.classList.toggle("hidden");
      return null;
    }
  }

  private async displayQR() {
    const qrDiv = document.getElementById("downloaderQR") as HTMLDivElement;
    qrDiv.innerHTML = "";
    qrDiv.classList.toggle("hidden");

    if (!this.photoUrl) {
      this.updateError("No photo URL");
      return false;
    }

    QrCreator.render(
      {
        text: this.photoUrl,
        size: 300
      },
      qrDiv
    );
    setTimeout(() => { 
      qrDiv.classList.toggle("hidden");
    }, 20000); 
    return true;
  }

  render() {
    const vis3d =
      (this.inputNode &&
        this.outputNode &&
        html`
          <gdm-live-audio-visuals-3d
            .inputNode=${this.inputNode}
            .outputNode=${this.outputNode}
          ></gdm-live-audio-visuals-3d>
        `) ||
      "";
    return html`
      <div>
        <img id="logo" src="/logo-glitch.png" title="difffusion logo" />
        <div id="begin">start by showing me your festival ticket</div>
        ${vis3d}
        <div id="status">${this.error}</div>
      </div>
    `;
  }
}
