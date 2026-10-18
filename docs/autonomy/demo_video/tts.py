import base64, json, sys, time, urllib.request, urllib.error, wave
from pathlib import Path
ROOT = Path.home() / "workspace/k1-meal-delivery"
KEY = [l.split("=", 1)[1].strip() for l in open(ROOT / ".env") if l.startswith("GEMINI_API_KEY=")][0]

def tts(text, out, voice="Charon", model="gemini-2.5-pro-preview-tts", style=""):
    body = {"contents": [{"parts": [{"text": (style + "\n\n" + text) if style else text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    for i in range(6):
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                         json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": KEY})
            d = json.loads(urllib.request.urlopen(req, timeout=180).read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read()[:200].decode(errors="replace")
            if e.code in (429, 500, 503) and i < 5:
                time.sleep(15 * (i + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    pcm = base64.b64decode(part["data"])
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    return len(pcm) / 2 / 24000

if __name__ == "__main__":
    print(round(tts(sys.argv[1], sys.argv[2], *(sys.argv[3:5])), 2))
