import requests
import time
import json

# Your AudD API key
API_KEY = "b86161e9f95cc24b3bc391263d06aa09"

# File to analyze
INPUT_FILE = "mix.mp3"
SEGMENT_DURATION = 15000  # in milliseconds (15 seconds)
SKIP_GAP = 10000  # in milliseconds (10 seconds)
OUTPUT_LOG = "tracklist_audd.txt"

# Function to send the audio segment to AudD for recognition
def recognize_audio(file_path):
    url = "https://api.audd.io/"
    files = {'file': open(file_path, 'rb')}
    data = {
        'api_token': API_KEY,
        'return': 'apple_music,spotify,deezer,shazam',
    }
    
    response = requests.post(url, files=files, data=data)
    return response.json()

# Track processing
def process_audio_segment(start, segment, timestamp):
    temp_file = "temp_segment.mp3"
    segment.export(temp_file, format="mp3")

    result = recognize_audio(temp_file)
    
    if 'result' in result and result['result']:
        track = result['result']
        track_info = f"{track.get('artist')} – {track.get('title')}"
        print(f"[{timestamp}] {track_info}")
        return track_info
    else:
        print(f"[{timestamp}] Track non identifié")
        return "Track non identifié"

# Main function
def main():
    from pydub import AudioSegment
    audio = AudioSegment.from_file(INPUT_FILE)
    duration = len(audio)
    
    detected_tracks = []

    with open(OUTPUT_LOG, "w") as f:
        print(f"Durée totale du mix : {duration / 1000:.2f} secondes")
        print("Analyse en cours...")

        for start in range(0, duration, SEGMENT_DURATION + SKIP_GAP):
            segment = audio[start:start + SEGMENT_DURATION]
            timestamp = f"{start // 60000:02d}:{(start // 1000) % 60:02d}"

            track_info = process_audio_segment(start, segment, timestamp)

            if track_info not in detected_tracks:
                f.write(f"[{timestamp}] {track_info}\n")
                detected_tracks.append(track_info)
            time.sleep(1)  # To avoid hitting API limits

    print(f"Tracklist sauvegardée dans {OUTPUT_LOG}")

# Run the main function
if __name__ == "__main__":
    main()