import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import threading
import webbrowser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main
from tkinter import messagebox
from interface import SecondPage, LoadingPage, SavedArtistsPage

fields = ['artist', 'word']  # fields for text inputs

class State:
    def __init__(self):
        self.texts = {'artist': '', 'word': ''}
        self.active_entry = None  # tracks which entry field is active
        self.cursor_visible = True  # controls cursor blink
        self.selection_all = {'artist': False, 'word': False}

state = State()

# toggles cursor visibility and schedules another toggle
def toggle_cursor():
    state.cursor_visible = not state.cursor_visible
    update_cursor()
    root.after(500, toggle_cursor)

# updates the cursor line visibility based on the active field
def update_cursor():
    for entry in fields:
        cursor_item = cursor_items[entry]
        if state.active_entry == entry and state.cursor_visible:
            canvas.itemconfigure(cursor_item, state='normal')
        else:
            canvas.itemconfigure(cursor_item, state='hidden')

def draw_text():
    for entry in fields:
        text_item = text_items[entry]
        cursor_item = cursor_items[entry]
        canvas.itemconfigure(text_item, text=state.texts[entry])
        if state.active_entry == entry:
            bbox = canvas.bbox(text_item)
            x_offset = bbox[2] if bbox else entry_coords[entry][0] + 5
            y1 = entry_coords[entry][1] + 17
            y2 = entry_coords[entry][1] + 47
            canvas.coords(cursor_item, x_offset, y1, x_offset, y2)
    update_cursor()

def handle_backspace():
    if state.selection_all[state.active_entry]:
        state.texts[state.active_entry] = ''
        state.selection_all[state.active_entry] = False
    else:
        state.texts[state.active_entry] = state.texts[state.active_entry][:-1]

# control + A
def handle_selection_all():
    state.selection_all[state.active_entry] = True

def handle_character_entry(char):
    if state.selection_all[state.active_entry]:
        state.texts[state.active_entry] = char
        state.selection_all[state.active_entry] = False
    else:
        state.texts[state.active_entry] += char

def on_key_press(event):
    if not state.active_entry:
        return
    ctrl_pressed = (event.state & 0x4) != 0

    if ctrl_pressed and event.keysym.lower() == 'a':
        handle_selection_all()
    elif event.keysym == "BackSpace":
        handle_backspace()
    elif event.keysym == "Return":
        on_search()
        return "break"
    elif len(event.char) == 1:
        handle_character_entry(event.char)
    draw_text()
    return "break"

# tab key func
def on_tab_press(event):
    if not state.active_entry:
        state.active_entry = 'artist'
    else:
        state.active_entry = 'word' if state.active_entry == 'artist' else 'artist'
    state.selection_all[state.active_entry] = False
    draw_text()
    return "break"

def focus_entry(entry):
    state.active_entry = entry
    state.cursor_visible = True
    state.selection_all[state.active_entry] = False
    draw_text()

def show_loading_image():
    global loading_image, loading_label
    image_path = os.path.join(os.path.dirname(__file__), 'assets', 'LoadingIcon1.png')
    if os.path.exists(image_path):
        image = Image.open(image_path)
        loading_image = ImageTk.PhotoImage(image)
        loading_label = tk.Label(root, image=loading_image, bg='white', borderwidth=0, highlightthickness=0)
        loading_label.place(x=290, y=540)
    else:
        print(f"Loading image not found at {image_path}")

def hide_loading_image():
    global loading_label
    if loading_label:
        loading_label.destroy()
        loading_label = None

# initiates the search process
def on_search(event=None):
    artist_name = state.texts['artist'].strip()
    search_word = state.texts['word'].strip()
    if not artist_name or not search_word:
        messagebox.showwarning("Error", "Please enter both artist name and word.")
        return
    show_loading_image()

    # threaded function to get data and show results
    def do_search(): 
        data_file = os.path.join(main.data_dir, f"{artist_name}_lyrics.json")
        if os.path.exists(data_file):
            artist_data = main.get_artist_data_with_progress(artist_name)
            if artist_data:
                result = main.search_word_in_lyrics(search_word, artist_data, artist_name)
            else:
                result = [(f"Artist '{artist_name}' not found.", [])]
            root.after(0, lambda: [hide_loading_image(), hide_first_screen(), SecondPage.show_second_page(root, result, artist_data, search_word, on_back)])
        else:
            root.after(0, lambda: [hide_loading_image(), hide_first_screen(), LoadingPage.show_loading_page(root, artist_name, search_word, on_back)])

    threading.Thread(target=do_search).start()

