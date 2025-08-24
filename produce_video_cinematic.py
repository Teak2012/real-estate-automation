import os
import requests
import random
from bs4 import BeautifulSoup
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, afx
from gtts import gTTS

HF_API_KEY = os.environ['HF_API_KEY']
PIXABAY_KEY = os.environ['PIXABAY_KEY']
UPLOAD_URL = os.environ['UPLOAD_URL']
UPLOAD_TOKEN = os.environ['UPLOAD_TOKEN']
TEMP_DIR = "temp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

# 1. Scrape property images
def scrape_images(property_url):
    resp = requests.get(property_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    imgs = [img['src'] for img in soup.find_all('img') if 'property' in img.get('src','')]
    local_imgs = []
    for idx, img_url in enumerate(imgs[:10]):
        r = requests.get(img_url)
        path = f"{TEMP_DIR}/{idx}.jpg"
        with open(path,"wb") as f: f.write(r.content)
        local_imgs.append(path)
    return local_imgs

# 2. Generate narration script
def generate_script(property_url):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": f"Professional real estate marketing script for {property_url}", "parameters":{"max_new_tokens":250}}
    r = requests.post("https://api-inference.huggingface.co/models/gpt2", headers=headers, json=payload)
    data = r.json()
    return data[0]['generated_text']

# 3. TTS narration
def create_narration(text):
    tts = gTTS(text)
    path = f"{TEMP_DIR}/narration.mp3"
    tts.save(path)
    return path

# 4. Fetch Pixabay music
def download_pixabay_music(query="real estate upbeat"):
    url = f"https://pixabay.com/api/music/?key={PIXABAY_KEY}&q={query}&per_page=10"
    resp = requests.get(url).json()
    hits = resp.get("hits", [])
    if not hits: return "background.mp3"
    mp3_url = random.choice(hits).get("music_url")
    path = f"{TEMP_DIR}/background.mp3"
    r = requests.get(mp3_url)
    with open(path,"wb") as f: f.write(r.content)
    return path

# 5. Cinematic video creation
def create_video(images, narration, music_file):
    clips = []
    for idx, img_path in enumerate(images):
        clip = ImageClip(img_path).set_duration(3).fx(afx.fadein,0.5).fx(afx.fadeout,0.5)
        clip = clip.resize(random.uniform(1.05,1.2))
        txt = TextClip(f"Feature {idx+1}", fontsize=50,color='white',font='Amiri-Bold').set_duration(3).set_position(('center','bottom'))
        clips.append(CompositeVideoClip([clip, txt]))
    video = concatenate_videoclips(clips, method="compose", padding=-0.5)
    audio = AudioFileClip(narration)
    music = AudioFileClip(music_file).volumex(0.3)
    video = video.set_audio(audio)
    out_file = "property_video.mp4"
    video.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac")
    return out_file

# 6. Upload video to Apps Script
def upload(video_file):
    with open(video_file,"rb") as f:
        r = requests.post(UPLOAD_URL, files={"file": (os.path.basename(video_file),f)}, data={"token":UPLOAD_TOKEN})
    print(r.text)

if __name__=="__main__":
    import sys
    property_url = sys.argv[1]
    images = scrape_images(property_url)
    script = generate_script(property_url)
    narration = create_narration(script)
    music_file = download_pixabay_music()
    video_file = create_video(images, narration, music_file)
    upload(video_file)
