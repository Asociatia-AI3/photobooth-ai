import asyncio
import os
import base64
import uuid
import sounddevice as sd
import numpy as np
import boto3
import qrcode
import cv2
from google import genai
from google.genai.types import Content, FunctionDeclaration, Tool, LiveConnectConfig, Modality

# Configure Gemini
# client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
client = genai.Client(api_key="AIzaSyCMMf5dbdGXQ4_PEh5SfNpmGnub5JGkKDI")
S3_BUCKET = os.getenv("BUCKET_NAME", "festival-booth")

# 🎫 Mock GraphQL
async def identify_user(qr: str) -> dict:
    return {"name": "Adrian", "code": qr}

# 📸 Funcții callback
def capture_snapshot() -> str:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf).decode()

def upload_to_s3(bytes_b64: str, user_code: str) -> str:
    s3 = boto3.client("s3")
    data = base64.b64decode(bytes_b64)
    key = f"{user_code}/{uuid.uuid4()}.jpg"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ACL="public-read")
    return f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"

def generate_qr(url: str) -> str:
    img = qrcode.make(url)
    buf = cv2.imencode(".png", cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))[1]
    return base64.b64encode(buf).decode()

def display_on_tv(img_b64: str):
    data = base64.b64decode(img_b64)
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    cv2.namedWindow("TV", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("TV", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("TV", img)
    cv2.waitKey(60000)
    cv2.destroyAllWindows()

# ✅ Flux principal
async def main():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    qr = None
    print("📸 Scanează QR de pe bilet...")
    while qr is None:
        ret, frame = cap.read()
        if not ret: continue
        cv2.imshow("Scanare QR", frame)
        data, _, _ = detector.detectAndDecode(frame)
        if data:
            qr = data
            break
        if cv2.waitKey(1) & 0xFF == ord("q"):
            return
    cap.release()
    cv2.destroyAllWindows()

    user = await identify_user(qr)
    print("🎟️ Welcome:", user)

    tools = [
        Tool(function_declarations=[
            FunctionDeclaration(name="capture_snapshot", description="Take webcam photo", parameters={"type":"object","properties":{},"required":[]}),
            FunctionDeclaration(name="upload_to_s3", description="Upload photo", parameters={"type":"object","properties":{"bytes":{"type":"string"},"user_code":{"type":"string"}},"required":["bytes","user_code"]}),
            FunctionDeclaration(name="generate_qr", description="Make QR code", parameters={"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}),
            FunctionDeclaration(name="display_on_tv", description="Display image on TV", parameters={"type":"object","properties":{"img_b64":{"type":"string"}},"required":["img_b64"]}),
        ])
    ]

    async with client.aio.live.connect(
        model="gemini-2.0-flash-live-preview-04-09",
        config=LiveConnectConfig(response_modalities=[Modality.AUDIO, Modality.TEXT], tools=tools),
    ) as session:
        print("📢 Starting session...")
        await session.send_client_content(Content(parts=[{"text": f"Salut, {user['name']}! Vrei o poză?"}]))

        async for msg in session.receive():
            if msg.text:
                print("Gemini:", msg.text)
            if msg.tool_call:
                name = msg.tool_call.name
                args = msg.tool_call.arguments or {}
                if name == "capture_snapshot":
                    res = capture_snapshot()
                elif name == "upload_to_s3":
                    res = upload_to_s3(args["bytes"], user["code"])
                elif name == "generate_qr":
                    res = generate_qr(args["url"])
                elif name == "display_on_tv":
                    res = (display_on_tv(args["img_b64"]) or "ok")
                else:
                    res = ""
                await session.send_tool_response([{"name": name, "response": res}])

if __name__ == "__main__":
    asyncio.run(main())
    