"""
Usage:
  Universal:
    Shift to change mode

  Select:
    Up and down buttons to change selected track
    Left and right to go backwards/forwards 5 seconds
    Space to play track

  Order:
    Up and down buttons to move selected track up and down
    Left and right to go backwards/forwards 5 seconds
    Space to save order & effects (done automatically when closed)
  
  Edit:
    Left and right to change selected attribute
    Space to edit stat/effect
    Space to go to next entry/text box and confirm input

https://pythonhosted.org/pyglet/programming_guide/controlling_playback.html
"""

import tkinter as tk
import tkinter.ttk as ttk
import random #Testing
import threading
import time
import os
import soundfile
import sys #Testing
import json
import re
#Also import pyglet, sounfile, mutagen.mp3 and eyed3

NAMES_COMMANDS = (
  ("pyglet","python -m pip install pyglet"),
  ("soundfile","python -m pip install soundfile"),
  ("mutagen.mp3", "python -m pip install mutagen"),
  ("eyed3", "python -m pip install python-magic & python -m pip install eyed3"))

PY_PATH = os.__file__[:-10] #Any library will do
PATHS = os.environ["PATH"].split(";")
if not PY_PATH in PATHS:
  os.environ["PATH"] += PY_PATH + ";"
  print("Added python to PATH")
##os.system("python -m pip install python_magic_bin-0.4.14-py2.py3-none-win32.whl")
for i in range(len(NAMES_COMMANDS)):
  try:
    exec("import " + NAMES_COMMANDS[i][0])
  except ImportError:
    os.system("echo {} not found; installing & {} & Pause".format(*NAMES_COMMANDS[i]))
    exec("import " + NAMES_COMMANDS[i][0])

try:
  import sdasdasd
  pyglet.lib.load_library("avbin")
  print("Success: Found AVbin")
except ImportError:
  print(r"""Go to https://www.mediafire.com/file/64vjttya35alh7k/avbin.rar and download the file.

Put avbin.dll into 'C:\Windows\System'.
Note that you cannot install this with pip.
It is required for 'pyglet' to handle compressed files.

Tutorials at:
  https://www.youtube.com/watch?v=dQw4w9WgXcQ
  https://www.youtube.com/watch?v=zZbWX8Q2bsk""")
  input("\nPress any key to continue...")
  sys.exit()

FILE_PATH = os.path.dirname(__file__)
ATTR_NAMES = ("State", "Loop", "Name", "Trim", "Duration","Volume", "Fade Time")
MODES = ("Select", "Order", "Edit")
HL_BG = "#4c4c4c" #Colour for when highlighted
BG = "#212121"
FG = "#afafaf"
CHARS = "4;ra" #Pause, play, cross, tick in Webdings font
KEY_MOVE = {
  "<Right>":(lambda column:(0, 2 if column in (6, 1, 3) else 1)),
  "<Left>":(lambda column:(0, -2 if column in (1, 3 , 5) else -1)),
  "<Up>":(lambda column:(-1, 0)),
  "<Down>":(lambda column:(1, 0))
}

CUTOFF_LENGTH = 35 #How long a name can be before it is cut off and ended with and ellipsis
COLUMN_WIDTHS = (80, 80, 420, 130, 130, 130, 130) #How much space is allocated to each widget
DEFAULT_PARAMS = (False, (0.0, 0.0), 100, 0.0)

def audio_length(file_name):
  try:
    file = soundfile.SoundFile(file_name)
    value = len(file) / file.samplerate
  except:
    try:
      file = mutagen.mp3.MP3(file_name)
      if file is not None:
        value = int(file.info.length)
      else:
        raise
    except:
      try:
        value = int(eyed3.load(file_name).info.time_secs)
      except:
        value = 2013
  return value

def style(size = 0): 
  result = {
    "bg":BG,
    }
  if size != 0:
    result["fg"] = FG
    result["font"] = ["Consolas", size]
  return result