def hide_first_screen():
    for item in [search_area, saved_artists_area, history_logs_area, github_area, website_area]:
        canvas.itemconfigure(item, state='hidden')
    for item in entry_areas.values():
        canvas.itemconfigure(item, state='hidden')
    for item in text_items.values():
        canvas.itemconfigure(item, state='hidden')
    for item in cursor_items.values():
        canvas.itemconfigure(item, state='hidden')
    if loading_label:
        loading_label.lift()

# back to first page func
def show_first_screen():
    for item in [search_area, saved_artists_area, history_logs_area, github_area, website_area]:
        canvas.itemconfigure(item, state='normal')
    for item in entry_areas.values():
        canvas.itemconfigure(item, state='normal')
    for item in text_items.values():
        canvas.itemconfigure(item, state='normal')
    draw_text()

# back func
def on_back():
    state.texts = {'artist': '', 'word': ''}
    state.active_entry = None
    state.selection_all['artist'] = False
    state.selection_all['word'] = False
    hide_loading_image()
    draw_text()
    show_first_screen()

def open_github(event=None):
    webbrowser.open_new("https://github.com/LinoMontagnon1")

# my own website in the future (to do)
def open_website(event=None):
    webbrowser.open_new("https://genius.com/")

def open_saved_artists():
    show_loading_image()
    root.after(1000, lambda: [hide_loading_image(), hide_first_screen(), SavedArtistsPage.show_saved_artists_page(root, on_back)])

root = tk.Tk()  # main window
root.title("LF Lyrics Finder")
root.geometry("750x750")
root.resizable(False, False)

icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'Icon64bits.ico')
root.iconbitmap(icon_path)

asset_path = os.path.join(os.path.dirname(__file__), 'assets', 'FirstPage.png')
bg_image = Image.open(asset_path)
bg_photo = ImageTk.PhotoImage(bg_image)

canvas = tk.Canvas(root, width=750, height=750, takefocus=True)
canvas.pack(fill="both", expand=True)
canvas.create_image(0, 0, image=bg_photo, anchor="nw")
canvas.image = bg_photo

entry_coords = {
    'artist': (210, 240, 610, 290),
    'word': (200, 378, 610, 428)
}

entry_areas = {}
text_items = {}
cursor_items = {}
text_font = ("Comic Sans MS", 26)

for entry in fields:
    x1, y1, x2, y2 = entry_coords[entry]
    entry_area = canvas.create_rectangle(x1, y1, x2, y2, fill="", outline="")
    canvas.tag_bind(entry_area, "<Button-1>", lambda e, ent=entry: focus_entry(ent))
    entry_areas[entry] = entry_area

    text_item = canvas.create_text(x1+5, y1+5, anchor="nw", text="", font=text_font, fill="black")
    text_items[entry] = text_item

    cursor_item = canvas.create_line(x1+5, y1+5, x1+5, y1+35, fill="black", width=2)
    canvas.itemconfigure(cursor_item, state='hidden')
    cursor_items[entry] = cursor_item

# bind keys to the canvas
canvas.bind("<Key>", on_key_press)
canvas.bind("<Tab>", on_tab_press)

canvas.focus_set()
toggle_cursor()

search_area = canvas.create_rectangle(260, 450, 550, 550, fill="", outline="")
canvas.tag_bind(search_area, "<Button-1>", on_search)

saved_artists_area = canvas.create_rectangle(0, 590, 200, 790, fill="", outline="")
canvas.tag_bind(saved_artists_area, "<Button-1>", lambda e: open_saved_artists())

history_logs_area = canvas.create_rectangle(580, 590, 830, 790, fill="", outline="")
canvas.tag_bind(history_logs_area, "<Button-1>", lambda e: messagebox.showinfo("Info", "Not implemented yet.")) #to do

github_area = canvas.create_rectangle(300, 690, 380, 750, fill="", outline="")
canvas.tag_bind(github_area, "<Button-1>", open_github)

website_area = canvas.create_rectangle(385, 690, 455, 750, fill="", outline="")
canvas.tag_bind(website_area, "<Button-1>", open_website)

if __name__ == '__main__':
    root.mainloop()
