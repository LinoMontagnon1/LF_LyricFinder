import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import requests
import io
import sys
import numpy as np
import lyricsgenius
import json
import config

# constants for styling
BG_COLOR = '#ffd75d'  # background color for text box
HIGHLIGHT_COLOR = '#b057cc'  # highlight and title color
FONT_TITLE = ('Comic Sans MS', 15, 'bold')
FONT_LYRICS = ('Comic Sans MS', 13)
FONT_SEARCHED_WORD = ('Comic Sans MS', 26, 'bold')

# genius key
genius = lyricsgenius.Genius(config.API_KEY)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# gets or fetches the artist image URL if missing
def get_or_fetch_artist_image_url(artist_data):
    artist_image_url = artist_data.get('artist', {}).get('image_url', None)
    if not artist_image_url:
        artist_name = artist_data.get('artist', {}).get('name', None)
        if artist_name:
            artist = genius.search_artist(artist_name, max_songs=0, get_full_info=False)
            if artist and artist.image_url:
                artist_image_url = artist.image_url
                artist_data['artist']['image_url'] = artist_image_url
                data_file = os.path.join('data', f"{artist_name}_lyrics.json")
                with open(data_file, 'w', encoding='utf-8') as file:
                    json.dump(artist_data, file, ensure_ascii=False)
    return artist_image_url

# fetches the artist image and pastes it onto the background image
def fetch_and_paste_artist_image(bg_image_pil, mask, bbox, artist_image_url):
    green_composited = bg_image_pil.copy()
    if artist_image_url:
        try:
            response = requests.get(artist_image_url)
            response.raise_for_status()
            image_data = response.content
            artist_image = Image.open(io.BytesIO(image_data))
            artist_image_resized = artist_image.resize((bbox[2] - bbox[0], bbox[3] - bbox[1]), Image.LANCZOS)
            mask_cropped = mask.crop(bbox)
            green_composited.paste(artist_image_resized, bbox[:2], mask_cropped)
            return green_composited
        except Exception:
            return bg_image_pil
    return bg_image_pil

def configure_scrollbar(canvas, text_widget, x1, y1, width, height):
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Custom.Vertical.TScrollbar",
                    gripcount=0, background=HIGHLIGHT_COLOR,
                    troughcolor=BG_COLOR, bordercolor=BG_COLOR,
                    arrowcolor=BG_COLOR, relief='flat', borderwidth=0)
    style.map("Custom.Vertical.TScrollbar",
              background=[('active', HIGHLIGHT_COLOR), ('!active', HIGHLIGHT_COLOR)],
              lightcolor=[('active', HIGHLIGHT_COLOR), ('!active', HIGHLIGHT_COLOR)],
              darkcolor=[('active', HIGHLIGHT_COLOR), ('!active', HIGHLIGHT_COLOR)])
    scrollbar = ttk.Scrollbar(canvas, orient="vertical", command=text_widget.yview, style="Custom.Vertical.TScrollbar")
    scrollbar.place(x=x1+width, y=y1, height=height)
    text_widget.configure(yscrollcommand=scrollbar.set)

# bold highlight 
def highlight_word_in_text(text_widget, search_word):
    start_pos = "1.0"
    while True:
        start_pos = text_widget.search(search_word, start_pos, nocase=True, stopindex=tk.END)
        if not start_pos:
            break
        end_pos = f"{start_pos}+{len(search_word)}c"
        text_widget.tag_add('highlight', start_pos, end_pos)
        start_pos = end_pos

# displays the second page with search results
def show_second_page(root, result, artist_data, search_word, on_back_callback):

    second_screen = tk.Frame(root, width=750, height=750)
    second_screen.place(x=0, y=0)

    # loads background and finds green mask bbox
    bg_image_path = os.path.join(os.path.dirname(__file__), 'assets', 'SecondPage.png')
    bg_image_pil = Image.open(bg_image_path).convert('RGB')
    green_color = (0, 255, 17)
    bg_array = np.array(bg_image_pil)
    mask_array = np.all(bg_array == green_color, axis=-1).astype(np.uint8) * 255
    mask = Image.fromarray(mask_array, mode='L')
    bbox = mask.getbbox()

    artist_image_url = get_or_fetch_artist_image_url(artist_data)
    composited_image = fetch_and_paste_artist_image(bg_image_pil, mask, bbox, artist_image_url)

    final_image = ImageTk.PhotoImage(composited_image)
    second_canvas = tk.Canvas(second_screen, width=750, height=750)
    second_canvas.pack(fill="both", expand=True)
    second_canvas.create_image(0, 0, image=final_image, anchor='nw')
    second_canvas.final_image = final_image

    # places the searched word
    word_x, word_y = 200, 203
    second_canvas.create_text(word_x, word_y, anchor='nw', text=f"{search_word}", font=FONT_SEARCHED_WORD, fill=HIGHLIGHT_COLOR)

    # places the lyrics text box
    x1, y1, x2, y2 = 70, 280, 680, 640
    width = x2 - x1
    height = y2 - y1
    result_text = tk.Text(second_canvas, wrap=tk.WORD, bg=BG_COLOR, bd=0, highlightthickness=0)
    result_text.place(x=x1, y=y1, width=width, height=height)

    configure_scrollbar(second_canvas, result_text, x1, y1, width, height)

    result_text.tag_configure('title', font=FONT_TITLE, foreground=HIGHLIGHT_COLOR)
    result_text.tag_configure('lyrics', font=FONT_LYRICS)
    result_text.tag_configure('highlight', font=FONT_TITLE)
    result_text.configure(state='normal')

    # inserts titles and lyrics lines
    for title, lines in result:
        result_text.insert(tk.END, f"\n{title}\n", 'title')
        if lines:
            for line in lines:
                result_text.insert(tk.END, f"{line}\n", 'lyrics')

    highlight_word_in_text(result_text, search_word)

    result_text.configure(state='disabled')

    # places a back button
    back_x1, back_y1, back_x2, back_y2 = 280, 670, 475, 740
    back_button_area = second_canvas.create_rectangle(back_x1, back_y1, back_x2, back_y2, fill="", outline="")
    second_canvas.tag_bind(back_button_area, "<Button-1>", lambda e: on_back())

    def on_back():
        # calls callback and destroys second screen
        second_screen.destroy()
        on_back_callback()