ENTRY_KW = {**style(15), **{"insertbackground":FG, "highlightthickness":3, "highlightbackground":FG, "highlightcolor":FG, "relief":"solid"}}

def replace(dictionary, *kv): #For debugging purporses
  copy = dictionary.copy()
  for k, v in kv:
    copy[k] = v
  return copy

def add_ellipses(string):
  if len(string) >= CUTOFF_LENGTH:
    string = string[:CUTOFF_LENGTH - 3] + "..."
  return string

def grid_config(frame): #Set each column to constant width in accordance with COLUMN_WIDTHS
  frame.grid_rowconfigure(0, weight = 1)
  for i in range(len(COLUMN_WIDTHS)):
    frame.grid_columnconfigure(i, minsize = COLUMN_WIDTHS[i], weight = 1)

def entry_frame_config(frame, columns = 1): #Set each column to constant width
  frame.grid_propagate(True)
  frame.grid_rowconfigure(0, weight = 1)
  for i in range(columns):
    frame.grid_columnconfigure(i, weight = 1)

to_minutes = lambda seconds: "{}:{}".format(*map(two_digit, divmod(round(seconds), 60)))

two_digit = lambda n: ("0" if len(str(n)) == 1 else "") + str(n)

is_float = lambda string: re.match(r"^[0-9]*\.?[0-9]*$", string) is not None and string != "" 

float_ = lambda string: 0.0 if string == "." else float(string)

