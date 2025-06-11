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

    "github.com/google/uuid"
    "github.com/gordonklaus/portaudio"
    "layeh.com/gopus"
    "gocv.io/x/gocv"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/s3"
    "github.com/skip2/go-qrcode"
    "google.golang.org/genai"
    "google.golang.org/genai/genaiws"
)

// Canale globale pentru streaming audio/video
var (
    audioChan = make(chan []byte, 100)
    videoChan = make(chan []byte, 10)
)

func main() {
    // Pornește streaming continui audio și video
    go streamMicAudio(audioChan)
    go playAudio(audioChan)
    stopVid := make(chan struct{})
    go webcamStream(videoChan, stopVid)

    // Inițializează client Gemini Live
    ctx := context.Background()
    client, err := genai.NewClient(ctx, &genai.ClientConfig{APIKey: os.Getenv("GEMINI_API_KEY")})
    if err != nil {
        log.Fatal(err)
    }

    // Declarații function-call
    tools := []genaiws.FunctionDeclaration{
        {Name: "identifyUser", Description: "Identify via QR", Parameters: schema(`{"type":"object","properties":{"qr_data":{"type":"string"}},"required":["qr_data"]}`)},
        {Name: "captureSnapshot", Description: "Take webcam snapshot", Parameters: schema(`{"type":"object","properties":{},"required":[]}`)},
        {Name: "uploadToS3", Description: "Upload image bytes", Parameters: schema(`{"type":"object","properties":{"bytes":{"type":"string"},"user_code":{"type":"string"}},"required":["bytes","user_code"]}`)},
        {Name: "generateQR", Description: "Generate QR code", Parameters: schema(`{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}`)},
        {Name: "displayOnTV", Description: "Show image on TV", Parameters: schema(`{"type":"object","properties":{"img_b64":{"type":"string"}},"required":["img_b64"]}`)},
    }

    conn, err := genaiws.DialLive(ctx, client, "gemini-2.0-flash-live-preview-04-09", genaiws.LiveConfig{
        ResponseModalities: []genaiws.Modality{genaiws.ModalityAudio, genaiws.ModalityText},
        Tools:              tools,
    })
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    conn.SendText("standby")

    // Handler pentru function_call-uri Gemini
    go func() {
        for msg := range conn.Receive() {
            if fc := msg.FunctionCall; fc != nil {
                switch fc.Name {
                case "identifyUser":
                    qr := fc.Args["qr_data"].(string)
                    user, _ := graphqlIdentify(qr)
                    conn.SendToolResponse("identifyUser", map[string]string{
                        "user_name": user.Name, "user_code": user.Code,
                    })
                case "captureSnapshot":
                    img := <-videoChan
                    conn.SendToolResponse("captureSnapshot", map[string]string{
                        "image_bytes": base64.StdEncoding.EncodeToString(img),
                    })
                case "uploadToS3":
                    b, _ := base64.StdEncoding.DecodeString(fc.Args["bytes"].(string))
                    url, _ := uploadToS3(fc.Args["user_code"].(string), b)
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

    // Așteaptă CTRL+C pentru oprire
    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt)
    <-c
    close(stopVid)
    conn.Close()
}

// Funții helper

type User struct{ Name, Code string }

func graphqlIdentify(qr string) (*User, error) {
    // înlocuiește cu GraphQL real
    return &User{Name: "Adrian", Code: "WR1234"}, nil
}

func uploadToS3(userCode string, img []byte) (string, error) {
    sess := session.Must(session.NewSession())
    svc := s3.New(sess)
    key := fmt.Sprintf("%s/%s.jpg", userCode, uuid.New().String())
    _, err := svc.PutObject(&s3.PutObjectInput{
        Bucket: aws.String("festival-booth"),
        Key:    aws.String(key),
        Body:   bytes.NewReader(img),
    })
    return fmt.Sprintf("https://festival-booth.s3.amazonaws.com/%s", key), err
}

// Afișează imagine base64 full-screen pe TV folosind GoCV
func displayOnTV(imgB64 string) {
    data, err := base64.StdEncoding.DecodeString(imgB64)
    if err != nil {
        log.Printf("displayOnTV: decode error: %v", err)
        return
    }
    mat, err := gocv.IMDecode(data, gocv.IMReadColor)
    if err != nil {
        log.Printf("displayOnTV: IMDecode error: %v", err)
        return
    }
    defer mat.Close()

    window := gocv.NewWindow("FestivalBooth")
    defer window.Close()
    window.SetWindowProperty(gocv.WindowPropertyFullscreen, gocv.WindowFullscreen)
    window.IMShow(mat)
    // Afișează QR-ul cel puțin 60s
    window.WaitKey(60000)
}

// Streaming audio și video continuu

func streamMicAudio(out chan<- []byte) {
    portaudio.Initialize()
    defer portaudio.Terminate()
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
    <-make(chan os.Signal, 1)
    stream.Stop()
}

func playAudio(in <-chan []byte) {
    portaudio.Initialize()
    defer portaudio.Terminate()
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
    if err != nil {
        log.Fatalf("webcam open: %v", err)
    }
    defer cam.Close()
    img := gocv.NewMat()
    defer img.Close()
    ticker := time.NewTicker(100 * time.Millisecond)
    defer ticker.Stop()
    for {
        select {
        case <-ticker.C:
            if ok := cam.Read(&img); ok && !img.Empty() {
                if buf, err := gocv.IMEncode(".jpg", img); err == nil {
                    out <- buf.GetBytes()
                }
            }
        case <-stop:
            return
        }
    }
}

func schema(s string) interface{} { return map[string]interface{}{} }
