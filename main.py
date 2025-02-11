import sys
import os
import lyricsgenius
import json
import re
import threading
import config


genius = lyricsgenius.Genius(config.API_KEY, timeout=60)

data_dir = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# searches for word in the artists lyrics
def search_word_in_lyrics(word, artist_data, artist_name):
    word = word.lower()
    found = False
    result = []
    if 'songs' in artist_data:
        for song in artist_data['songs']:
            if not song.get('lyrics'):
                continue
            lyrics_lines = song['lyrics'].split('\n')
            matching_lines = [line for line in lyrics_lines if word in re.sub(r'\[.*?\]', '', line).lower()]
            if matching_lines:
                result.append((song['title'], matching_lines))
                found = True
    if not found:
        result.append((f"Word '{word}' not found in any song of artist '{artist_name}'.", []))
    return result


# gets artist data, downloads songs if not already saved
def get_artist_data_with_progress(artist_name, progress_callback=None, force_update=False):
    data_file = os.path.join(data_dir, f"{artist_name}_lyrics.json")
    if not force_update and os.path.exists(data_file):
        # load cache
        with open(data_file, 'r', encoding='utf-8') as file:
            artist_data = json.load(file)
            return artist_data
    
    # search data
    artist = genius.search_artist(artist_name, max_songs=1, get_full_info=False)
    if artist:
        artist_id = artist.id
        songs = []
        page = 1
        per_page = 50
        total_songs = None
        while True:
            response = genius.artist_songs(artist_id, page=page, per_page=per_page)
            if response and 'songs' in response:
                songs.extend(response['songs'])
                if progress_callback:
                    progress_callback(len(songs), 'unknown')
                if response['next_page']:
                    page += 1
                else:
                    break
            else:
                break
        song_objs = []
        total_songs = len(songs)
        for idx, song_info in enumerate(songs):
            song = genius.song(song_info['id'])
            if song and 'song' in song:
                song_lyrics = genius.lyrics(song_url=song['song']['url'])
                song_obj = {
                    'title': song['song']['title'],
                    'lyrics': song_lyrics
                }
                song_objs.append(song_obj)
            if progress_callback:
                progress_callback(idx + 1, total_songs)
        artist_data = {
            'artist': {
                'name': artist.name,
                'image_url': artist.image_url
            },
            'songs': song_objs
        }
        with open(data_file, 'w', encoding='utf-8') as file:
            json.dump(artist_data, file, ensure_ascii=False)
        return artist_data
    else:
        return None