class App(tk.Tk):
  def __init__(self):
    super().__init__()
    self.configure(**style()) #BG value in dictionary returned only
    self.title("W.I.P")
    self.pack_propagate(True)
    self.resizable(0, 0)
    self.protocol("WM_DELETE_WINDOW", self.end)

    ttk_style = ttk.Style()
    ttk_style.theme_use("default")
    ttk_style.configure("TProgressbar", thickness = 5)

    effects = json.loads(open(FILE_PATH + r"\Config\Effects.json", "r").read())

    os.chdir(FILE_PATH + r"\Tracks")
    track_list = os.listdir()

    for file in track_list: 
      if file not in effects.keys():
        effects[file] = list(DEFAULT_PARAMS) #If new files added, make new set of default stats
    for included in effects.keys():
      if included not in track_list:
        del effects[included] #If files have been removed, remove them
    self.effects = effects
    self.tracks = [Track(track_list[i], audio_length(track_list[i]), i, *effects[track_list[i]]) for i in range(len(track_list))]
    with open(FILE_PATH + r"\Config\Order.txt") as file:
      order = tuple(map(int, file.readlines()))
      self.tracks = [self.tracks[num] for num in order]
    self.selection = (0, 0) #Selected track, selected attribute (edit mode only)
    self.track_selection = (0, 0)
    self.modulo = (len(self.tracks), len(COLUMN_WIDTHS))
    self.end = False
    self.mode = 0
    self.top_frame = tk.Frame(height = 60, width = 1120, **style())
    self.mode_lbl = tk.Label(self.top_frame, **style(20)) #style dictionary kwargs with font size as 20

    self.top_frame.grid_propagate(True)
    for i in range(2):
      self.top_frame.grid_columnconfigure(i, weight = 1, minsize = 100)
    self.top_frame.grid_rowconfigure(0, weight = 1, pad = 50)
    tk.Label(self.top_frame, **style(20), text = "Mode:").grid(row = 0, column = 0, sticky = "E")
    self.mode_lbl.grid(row = 0, column = 1, sticky = "W")
    self.top_frame.grid(row = 0, column = 0, columnspan = 2)

    self.progress_dvar = tk.DoubleVar(self, value = 0)
    self.progress_dvar.trace("w", self.update_bar)
    self.progress_pb = ttk.Progressbar(self.top_frame, style = "TProgressbar", variable = self.progress_dvar, length = 1000, mode = "determinate")
    self.progress_pb.grid(row = 1, column = 0, columnspan = 2)
    self.time_lbl = tk.Label(self.top_frame, **style(20))
    self.time_lbl.grid(row = 2, column = 0, columnspan = 2)
    self.update_bar()

    self.category_frame = tk.Frame(self, height = 30, width = 1100, **style())
    self.category_frame.grid_propagate(False)
    grid_config(self.category_frame)
    for i in range(len(COLUMN_WIDTHS)):
      tk.Label(self.category_frame, text = "<{}>".format(ATTR_NAMES[i]), **style(12)).grid(row = 0, column = i)
    self.category_frame.grid(row = 1, column = 0, sticky = "W")
    
    self.canvas = tk.Canvas(self, **style(), height = 375, width = 1100, highlightthickness = 0)
    self.song_frame = tk.Frame(self.canvas, **style())
    self.scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview, activebackground = BG, troughcolor = BG, **style())
    self.canvas.configure(yscrollcommand = self.scrollbar.set)

    self.canvas.grid(row = 2, column = 0, pady = 10)
    self.canvas.create_window((0, 0), window = self.song_frame, anchor = "n")
    self.scrollbar.grid(row = 2, column = 1, sticky = "NSW")

    self.song_frame.bind("<Configure>", self.on_frame_config)
    self.bind("<Shift_L>", self.shift_pressed)
    self.bind("<space>", self.space_pressed)
    self.bind("<Return>", self.enter_pressed)
    for k, v in KEY_MOVE.items():
      self.bind(k, lambda event, v = v: self.change_selection(v))

    self.track_frames = []
    for i in range(len(self.tracks)):
      self.track_frames.append(TrackFrame(self.song_frame, self.tracks[i]))
      self.track_frames[i].grid(row = i, column = 0)
    self.track_frames[0].highlight = range(len(COLUMN_WIDTHS))
    self.entry_present = False

    self.player = pyglet.media.Player()
    ##for track in self.tracks:
      ##self.player.queue(pyglet.media.load(repr(track)))
    ##self.music_thread = MusicThread(1, self.tracks[0], self)
    ##self.music_thread.start()
    self.play_thread = PlayThread(1, self.tracks[0], self)
    self.play_thread.start()
    


    self.shift_pressed(increment = 0) 
    
    self.mainloop()

  def save(self):
    #Save order
    order = [track.num for track in self.tracks]
    os.chdir(os.path.dirname(__file__) + r"\Config")
    with open(r"Order.txt", "w") as file:
      for n in order:
        file.write(str(n) + "\n")
    
    #Save effects
    effects = {}
    for track in self.tracks:
      effects[str(track)] = track.compile_effects()
    with open("Effects.json", "w") as file:
      json.dump(effects, file)
  
  def update_bar(self, *events):
    self.time_lbl.config(text = "{} / {}".format(to_minutes(self.progress_dvar.get()), to_minutes(len(self.tracks[self.track_selection[0]]))))
  
  def on_frame_config(self, event):
    self.canvas.configure(scrollregion = self.canvas.bbox("all"))
  
  def enter_pressed(self, event):
    track_frame = self.track_frames[self.selection[0]]
    if not self.entry_present or self.mode != 2:
      return
    if self.selection[1] == 3: #If trim selected
      if event.widget == track_frame.stat_entries[0] and track_frame.trace_trim(0): #If correct widget focus and valid input
        track_frame.stat_entries[1].focus_set()
      elif event.widget == track_frame.stat_entries[1] and track_frame.trace_trim(1):
        self.tracks[self.selection[0]].trim = [float_(track_frame.stat_entries[i].get()) for i in range(2)]
        track_frame.update_text()
        track_frame.trim_frame.grid_remove()
        track_frame.grid_widget(3)
        self.entry_present = False
    elif self.selection[1] in (5, 6) and track_frame.trace_trim(2) and track_frame.trace_trim(3): #Volume or fade
      if self.selection[1] == 5:
        self.tracks[self.selection[0]].volume = int(track_frame.stat_entries[2].get())
      else:
        self.tracks[self.selection[0]].fade = float_(track_frame.stat_entries[3].get())
      track_frame.update_text()
      track_frame.grid_widget(self.selection[1])
      self.entry_present = False

  def space_pressed(self, event):
    if self.entry_present:
      return
    if self.mode == 2 and not self.entry_present:
      track_frame = self.track_frames[self.selection[0]]
      if self.selection[1] == 1: #Loop
        track_frame.track.loop = not track_frame.track.loop
      elif self.selection[1] == 3: #Trim
        track_frame.labels[3].grid_remove()
        track_frame.trim_frame.grid(row = 0, column = 3, sticky = "NESW")
        track_frame.stat_entries[0].focus_set()
        self.entry_present = True
      elif self.selection[1] in (5, 6):
        track_frame.labels[self.selection[1]].grid_remove()
        track_frame.unique_frames[self.selection[1] - 5].grid(row = 0, column = self.selection[1], sticky = "NESW")
        track_frame.stat_entries[self.selection[1] - 3].focus_set()
        self.entry_present = True
      self.track_frames[self.selection[0]].update_text()

    if self.mode == 2: #Only play if order or select
      return

    if self.track_selection != self.selection: #New item selected
      print("new")
      self.player.pause()
      self.media_player(self.tracks[self.selection[0]])
      ##self.music_thread.set_track(self.tracks[self.selection[0]])
      for i in range(len(self.track_frames)):
        self.track_frames[i].playing_state_set(False)
      self.progress_dvar.set(0)
    self.track_selection = self.selection[:]
    self.update_bar()
    track_frame_obj = self.track_frames[self.track_selection[0]]
    track_frame_obj.playing_state_set("toggle")
    if track_frame_obj.track.playing:
      self.progress_pb.config(maximum = len(self.tracks[self.track_selection[0]]))
      seek_time = self.tracks[self.selection[0]].trim[0]
      if self.player.time < seek_time: #Only set if it's below (otherwise, resume)
        if seek_time > 0: #This appears to be a bug with pyglet, where it will constantly reset set to 0 if 0
          print("trim[0] = {}".format(seek_time))
          self.player.seek(seek_time)
      self.play_thread.play()
  
  def media_player(self, track_obj):
    self.player.pause()
    del self.player
    self.player = pyglet.media.Player()
    source = pyglet.media.load(repr(track_obj))
    self.player.queue(source)
    print(track_obj.trim)
    self.progress_dvar.set(track_obj.trim[0])
    self.focus_set()
    
  def shift_pressed(self, event = None, increment = 1): #Increment mode
    self.mode = (self.mode + increment) % 3
    self.mode_lbl.config(text = MODES[self.mode])
    self.change_selection(lambda column:(0, 0))

  def change_selection(self, change):
    if self.entry_present:
      return
    change = change(self.selection[1])
    self.selection =  [(self.selection[i] + change[i]) % self.modulo[i] for i in range(2)]

    if self.mode == 1: #If order
      pos = self.selection[0]
      edits = (pos, (pos - change[0]) % len(self.tracks))
      self.tracks[edits[0]], self.tracks[edits[1]] = self.tracks[edits[1]], self.tracks[edits[0]]
      for i in range(2):
        self.track_frames[edits[i]].destroy()
        new = edits[i]
        self.track_frames[edits[i]] = TrackFrame(self.song_frame, self.tracks[new])
        self.track_frames[edits[i]].grid(row = edits[i], column = 0)
    for obj in self.track_frames:
      obj.highlight = []
    track_frame_obj = self.track_frames[self.selection[0]]
    if self.mode == 2: #Edit mode
      track_frame_obj.highlight = [self.selection[1]]
    else: #Select or order mode
      track_frame_obj.highlight = range(len(COLUMN_WIDTHS))
      self.selection[1] = 1

      track = self.tracks[self.selection[0]]
      if change[1] < 0:
        seek = self.player.time - 5
        if seek < track.trim[0]:
          seek = track.trim[0]
        if seek == 0:
          seek = 0.01
      elif change[1] > 0:
        seek = self.player.time + 5
        if seek > len(track) - track.trim[1]:
          seek = len(track) - track.trim[1]
      if change[1] != 0:
        self.player.seek(seek)
        
        ##self.tracks[self.selection[0]]

    bottom = int(self.scrollbar.get()[1] * len(self.track_frames))
    if not self.selection[0] in range(bottom - 5, bottom):
      self.canvas.yview("moveto", (self.selection[0] / len(self.track_frames)))

  def end(self):
    self.player.pause()
    self.save()
    if self.tracks[self.selection[0]].playing:
      print("Running")
      self.end = True
    else:
      print("Not running")
      self.play_thread.parent.destroy()

