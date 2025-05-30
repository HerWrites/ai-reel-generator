# generator.py  (place in root of repo)
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess, uuid, os, base64, requests, json, asyncio, edge_tts

app = FastAPI()

class Job(BaseModel):
    prompt: str   # what to show
    style: str    # "story" or "scenic"

HORDE_KEY = "PASTE_YOUR_STABLE_HORDE_KEY_HERE"  # free key from stablehorde.net

async def make_tts(text, out_mp3):
    communicate = edge_tts.Communicate(text=text, voice="en-US-AriaNeural")
    await communicate.save(out_mp3)

def horde_image(prompt, out_png):
    payload = {
        "prompt": prompt,
        "params": {"n": 1, "width": 768, "height": 1344}
    }
    r = requests.post(
        "https://stablehorde.net/api/v2/generate/sync",
        headers={
            "apikey": HORDE_KEY,
            "client-agent": "n8n-reel/0.1"
        },
        data=json.dumps(payload),
        timeout=300
    )
    r.raise_for_status()
    url = r.json()["generations"][0]["img"]
    open(out_png, "wb").write(requests.get(url).content)

@app.post("/generateReel")
async def generate(job: Job):
    work = f"/tmp/{uuid.uuid4()}"
    os.makedirs(work, exist_ok=True)
    img = f"{work}/img.png"
    audio = f"{work}/audio.mp3"
    video = f"{work}/final.mp4"

    # 1) picture
    horde_image(job.prompt, img)

    # 2) audio
    if job.style == "story":
        await make_tts(job.prompt, audio)
    else:
        import random, glob, shutil
        track = random.choice(glob.glob("/workspace/music/*.mp3"))
        shutil.copy(track, audio)

    # 3) 30-sec vertical video
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", img,
        "-i", audio,
        "-t", "30", "-r", "30",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
        "-c:a", "aac", "-b:a", "128k", "-shortest", video
    ], check=True)

    data_b64 = base64.b64encode(open(video, "rb").read()).decode()
    return {"fileName": "reel.mp4", "data": data_b64}
