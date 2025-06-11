// main.go
package main

import (
    "context"
    "encoding/base64"
    "bytes"
    "fmt"
    "log"
    "os"
    "os/signal"
    "time"

    "gocv.io/x/gocv"
    "github.com/google/uuid"
    "github.com/gordonklaus/portaudio"
    "layeh.com/gopus"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/s3"
    "github.com/skip2/go-qrcode"
    "google.golang.org/genai"
    "google.golang.org/genai/genaiws"
)

// Canale audio/video
var (
    audioChan = make(chan []byte, 100)
    videoChan = make(chan []byte, 10)
)

func main() {
    stopScanner := make(chan struct{})
    qrChan := make(chan string)

    go webcamQRScanner(videoChan, stopScanner, qrChan)
    qrData := <-qrChan
    close(stopScanner)

    log.Println("QR detectat:", qrData)
    user, err := graphqlIdentify(qrData)
    if err != nil {
        log.Fatalf("Grafică utilizator eșuat: %v", err)
    }
    log.Printf("User: %s (%s)", user.Name, user.Code)

    go streamMicAudio(audioChan)
    go playAudio(audioChan)
    stopVid := make(chan struct{})
    go webcamStream(videoChan, stopVid)

    startGeminiLive(user)

    close(stopVid)
    log.Println("Sesiune terminată")
}

func startGeminiLive(user *User) {
    ctx := context.Background()
    client, err := genai.NewClient(ctx, &genai.ClientConfig{APIKey: os.Getenv("GEMINI_API_KEY")})
    if err != nil {
        log.Fatal(err)
    }

    tools := []genaiws.FunctionDeclaration{
        genaiws.FunctionDeclaration{Name: "captureSnapshot", Description: "Makes snapshot", Parameters: schema(`{"type":"object","properties":{},"required":[]}`)},
        genaiws.FunctionDeclaration{Name: "uploadToS3", Description: "Uploads image", Parameters: schema(`{"type":"object","properties":{"bytes":{"type":"string"},"user_code":{"type":"string"}},"required":["bytes","user_code"]}`)},
        genaiws.FunctionDeclaration{Name: "generateQR", Description: "Creates QR code", Parameters: schema(`{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}`)},
        genaiws.FunctionDeclaration{Name: "displayOnTV", Description: "Show on TV", Parameters: schema(`{"type":"object","properties":{"img_b64":{"type":"string"}},"required":["img_b64"]}`)},
    }

    conn, err := genaiws.DialLive(ctx, client, "gemini-2.0-flash-live-preview-04-09", genaiws.LiveConfig{
        ResponseModalities: []genaiws.Modality{genaiws.ModalityAudio, genaiws.ModalityText},
        Tools:              tools,
    })
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    systemPrompt := fmt.Sprintf("Ești un asistent foto la festival. Salută pe %s și propune o poză.", user.Name)
    conn.SendText(systemPrompt)

    go func() {
        for msg := range conn.Receive() {
            if fc := msg.FunctionCall; fc != nil {
                switch fc.Name {
                case "captureSnapshot":
                    img := <-videoChan
                    conn.SendToolResponse("captureSnapshot", map[string]string{"image_bytes": base64.StdEncoding.EncodeToString(img)})
                case "uploadToS3":
                    b, _ := base64.StdEncoding.DecodeString(fc.Args["bytes"].(string))
                    url, _ := uploadToS3(user.Code, b)
                    conn.SendToolResponse("uploadToS3", map[string]string{"url": url})
                case "generateQR":
                    png, _ := qrcode.Encode(fc.Args["url"].(string), qrcode.Medium, 256)
                    conn.SendToolResponse("generateQR", map[string]string{"qr_b64": base64.StdEncoding.EncodeToString(png)})
                case "displayOnTV":
                    displayOnTV(fc.Args["img_b64"].(string))
                    conn.SendToolResponse("displayOnTV", map[string]string{"status": "ok"})
                }
            }
        }
    }()

    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt)
    <-c
}