class PlayThread(threading.Thread):
  def __init__(self, thread_id, track, parent):
    super().__init__(daemon = False)
    self.id = thread_id
    self.track = track
    self.parent = parent
  
  def run(self):
    self.play()

  def play(self):
    self.parent.player.play()
    track_frame_obj = self.parent.track_frames[self.parent.selection[0]]
    self.track = track_frame_obj.track
    self.parent.player.volume = self.track.volume / 100
    condition = lambda:self.parent.progress_dvar.get() < 0.1 + (len(self.track) - self.track.trim[1])
    if not condition():
      ##self.parent.media_player(self.parent.tracks[self.parent.selection[0]])
      print("Progress = {}".format(track_frame_obj.track.trim[0]))
      self.parent.progress_dvar.set(track_frame_obj.track.trim[0])
    while condition():
      if not self.track.playing:
        self.parent.player.pause()
        print("Pausing")
        return
      if self.parent.end:
        print("Ending")
        self.parent.destroy()
        return
      self.parent.update()
      ##self.parent.progress_dvar.set(self.parent.progress_dvar.get() + 0.1) #Automagically updates bar
      ##print(self.parent.player.time)
      self.parent.progress_dvar.set(self.parent.player.time)
    #Run below if ended by getting to the end
    print("End")
    self.parent.media_player(self.parent.tracks[self.parent.selection[0]])
    if self.track.loop:
      self.play()
    else:
      track_frame_obj.playing_state_set(False)

