import base64, json, sys, urllib.request
from pathlib import Path
KEY = [l.split("=", 1)[1].strip() for l in open(Path.home() / "workspace/k1-meal-delivery/.env") if l.startswith("GEMINI_API_KEY=")][0]
def transcribe(path, model="gemini-2.5-flash"):
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(open(path, "rb").read()).decode()}},
                                    {"text": "Transcribe this audio verbatim. Then on a new line write SILENCE: and estimate total seconds of silence/dead air, and QUALITY: one short phrase on how natural/human the voice sounds."}]}]}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": KEY})
    d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("=====", p); print(transcribe(p))
