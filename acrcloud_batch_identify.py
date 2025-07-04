import os
from pydub import AudioSegment
from acrcloud.recognizer import ACRCloudRecognizer
import time
import json

# Configuration ACRCloud
config = {
    'host': 'identify-eu-west-1.acrcloud.com',  # Remplace avec ton hôte
    'access_key': '4e9014baa9d65215e6e418f071daec44',  # Remplace avec ta clé d'accès
    'access_secret': 'XxpsCnDhpHTAYCsyqJY9Tf2cd4SDYXCtNkqgQnao',  # Remplace avec ton secret
    'timeout': 10  # Timeout en secondes
}

recognizer = ACRCloudRecognizer(config)

# Fichier mix à analyser
INPUT_FILE = "mix.mp3"
SEGMENT_DURATION = 15000  # en millisecondes (15 secondes)
SKIP_GAP = 10000  # en millisecondes (10 secondes)
OUTPUT_LOG = "tracklist.txt"

audio = AudioSegment.from_file(INPUT_FILE)
duration = len(audio)

print(f"Durée totale du mix : {duration / 1000:.2f} secondes")
print("Analyse en cours...")

detected_tracks = []

with open(OUTPUT_LOG, "w") as f:
    for start in range(0, duration, SEGMENT_DURATION + SKIP_GAP):
        segment = audio[start:start+SEGMENT_DURATION]
        temp_file = "temp_segment.mp3"
        segment.export(temp_file, format="mp3")

        result = recognizer.recognize_by_file(temp_file, 0)
        timestamp = f"{start // 60000:02d}:{(start // 1000) % 60:02d}"

        if '"title":"' in result:
            data = json.loads(result)
            try:
                metadata = data['metadata']['music'][0]
                title = metadata['title']
                artist = metadata['artists'][0]['name']
                track = f"{artist} – {title}"
                if track not in detected_tracks:
                    f.write(f"[{timestamp}] {track}\n")
                    print(f"[{timestamp}] {track}")
                    detected_tracks.append(track)
            except Exception:
                f.write(f"[{timestamp}] Track non identifié\n")
        else:
            f.write(f"[{timestamp}] Track non identifié\n")

        time.sleep(1)  # éviter les limites d’API

os.remove("temp_segment.mp3")
print(f"Tracklist sauvegardée dans {OUTPUT_LOG}")