class MusicThread(threading.Thread):
  def __init__(self, thread_id, track, parent):
    super().__init__(daemon = False)
    self.thread_id = thread_id
    self.track = track
    self.parent = parent
  
  def set_track(self, track):
    self.pause()
    self.track = track

  def run(self):
    self.play()
  
  def play(self):
    self.parent.player.play()
  
  def pause(self):
    self.parent.player.pause()

class Track:
  def __init__(self, name, track_length, num, loop = False, trim_values = (0, 0), volume_modifier = 100, fade_time = 0):
    """Note that 'num' is used so that the order can easily be kept track of,
    meaning that saving is simply a matter of writing the 'num' of each object
    to a text file."""
    self.name = name
    self.length = track_length
    self.num = num
    
    self.loop = loop
    self.trim = trim_values[:]
    self.volume = volume_modifier
    self.fade = fade_time
    
    self.playing = False

  def __len__(self):
    """Objects of this class are NOT iterable. 'len' simply gets the length,
    not the number of items stored in a certain variable as not such variable
    exists in this class."""
    return self.length

  def __repr__(self):
    """Simple string representation"""
    return self.name
##    return "(Name: '{}', Length: {}, Trim: {}, Volume Modifier: {}, Fade Time: {}, Loop: {}, Playing: {})".format(self.name, to_minutes(self.length), self.trim, self.volume, self.fade, self.loop, self.playing)

  def compile_effects(self):
    return (self.loop, self.trim, self.volume, self.fade)