type User struct{ Name, Code string }

func graphqlIdentify(qr string) (*User, error) {
    // Înlocuiește cu apel real GraphQL
    return &User{Name: "Adrian", Code: "WR1234"}, nil
}

func streamMicAudio(out chan<- []byte) {
    portaudio.Initialize(); defer portaudio.Terminate()
    enc, _ := gopus.NewEncoder(48000, 1, gopus.AppAudio)
    stream, _ := portaudio.OpenDefaultStream(1, 0, 48000, 960, func(in []int16) {
        pcm := make([]float32, len(in))
        for i := range in {
            pcm[i] = float32(in[i]) / 32768
        }
        if data, err := enc.Encode(pcm, 960, 4000); err == nil {
            out <- data
        }
    })
    defer stream.Close()
    stream.Start()
    select {}
}

func playAudio(in <-chan []byte) {
    portaudio.Initialize(); defer portaudio.Terminate()
    dec, _ := gopus.NewDecoder(48000, 1)
    stream, _ := portaudio.OpenDefaultStream(0, 1, 48000, 960, func(out []int16) {
        select {
        case data := <-in:
            pcm := make([]int16, 960)
            if _, err := dec.Decode(data, pcm, false); err == nil {
                copy(out, pcm)
            }
        default:
            for i := range out {
                out[i] = 0
            }
        }
    })
    defer stream.Close()
    stream.Start()
    select {}
}

func webcamStream(out chan<- []byte, stop <-chan struct{}) {
    cam, err := gocv.VideoCaptureDevice(0)
    if err != nil { log.Fatalf("webcam error: %v", err) }
    defer cam.Close()
    img := gocv.NewMat(); defer img.Close()
    ticker := time.NewTicker(100 * time.Millisecond)
    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            if ok := cam.Read(&img); !ok || img.Empty() {
                continue
            }
            if buf, err := gocv.IMEncode(".jpg", img); err == nil {
                out <- buf.GetBytes()
            }
        case <-stop:
            return
        }
    }
}

func webcamQRScanner(out chan<- []byte, stop <-chan struct{}, qrChan chan<- string) {
    cam, _ := gocv.VideoCaptureDevice(0)
    defer cam.Close()
    img := gocv.NewMat(); defer img.Close()
    qcd := gocv.NewQRCodeDetector()
    defer qcd.Close()
    ticker := time.NewTicker(100 * time.Millisecond)
    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            if ok := cam.Read(&img); !ok || img.Empty() {
                continue
            }
            if buf, err := gocv.IMEncode(".jpg", img); err == nil {
                out <- buf.GetBytes()
            }
            if code := qcd.DetectAndDecode(img); code != "" {
                qrChan <- code
                return
            }
        case <-stop:
            return
        }
    }
}

func uploadToS3(userCode string, data []byte) (string, error) {
    sess := session.Must(session.NewSession())
    svc := s3.New(sess)
    key := fmt.Sprintf("%s/%s.jpg", userCode, uuid.New().String())
    _, err := svc.PutObject(&s3.PutObjectInput{
        Bucket: aws.String("festival-booth"), Key: aws.String(key), Body: bytes.NewReader(data),
    })
    return fmt.Sprintf("https://festival-booth.s3.amazonaws.com/%s", key), err
}

func displayOnTV(imgB64 string) {
    data, err := base64.StdEncoding.DecodeString(imgB64)
    if err != nil { log.Printf("TV decode err: %v", err); return }
    mat, err := gocv.IMDecode(data, gocv.IMReadColor)
    if err != nil { log.Printf("IMDecode err: %v", err); return }
    defer mat.Close()
    win := gocv.NewWindow("FestivalBooth")
    defer win.Close()
    win.SetWindowProperty(gocv.WindowPropertyFullscreen, gocv.WindowFullscreen)
    win.IMShow(mat)
    win.WaitKey(60000)
}

func schema(s string) interface{} { return map[string]interface{}{} }
