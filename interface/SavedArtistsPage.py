import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import json
import numpy as np
import requests
import io
from tkinter import messagebox
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main
from interface import LoadingPage

# base directories and constants
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

BG_COLOR = '#ffd75d'
HIGHLIGHT_COLOR = '#b057cc'
FONT_MAIN = ('Comic Sans MS', 20, 'bold')
FONT_SUB = ('Comic Sans MS', 16)
FONT_TITLE = ('Comic Sans MS', 20, 'bold')
MOUSEWHEEL_FACTOR = -1

def load_image(filename):
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(path):
        pil_img = Image.open(path)
        return ImageTk.PhotoImage(pil_img)
    return None

def show_saved_artists_page(root, on_back_callback):
    saved_artists_screen = tk.Frame(root, width=750, height=750)
    saved_artists_screen.place(x=0, y=0)

    # load main background image
    bg_image_path = os.path.join(ASSETS_DIR, 'SavedArtistsPage.png')
    bg_image_pil = Image.open(bg_image_path).convert('RGB')
    bg_photo = ImageTk.PhotoImage(bg_image_pil)

    main_canvas = tk.Canvas(saved_artists_screen, width=750, height=750, highlightthickness=0)
    main_canvas.place(x=0, y=0)
    main_canvas.create_image(0, 0, image=bg_photo, anchor='nw')
    main_canvas.bg_photo = bg_photo

    artist_files = [f for f in os.listdir(DATA_DIR) if f.endswith('_lyrics.json')]

    if not artist_files:
        # no saved artists found
        messagebox.showinfo("Information", "No saved artists found.")
        saved_artists_screen.destroy()
        on_back_callback()
        return

    # scrollable area for artists
    artists_area_frame = tk.Frame(saved_artists_screen, width=500, height=500)
    artists_area_frame.place(x=0, y=210)
    artists_canvas = tk.Canvas(artists_area_frame, width=500, height=500, bg="white", highlightthickness=0)
    artists_canvas.pack(side='left', fill='both', expand=True)

    inner_frame = tk.Frame(artists_canvas)
    artists_canvas.create_window((0,0), window=inner_frame, anchor='nw')

    # adjust scroll region when frame size changes
    def on_frame_configure(event):
        artists_canvas.configure(scrollregion=artists_canvas.bbox('all'))
    inner_frame.bind('<Configure>', on_frame_configure)

    # mouse wheel scrolling
    def _on_mousewheel(event):
        artists_canvas.yview_scroll(int(MOUSEWHEEL_FACTOR*(event.delta/120)), "units")
    artists_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # extract block area for artist display
    artist_block_coords = (0, 230, 500, 350)
    artist_block_image = bg_image_pil.crop(artist_block_coords)
    green_color = (0, 255, 17)
    block_array = np.array(artist_block_image)
    mask_array = np.all(block_array == green_color, axis=-1).astype(np.uint8)*255
    mask = Image.fromarray(mask_array, mode='L')
    bbox = mask.getbbox()
    block_width, block_height = artist_block_image.size

    # load images
    loading_img = load_image('LoadingIcon1.png')
    update_pil_path = os.path.join(ASSETS_DIR, 'UpdateIcon.png')
    update_pil = Image.open(update_pil_path) if os.path.exists(update_pil_path) else None
    update_icon_img = ImageTk.PhotoImage(update_pil) if update_pil else None

    # updates artist data
    def update_artist(artist_name, artist_canvas_item):
        if loading_img:
            loading_label = tk.Label(
                saved_artists_screen,
                image=loading_img,
                bg=BG_COLOR,
                borderwidth=0,
                highlightthickness=0
            )
            loading_label.place(x=570, y=400)
            root.update()

        progress_label.config(text=f"Updating {artist_name}...")

        def progress_callback(current, total):
            progress_text = f"Updating {artist_name}: {current}/{total} songs"
            progress_label.config(text=progress_text)
            root.update()

        def do_update():
            main.get_artist_data_with_progress(artist_name, progress_callback=progress_callback, force_update=True)
            root.after(0, lambda: [
                loading_label.destroy(),
                progress_label.config(text=""),
                saved_artists_screen.destroy(),
                show_saved_artists_page(root, on_back_callback)
            ])

        import threading
        threading.Thread(target=do_update).start()



    # called when an artist is clicked
    def on_artist_click(e, an, aci):
        show_update_icon(an, aci)

    # shows the update icon for the artist
    def show_update_icon(artist_name, artist_canvas_item):
        if update_icon_img and update_pil:
            width, height = update_pil.size
            new_width = int(width * 0.7) # 70%
            new_height = int(height * 0.7)
            update_pil_resized = update_pil.resize((new_width, new_height), Image.LANCZOS)
            update_icon_img_resized = ImageTk.PhotoImage(update_pil_resized)

            icon_x = bbox[2] + 10
            icon_y = bbox[1] - 10
            icon_item = artist_canvas_item.create_image(icon_x, icon_y, image=update_icon_img_resized, anchor='nw')
            artist_canvas_item.lift(icon_item)

            def on_update_click(e):
                update_artist(artist_name, artist_canvas_item)
            artist_canvas_item.tag_bind(icon_item, "<Button-1>", on_update_click)

            # keep a reference to avoid garbage collection
            artist_canvas_item.update_icon_img_resized = update_icon_img_resized
        else:
            print("Update icon not found. Check if 'UpdateIcon.png' exists in the assets folder.")

    for artist_file in artist_files:
        data_file = os.path.join(DATA_DIR, artist_file)
        with open(data_file, 'r', encoding='utf-8') as file:
            artist_data = json.load(file)

        artist_name = artist_data.get('artist', {}).get('name', 'Name not available')
        artist_image_url = artist_data.get('artist', {}).get('image_url', None)
        total_songs = len(artist_data.get('songs', []))

        block_image = artist_block_image.copy()

        if artist_image_url:
            # load artist image
            try:
                response = requests.get(artist_image_url)
                response.raise_for_status()
                image_data = response.content
                artist_image = Image.open(io.BytesIO(image_data))
                artist_image_resized = artist_image.resize((bbox[2]-bbox[0], bbox[3]-bbox[1]), Image.LANCZOS)
                mask_cropped = mask.crop(bbox)
                block_image.paste(artist_image_resized, bbox[:2], mask_cropped)
            except Exception as e:
                print(f"Error loading artist image {artist_name}: {e}")

        block_photo = ImageTk.PhotoImage(block_image)
        artist_frame = tk.Frame(inner_frame, width=block_width, height=block_height)
        artist_frame.pack()
        artist_frame.pack_propagate(0)

        artist_canvas_item = tk.Canvas(artist_frame, width=block_width, height=block_height, highlightthickness=0)
        artist_canvas_item.pack(fill='both', expand=True)

        image_id = artist_canvas_item.create_image(0, 0, image=block_photo, anchor='nw')
        artist_canvas_item.block_photo = block_photo

        # bind click on the artist image
        artist_canvas_item.tag_bind(image_id, "<Button-1>", lambda e, an=artist_name, aci=artist_canvas_item: on_artist_click(e, an, aci))

        name_x, name_y = bbox[2] + 20, bbox[1]
        artist_canvas_item.create_text(
            name_x, name_y, anchor='nw', text=artist_name,
            font=FONT_TITLE, fill=HIGHLIGHT_COLOR
        )

        songs_text = f"total songs: {total_songs}"
        artist_canvas_item.create_text(
            name_x, name_y + 40, anchor='nw', text=songs_text,
            font=FONT_SUB, fill=HIGHLIGHT_COLOR
        )

    back_button_area = main_canvas.create_rectangle(580, 650, 750, 750, fill="", outline="")
    main_canvas.tag_bind(back_button_area, "<Button-1>", lambda e: on_back(saved_artists_screen, on_back_callback))

    save_new_artist_button_area = main_canvas.create_rectangle(570, 555, 750, 650, fill="", outline="")
    main_canvas.tag_bind(save_new_artist_button_area, "<Button-1>", lambda e: show_new_artist_entry())

    progress_label = tk.Label(saved_artists_screen, text="", font=FONT_SUB, bg=BG_COLOR, fg=HIGHLIGHT_COLOR)
    progress_label.place(x=200, y=710)


    entry_x = 560
    entry_y = 530
    entry_width = 170
    entry_height = 30

    new_artist_entry = tk.Entry(saved_artists_screen, 
                                font=FONT_MAIN, 
                                fg=HIGHLIGHT_COLOR, 
                                bd=0, 
                                highlightthickness=0, 
                                bg=BG_COLOR)
    new_artist_entry.place_forget()

    underline = main_canvas.create_line(
        entry_x, entry_y + entry_height, 
        entry_x + entry_width, entry_y + entry_height, 
        fill=HIGHLIGHT_COLOR, width=2, 
        state='hidden'
    )

    # new artist entry box
    def show_new_artist_entry():
        new_artist_entry.place(x=entry_x, y=entry_y, width=entry_width, height=entry_height)
        new_artist_entry.focus_set()
        new_artist_entry.bind("<Return>", on_new_artist_enter)
        main_canvas.itemconfigure(underline, state='normal')

    # press enter after writing artist name
    def on_new_artist_enter(event):
        new_artist_name = new_artist_entry.get().strip()
        if not new_artist_name:
            return
        new_artist_entry.place_forget()
        new_artist_entry.unbind("<Return>")
        main_canvas.itemconfigure(underline, state='hidden')

        if loading_img:
            loading_label = tk.Label(saved_artists_screen, image=loading_img, bg=BG_COLOR, borderwidth=0, highlightthickness=0)
            loading_label.place(x=entry_x + 20, y=entry_y - 100)
            root.update()

        # returns to the saved artists page after loading
        def on_loading_back():
            saved_artists_screen.destroy()
            show_saved_artists_page(root, on_back_callback)

        LoadingPage.show_loading_page(root, new_artist_name, "", on_loading_back, came_from_saved_artists=True)

    def on_back(screen, callback):
        screen.destroy()
        callback()
