import os
import subprocess
import requests
from pydub import AudioSegment
from tqdm import tqdm
import acoustid
import time
import urllib.parse

# Configuration
DJ_MIX_PATH = "mix.mp3"  # Replace with your file
CHUNK_LENGTH_MS = 60 * 1000
STEP_MS = 30 * 1000
TEMP_DIR = "chunks"
ACOUSTID_API_KEY = "f0sR0DEXWc"  # Replace with your real key

# Ensure output folder exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Load audio
audio = AudioSegment.from_file(DJ_MIX_PATH)
total_length = len(audio)
print(f"Loaded mix: {total_length / 1000:.1f} seconds")

# Rate limiting setup
last_request_time = 0
min_interval = 1 / 3  # 3 requests per second

# Split and analyze
for start in tqdm(range(0, total_length - CHUNK_LENGTH_MS + 1, STEP_MS), desc="Processing chunks"):
    end = start + CHUNK_LENGTH_MS
    chunk = audio[start:end]
    chunk = chunk.set_channels(1).set_frame_rate(44100).set_sample_width(2)
    chunk_path = os.path.join(TEMP_DIR, f"chunk_{start}.wav")
    chunk.export(chunk_path, format="wav")

    try:
        # Generate fingerprint using pyacoustid
        duration, fingerprint = acoustid.fingerprint_file(chunk_path)

        print(f"Generated fingerprint for chunk starting at {start//1000}s: {fingerprint[:50]}...")

        # Enforce rate limiting
        elapsed = time.time() - last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        # Use an approximate duration for individual tracks in DJ mixes
        total_duration = 180  # seconds

        # Use the total duration of the track, not the chunk's duration
        duration_str = str(int(total_duration))

        # Construct the parameters with URL encoding
        meta = "recordings+releasegroups+compress"

        # Query AcoustID (using GET instead of POST)
        print(f"\n🔎 Identifying chunk starting at {start//1000}s ({start//1000}s - {end//1000}s)...")
        url = "https://api.acoustid.org/v2/lookup"
        params = {
            "client": ACOUSTID_API_KEY,
            "meta": meta,  # Use the properly encoded meta parameter
            "duration": duration_str,  # Pass the total track duration
            "fingerprint": fingerprint.decode("ascii")
        }
        params_encoded = "&".join([f"{k}={v}" for k, v in params.items()])
        response = requests.get(f"{url}?{params_encoded}")

        # Debugging - print request and response
        #print(f"Request URL: {response.request.url}")
        print(f"Response Status: {response.status_code}")
        #print(f"Response data: {response.json()}")  # Print the full response
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                print(f"✅ Match found (score: {data['results'][0]['score']:.2f}):")
                for recording in data['results'][0].get('recordings', []):
                    title = recording.get("title", "Unknown")
                    artists = ", ".join([a['name'] for a in recording.get('artists', [])])
                    print(f"    🎵 {title} — {artists}")

                # If additional information was already included in the response, no need for further requests
                if 'recordings' in data['results'][0]:
                    print(f"    🎵 Title: {data['results'][0]['recordings'][0].get('title', 'Unknown')}")
                    print(f"    🎤 Artists: {', '.join([artist['name'] for artist in data['results'][0]['recordings'][0].get('artists', [])])}")
                    print(f"    📀 Release Groups: {', '.join([releasegroup['title'] for releasegroup in data['results'][0]['recordings'][0].get('releasegroups', [])])}")
            else:
                print("❌ No match found")
        else:
            print(f"❌ API request failed with status: {response.status_code}, message: {response.text}")

        # Add a short delay between requests to avoid throttling
        time.sleep(1)

    except acoustid.FingerprintGenerationError as e:
        print(f"[!] Fingerprint generation error for chunk starting at {start}: {e}")
    except requests.RequestException as e:
        print(f"[!] Request error for chunk starting at {start}: {e}")
    except Exception as e:
        print(f"[!] Unexpected error for chunk starting at {start}: {e}")