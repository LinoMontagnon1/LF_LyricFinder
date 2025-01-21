import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import requests
import io
import threading
import numpy as np
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main
from interface import SecondPage

# constants for styling and fonts
FONT_ARTIST_NAME = ('Comic Sans MS', 40, 'bold')
FONT_LOADING_TEXT = ('Comic Sans MS', 24)
FONT_PROGRESS_TEXT = ('Comic Sans MS', 20)
TEXT_COLOR = '#b057cc'
GREEN_COLOR = (0, 255, 17)

def fetch_artist_image(artist):
    if artist and artist.image_url:
        try:
            response = requests.get(artist.image_url)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        except Exception as e:
            print(f"Error loading artist image: {e}")
    return None

def paste_artist_image(bg_image_pil, mask, artist_image, bbox):
    if artist_image:
        artist_image_resized = artist_image.resize((bbox[2] - bbox[0], bbox[3] - bbox[1]), Image.LANCZOS)
        mask_cropped = mask.crop(bbox)
        final_image = bg_image_pil.copy()
        final_image.paste(artist_image_resized, bbox[:2], mask_cropped)
        return final_image
    return bg_image_pil

def show_loading_page(root, artist_name, search_word, on_back_callback, came_from_saved_artists=False):
    loading_screen = tk.Frame(root, width=750, height=750)
    loading_screen.place(x=0, y=0)

    bg_image_path = os.path.join(os.path.dirname(__file__), 'assets', 'LoadingPage.png')
    bg_image_pil = Image.open(bg_image_path).convert('RGB')

    mask = Image.new('L', bg_image_pil.size, 0)
    bg_array = np.array(bg_image_pil)
    mask_array = np.all(bg_array == GREEN_COLOR, axis=-1).astype(np.uint8) * 255
    mask = Image.fromarray(mask_array, mode='L')
    bbox = mask.getbbox()

    artist = main.genius.search_artist(artist_name, max_songs=1, get_full_info=False)
    artist_image = fetch_artist_image(artist)

    final_image_pil = paste_artist_image(bg_image_pil, mask, artist_image, bbox)

    loading_canvas = tk.Canvas(loading_screen, width=750, height=750)
    loading_canvas.pack(fill="both", expand=True)

    final_image = ImageTk.PhotoImage(final_image_pil)
    loading_canvas.create_image(0, 0, image=final_image, anchor='nw')
    loading_canvas.final_image = final_image

    # place artist name
    artist_x = 750 / 2
    artist_y = 195
    loading_canvas.create_text(
        artist_x, artist_y, anchor='center', text=artist_name,
        font=FONT_ARTIST_NAME, fill=TEXT_COLOR
    )

    # loading text
    loading_text_x, loading_text_y = 180, 430
    loading_message = "Loading"
    loading_text_item = loading_canvas.create_text(
        loading_text_x, loading_text_y, anchor='nw', text=loading_message,
        font=FONT_LOADING_TEXT, fill=TEXT_COLOR
    )

    # blinking dots
    dots = ['   ', '.  ', '.. ', '...']
    dot_index = 0

    # progress text
    progress_text_x, progress_text_y = 340, 440
    progress_text_item = loading_canvas.create_text(
        progress_text_x, progress_text_y, anchor='nw', text="0/0 songs",
        font=FONT_PROGRESS_TEXT, fill=TEXT_COLOR
    )

    # updates the blinking dots in loading text
    def update_dots():
        nonlocal dot_index
        dot_index = (dot_index + 1) % len(dots)
        loading_canvas.itemconfigure(loading_text_item, text=loading_message + dots[dot_index])
        loading_canvas.after(500, update_dots)

    update_dots()

    # thread for loading data
    def loading_thread():
        total_songs = [0]

        def progress_callback(x, y):
            if y == 'unknown':
                progress = f"{x}/?"
            else:
                total_songs[0] = y
                progress = f"{x}/{y} songs"
            loading_canvas.itemconfigure(progress_text_item, text=progress)

        artist_data = main.get_artist_data_with_progress(artist_name, progress_callback)

        if artist_data:
            if search_word.strip():
                # if a word is provided, search it
                result = main.search_word_in_lyrics(search_word, artist_data, artist_name)
                loading_screen.destroy()
                SecondPage.show_second_page(root, result, artist_data, search_word, on_back_callback)
            else:
                # if no word, just load artist
                loading_screen.destroy()
                if came_from_saved_artists:
                    from interface.SavedArtistsPage import show_saved_artists_page
                    show_saved_artists_page(root, on_back_callback)
                else:
                    on_back_callback()
        else:
            # artist not found
            loading_screen.destroy()
            messagebox.showerror("Error", f"Artist '{artist_name}' not found.")
            on_back_callback()

    threading.Thread(target=loading_thread).start()

    # back button
    back_x1, back_y1, back_x2, back_y2 = 0, 630, 200, 790
    back_button_area = loading_canvas.create_rectangle(back_x1, back_y1, back_x2, back_y2, fill="", outline="")
    loading_canvas.tag_bind(back_button_area, "<Button-1>", lambda e: on_back())

    def on_back():
        loading_screen.destroy()
        on_back_callback()
