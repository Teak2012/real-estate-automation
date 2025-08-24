import os, requests, random, asyncio
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, afx
from gtts import gTTS
from playwright.async_api import async_playwright

HF_API_KEY = os.environ['HF_API_KEY']
PIXABAY_KEY = os.environ['PIXABAY_KEY']
UPLOAD_URL = os.environ['UPLOAD_URL']
UPLOAD_TOKEN = os.environ['UPLOAD_TOKEN']
TEMP_DIR = "temp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

# Scrape images with Playwright
async def scrape_images(url):
    images = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        img_elements = await page.query_selector_all("img")
        for idx, img in enumerate(img_elements):
            src = await img.get_attribute("src")
            if src and "property" in src:
                r = requests.get(src)
                path = os.path.join(TEMP_DIR, f"{idx}.jpg")
                with open(path, "wb") as f: f.write(r.content)
                images.append(path)
        await browser.close()
    return images[:10]  # Limit to 10 images

# Generate marketing script using Hugging Face
def generate_script(property_url):
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": f"Create a professional real estate marketing script for {property_url}", "parameters":{"max_new_tokens":250}}
        r = requests.post("https://api-inference.huggingface.co/models/gpt2", headers=headers, json=payload)
        return r.json()[0]['generated_text']
    except:
        return "Discover this amazing property with our professional marketing video!"

# Create narration audio
def create_narration(text):
    path = os.path.join(TEMP_DIR, "narration.mp3")
    gTTS(text).save(path)
    return path

# Download music from Pixabay
def download_pixabay_music(query="real estate upbeat"):
    try:
        url = f"https://pixabay.com/api/music/?key={PIXABAY_KEY}&q={query}&per_page=10"
        resp = requests.get(url).json()
        hits = resp.get("hits", [])
        if not hits: return None
        mp3_url = random.choice(hits).get("music_url")
        if not mp3_url: return None
        path = os.path.join(TEMP_DIR, "background.mp3")
        r = requests.get(mp3_url)
        with open(path,"wb") as f: f.write(r.content)
        return path
    except:
        return None

# Create cinematic video
def create_video(images, narration, music_file=None):
    clips = []
    for idx, img_path in enumerate(images):
        clip = ImageClip(img_path).set_duration(3).fx(afx.fadein,0.5).fx(afx.fadeout,0.5)
        clip = clip.resize(random.uniform(1.05,1.2))
        txt = TextClip(f"Feature {idx+1}", fontsize=50,color='white',font='Amiri-Bold').set_duration(3).set_position(('center','bottom'))
        clips.append(CompositeVideoClip([clip, txt]))
    video = concatenate_videoclips(clips, method="compose")
    audio = AudioFileClip(narration)
    if music_file:
        music = AudioFileClip(music_file).volumex(0.3)
        audio = afx.audio_fadein(audio,1).volumex(1.0).set_audio(audio)
    video = video.set_audio(audio)
    out_file = "property_video.mp4"
    video.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac")
    return out_file

# Upload video to Apps Script
def upload(video_file):
    with open(video_file,"rb") as f:
        r = requests.post(UPLOAD_URL, files={"file": (os.path.basename(video_file),f)}, data={"token":UPLOAD_TOKEN})
    print(r.text)

# Main
async def main():
    import sys
    property_url = sys.argv[1]
    if not property_url:
        print("ERROR: No property URL provided")
        return
    images = await scrape_images(property_url)
    if not images:
        print("No images found, exiting")
        return
    script = generate_script(property_url)
    narration = create_narration(script)
    music_file = download_pixabay_music()
    video_file = create_video(images, narration, music_file)
    upload(video_file)

if __name__=="__main__":
    asyncio.run(main())