class TrackFrame(tk.Frame):
  def __init__(self, parent, track):
    super().__init__(parent, width = 1100, height = 75, bd = 0)
    self.grid_propagate(False)

    self.track = track
    self.labels = []

    self.trim_frame = tk.Frame(self, **style())
    ##
    entry_frame_config(self.trim_frame, 2)
    ##
    
    variables = self.track.trim + [self.track.volume, self.track.fade]
    self.stat_entries = []
    self.stat_svars = [tk.StringVar(value = variables[i]) for i in range(4)]
    self.unique_frames = [tk.Frame(self, **style()) for i in range(2)]

    #Loop below: 4 string variables for 4 entries (2 for trim, 1 for volume, 1 for fade)
    for i in range(4): #Terary operators: 0 or 1 for trim, 2 or 3 for independent stats
      self.stat_entries.append(tk.Entry((self.trim_frame if i <= 1 else self.unique_frames[i - 2]), textvariable = self.stat_svars[i], **ENTRY_KW, width = (4 if i <= 1 else 6)))
      self.stat_entries[i].grid(row = 0, column = (i if i <= 1 else 0))
      if i >= 2:
        entry_frame_config(self.unique_frames[i -2], 1)
      self.stat_svars[i].trace("w", lambda *args, i = i: self.trace_trim(i))

    self.update_text()
    grid_config(self)
    for i in range(len(self.text)):
      style_dict = style(14)
      if i in (0, 1):
        style_dict["font"][0] = "Webdings"
      self.labels.append(tk.Label(self, **style_dict, text = self.text[i]))
      self.grid_widget(i)
    self._highlight = []

  def __repr__(self):
    return "F " + repr(self.track)
  
  def grid_widget(self, n):
    self.labels[n].grid(row = 0, column = n, sticky = "NESW")

  def update_text(self):
    """Set the value of self.text to what it should be (based on the current
    state of self.track (if that is updated, this object is updated with this
    method)"""
    self.text = (CHARS[0], CHARS[self.track.loop + 2], "'{}'".format(add_ellipses(self.track.name)), "({}s, {}s)".format(*self.track.trim), to_minutes(len(self.track)), "{}%".format(self.track.volume), "{}s".format(self.track.fade))
    for i in range(len(self.labels)):
      self.labels[i].config(text = self.text[i])
  
  def trace_trim(self, n):
    """Convert the to the stat_entries[n] to the correct colour - normal if
    valid and red if invalid. Note that '.' is accepted, being converted by
    range_ to 0.0. Other examples: 5. and .5 are both allowed. Negative numbers
    are not allowed and '+' is not either. Standard form/exponents to the power
    if 10, such as '5e2' or `5E2` are ignored as they will not be needed in
    this case."""
    self.stat_svars[n].set(self.stat_svars[n].get().replace(" ", ""))
    entry = self.stat_entries[n]
    value = self.stat_svars[n].get()
    if n == 2:
      valid = re.match(r"^\d+$", value) is not None and int(value) >= 0 and int(value) <= 100
    elif n == 3:
      valid = is_float(value) and float_(value) <= (len(self.track) - (self.track.trim[0] + self.track.trim[1]))
    else:
      valid = is_float(value)
    if valid:
      entry.config(fg = style(1)["fg"])
      return True
    entry.config(fg = "red")
    return False
  
  @property
  def highlight(self):
    return self._highlight
  
  @highlight.setter
  def highlight(self, value):
    self._highlight = value
    for i in range(len(self.labels)):
      self.labels[i].config(bg = (HL_BG if i in self.highlight else style()["bg"]))
  
  def playing_state_set(self, value):
    if value == "toggle":
      self.track.playing = not self.track.playing
    else:
      self.track.playing = value #Toggle
    self.labels[0].config(text = CHARS[self.track.playing])

if __name__ == "__main__":
  app = App()
  ##self = app
