import os
import asyncio
import csv
from pydub import AudioSegment
from shazamio import Shazam
from mutagen.easyid3 import EasyID3
import time

# --- Configuration ---
DJ_MIX_PATH = "mix.mp3"
CHUNK_LENGTH_MS = 12 * 1000
TEMP_DIR = "chunks"
MAX_REQUESTS_PER_MINUTE = 19
SECONDS_IN_A_MINUTE = 60
SHAMIO_DELAY = SECONDS_IN_A_MINUTE / MAX_REQUESTS_PER_MINUTE
SKIP_CHUNKS = 3

os.makedirs(TEMP_DIR, exist_ok=True)

def format_time(ms):
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    seconds = seconds % 60
    minutes = minutes % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def generate_playlist_name(mp3_path):
    try:
        tags = EasyID3(mp3_path)
        date_tag = tags.get("date", ["UnknownDate"])[0].replace("-", "")
        title_tag = tags.get("title", ["UnknownTitle"])[0]
        return f"{date_tag}-{title_tag}"
    except Exception as e:
        print(f"❌ Impossible de lire les tags ID3 : {e}")
        return "UnknownDate-UnknownTitle"

class DJMixIdentifier:
    def __init__(self, mix_path):
        self.mix_path = mix_path
        self.audio = AudioSegment.from_file(mix_path)
        self.total_length = len(self.audio)
        self.shazam = Shazam()
        self.playlist_name = generate_playlist_name(mix_path)
        self.csv_file = f"{self.playlist_name}.csv"
        self.seen_tracks = set()
        print(f"Chargement du mix : {self.total_length / 1000:.1f} secondes")

    async def process_chunk(self, start_ms, chunk_audio):
        chunk_path = os.path.join(TEMP_DIR, f"chunk_{start_ms}.mp3")
        chunk_audio.export(chunk_path, format="mp3")
        print(f"\n🔎 Identifier le morceau à partir de {start_ms // 1000}s...")
        try:
            out = await self.shazam.recognize(chunk_path)
            if out:
                print(f"Réponse Shazam : {out}")
                if 'track' in out and 'title' in out['track']:
                    title = out['track']['title']
                    artist = out['track'].get('subtitle', 'Unknown')
                    apple_music_id = None
                    if 'hub' in out['track'] and 'actions' in out['track']['hub']:
                        for action in out['track']['hub']['actions']:
                            if action.get('type') == 'applemusicplay':
                                apple_music_id = action.get('id')
                                break
                    if apple_music_id is None:
                        apple_music_id = 'ID non disponible'
                    apple_music_url = out['track'].get('url', 'URL non disponible')
                    album = 'Unknown'
                    if 'sections' in out['track']:
                        for section in out['track']['sections']:
                            if 'metadata' in section:
                                album_metadata = section.get('metadata', [])
                                for metadata in album_metadata:
                                    if metadata.get('title') == 'Album':
                                        album = metadata.get('text', 'Unknown')
                                        break
                    track_identifier = (title, artist)
                    if track_identifier not in self.seen_tracks:
                        self.seen_tracks.add(track_identifier)
                        print(f"    🎵 {title} - {artist}")
                        time_identified_in_mix = format_time(start_ms)
                        with open(self.csv_file, mode='a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([time_identified_in_mix, title, artist, album, apple_music_id, apple_music_url])
                    else:
                        print(f"    🎵 {title} - {artist} (Déjà trouvé, ignoré)")
                else:
                    print("❌ Erreur lors de l'identification du morceau : 'title' non trouvé")
            else:
                print("❌ Aucune correspondance trouvée.")
        except Exception as e:
            print(f"❌ Erreur lors de l'identification du morceau : {e}")

    async def identify_dj_mix(self):
        # Write header to CSV if it's the first run
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if f.tell() == 0:
                    writer.writerow(["Time Identified (HH:MM:SS)", "Title", "Artist", "Album", "Apple Music Track ID", "Apple Music URL"])
        requests_sent = 0
        for start_ms in range(0, self.total_length, CHUNK_LENGTH_MS):
            if (start_ms // CHUNK_LENGTH_MS) % SKIP_CHUNKS != 0:
                continue
            end_ms = min(start_ms + CHUNK_LENGTH_MS, self.total_length)
            chunk_audio = self.audio[start_ms:end_ms]
            await self.process_chunk(start_ms, chunk_audio)
            requests_sent += 1
            if requests_sent < MAX_REQUESTS_PER_MINUTE:
                await asyncio.sleep(SHAMIO_DELAY)
            else:
                requests_sent = 0

def main():
    identifier = DJMixIdentifier(DJ_MIX_PATH)
    print(f"\nNom de la playlist à créer : {identifier.playlist_name} (fichier CSV : {identifier.csv_file})")
    create_playlist = input("Souhaitez-vous créer une playlist Apple Music avec ces morceaux ? (o/n) : ")
    if create_playlist.strip().lower() == 'o':
        print(f"✅ Playlist à créer : {identifier.playlist_name}")
        identify_tracks = input("Souhaitez-vous maintenant identifier les morceaux dans le mix ? (o/n) : ")
        if identify_tracks.strip().lower() == 'o':
            print("✅ Identification des morceaux commencée...")
            asyncio.run(identifier.identify_dj_mix())
    else:
        print("ℹ️ Création de playlist annulée.")

if __name__ == "__main__":
    main()