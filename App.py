"""
Bugs to fix:
  Play button resets when changing mode (but doesn't affect functionality)
    Ensure that play button is not reset when doing this (explicitly exlude it)
  .wav files inconsistent in playability
    Incorrect file path (FileNotFoundError, os.chdir(FILE_PATH + r"\Tracks"))?
    AVbin not consistenly installed on each program run?
  Doesn't always save order when closing
    A faulty condition - not saving in certain cases to avoid errors?


TROUBLESHOOTING:
  Are you using Python 32-bit?
  Syntax errors: Use Python 3.5 or above
  Error for 'libmagic not found'? python -m pip install python-magic-bin==0.4.14
  Python not recognised: import a library and print it to find out the Python directory and add it to PATH variables
  Error involving 'pyglet' and 'AVbin'?

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
    Enter to go to next entry/text box and confirm input

https://pythonhosted.org/pyglet/programming_guide/controlling_playback.html
"""

import tkinter as tk
import tkinter.ttk as ttk
import random #Testing purposes
import threading
import time
import os
import sys
import json
import re
#Also import pyglet, sounfile, mutagen.mp3 and eyed3

NAMES_COMMANDS = (
  ("pyglet","python -m pip install pyglet"), #Note that '-m' means module
  ("soundfile","python -m pip install soundfile"),
  ("mutagen.mp3", "python -m pip install mutagen"),
  ("eyed3", "python -m pip install python-magic-bin==0.4.14 & python -m pip install eyed3"), #libmagic is a dependency of eyed3
  ("soundfile", "python -m pip install soundfile"))

PY_PATH = os.__file__[:-10] #Any library will do
PATHS = os.environ["PATH"].split(";") #PATH is separated by semicolons - produces a list containing each path
if not PY_PATH in PATHS: #Must be in paths to be used on the command line
  os.environ["PATH"] += PY_PATH + ";" #Add Python to path (temporarily)
  print("Added python to PATH")
##os.system("python -m pip install python_magic_bin-0.4.14-py2.py3-none-win32.whl")
for i in range(len(NAMES_COMMANDS)):
  try:
    exec("import " + NAMES_COMMANDS[i][0]) #Import the first string in the selected tuple
  except ImportError:
    os.system("echo {} not found; installing & {} & Pause".format(*NAMES_COMMANDS[i])) #Install it on the command line
    try: #Not guarunteed to wirj
      exec("import " + NAMES_COMMANDS[i][0])
    except: #Note that errors raised by os.system are not caught (hence the exception that encompasses all)
      print("ERROR: Could not import library '{}' (see top of code for troubleshooting)".format(NAMES_COMMANDS[i][0]))

try:
  pyglet.lib.load_library("avbin") #Finds AVbin without having to open a compressed audio file
  print("Success: Found AVbin")
except ImportError:
  print(r"""Go to https://www.mediafire.com/file/64vjttya35alh7k/avbin.rar and download the file.

Put avbin.dll into 'C:\Windows\System'.
Note that you cannot install this with pip.
It is required for 'pyglet' to handle compressed files.

Tutorials at:
  https://www.youtube.com/watch?v=dQw4w9WgXcQ
  https://www.youtube.com/watch?v=zZbWX8Q2bsk""")
  input("\nPress any key to continue...") #Stops the command line from closing immediately (useless in IDE's, though)
  sys.exit() #Stops the program without having to close the shell (for IDLE)

FILE_PATH = os.path.dirname(__file__) #Location of this file
ATTR_NAMES = ("State", "Loop", "Name", "Trim", "Duration","Volume", "Fade Time") #Names of each attribute
MODES = ("Select", "Order", "Edit") #Names of modes (note that these can be changed without having to change any other code)
HL_BG = "#4c4c4c" #Colour for when highlighted
BG = "#212121" #Colour of background
FG = "#afafaf" #Colour of foreground (text)
CHARS = "4;ra" #Pause, play, cross, tick in Webdings font (these characters would have to be emojis otherwise)
KEY_MOVE = {
  "<Right>":(lambda column:(0, 2 if column in (6, 1, 3) else 1)), #Skips out certain columns that can't be edited
  "<Left>":(lambda column:(0, -2 if column in (1, 3 , 5) else -1)), #Subtract one extra if in certain columes
  "<Up>":(lambda column:(-1, 0)), #No exceptions to how far down it jumps
  "<Down>":(lambda column:(1, 0)) #Note that index 0 is row and index 1 is column
}

CUTOFF_LENGTH = 35 #How long a name can be before it is cut off and ended with and ellipsis
COLUMN_WIDTHS = (80, 80, 420, 130, 130, 130, 130) #How much space is allocated to each widget
DEFAULT_PARAMS = (False, (0.0, 0.0), 100, 0.0) #When Config.json is missing the file (i.e. new file added), use these arguments

def audio_length(file_name):
  try:
    file = soundfile.SoundFile(file_name) #If metadata contains number of samples (len) and sample rate
    value = len(file) / file.samplerate #length = samples / sample rate
  except:
    try:
      file = mutagen.mp3.MP3(file_name) #If sample rate and/or number of samples not available
      if file is not None: #May not raise error. None means that no data was found
        value = int(file.info.length)
      else:
        raise
    except:
      try:
        value = int(eyed3.load(file_name).info.time_secs) #For wav files with ambiguous metadata
      except:
        raise Warning("Could not find the length of " + file_name)
        value = 6039 #99:99 (Basically, I didn't want to raise any exceptions)
  return value

def style(size = 0): #Call style() to not have anything text-related (to not cause errors with widgets that don't support text)
  result = {
    "bg":BG,
    }
  if size != 0:
    result["fg"] = FG
    result["font"] = ["Consolas", size] #This needs to be mutable so that the font can be changed to Webdings for the special characters
  return result

ENTRY_KW = {**style(15), **{"insertbackground":FG, "highlightthickness":3, "highlightbackground":FG, "highlightcolor":FG, "relief":"solid"}}
#Add **ENTRY_KW to tk.Entry widget to use this styling

def replace(dictionary, *kv): #For debugging purporses. Call as: replace({1:2, 3:10, 5:7}, (5, 6), (3, 4))
  copy = dictionary.copy()
  for k, v in kv:
    copy[k] = v
  return copy

def add_ellipses(string): #If it exceeds the cutoff length, cut it to that length and replace the last 3 characters with '...'
  if len(string) >= CUTOFF_LENGTH:
    string = string[:CUTOFF_LENGTH - 3] + "..."
  return string

def grid_config(frame): #Set each column to constant width in accordance with COLUMN_WIDTHS
  frame.grid_rowconfigure(0, weight = 1) #rowconfigure required in conjunction with columnconfigure to take effect
  for i in range(len(COLUMN_WIDTHS)):
    frame.grid_columnconfigure(i, minsize = COLUMN_WIDTHS[i], weight = 1)
    #This only sets the minimum size. Do grid_propagate(False) to make it always that width

def entry_frame_config(frame, columns = 1): #Set each column to constant width (for trime, where there are 2 entries in one frame)
  frame.grid_propagate(True)
  frame.grid_rowconfigure(0, weight = 1)
  for i in range(columns):
    frame.grid_columnconfigure(i, weight = 1)

to_minutes = lambda seconds: "{}:{}".format(*map(two_digit, divmod(round(seconds), 60))) #Convert seconds to minutes

two_digit = lambda n: ("0" if len(str(n)) == 1 else "") + str(n) #Add a leading '0' if it's only one digit

is_float = lambda string: re.match(r"^[0-9]*\.?[0-9]*$", string) is not None and string != "" #Checks if float, but also allows '.'

float_ = lambda string: 0.0 if string == "." else float(string) #Converts to a float, but '.' is 0.0

class App(tk.Tk): #Inherits from tk.Tk so that self is also the window
  def __init__(self):
    super().__init__() #Run tk.Tk.__init__
    self.configure(**style()) #BG value in dictionary returned only
    self.title("W.I.P")
    self.pack_propagate(True) #By default, it's true, but here to make it easier to change
    self.resizable(0, 0) #Can't maximise or change width or height
    self.protocol("WM_DELETE_WINDOW", self.end) #Calls self.end when the window is closed, overriding the default 'self.destroy'

    ttk_style = ttk.Style() #Style for ttk widgets
    ttk_style.theme_use("default") #Default for your OS (tkinter works for Windows, Mac and Linux)
    ttk_style.configure("TProgressbar", thickness = 5) #Customise how thick the progress bar is

    effects = json.loads(open(FILE_PATH + r"\Config\Effects.json", "r").read()) #r"" means string where there are no escape sequences
    #Loads this file into a dictionary equivalent

    os.chdir(FILE_PATH + r"\Tracks") #Set CWD to 'Tracks'
    track_list = os.listdir() #List of all files in the folder 'Tracks'

    for file in track_list: 
      if file not in effects.keys():
        effects[file] = list(DEFAULT_PARAMS) #If new files added, make new set of default stats
    effect_copy = list(effects.keys()) #If it uses effects.keys(), there will be an IndexError as the length of it will decrease if anything is deleted
    ##print(effect_copy)
    for included in effect_copy:
      if included not in track_list: #If a file is no longer present, it can be removed to stop it from being loaded in
        del effects[included] #If files have been removed, remove them
    del effect_copy
    self.effects = effects #Make effects 'global' to the class (all methods within it can access it)
    self.tracks = [Track(track_list[i], 0.5 + audio_length(track_list[i]), i, *effects[track_list[i]]) for i in range(len(track_list))]
    #Create new Track object for each track name with the corrrct name, length and effects
    #Note that the 0.5 second buffer is to account for cutting tracks slightly short (a problem with the library?)
    with open(FILE_PATH + r"\Config\Order.txt") as file: #with statement automatically closes the file when it ends
      order = tuple(map(int, file.readlines())) #Convert each string into an integer
      order = [el for el in order if el < len(self.tracks)] #Remove all numbers that exceed the number of tracks, so as not to cause an IndexError
      if order == []: #If empty/deleted (by the user or by a crash), create a new order
        order = list(range(len(self.tracks)))
      for i in range(len(self.tracks) - len(order)):
        order.append(max(order) + 1) #If more tracks added, keep adding extra numbers on the end one more than the highest number there
        #Note that this causes new tracks to be added to the end by default
      print("order = {}".format(order))
      print(self.tracks)
      self.tracks = [self.tracks[num] for num in order] #Now they are the same length, put all of the tracks in the right order
      print(self.tracks)
    self.selection = (0, 0) #Selected track, selected attribute (edit mode only)
    self.track_selection = (0, 0) #Selected track, selected attribute. This allows for changing selection without changing the currently playing track
    self.modulo = (len(self.tracks), len(COLUMN_WIDTHS))
    self.end = False #Becomes true to make the loop that plays the track stop without orphaning a thread/deleting the root first
    self.mode = 0 #0, 1 or 2, corresponding to MODES
    self.top_frame = tk.Frame(height = 60, width = 1120, **style()) #Frame containing progress bar, mode and progress/time
    self.mode_lbl = tk.Label(self.top_frame, **style(20)) #style dictionary kwargs with font size as 20

    self.top_frame.grid_propagate(True) #Widgets can expand it
    for i in range(2):
      self.top_frame.grid_columnconfigure(i, weight = 1, minsize = 100) #So that 'Mode:' and the current mode are independently positioned
    self.top_frame.grid_rowconfigure(0, weight = 1, pad = 50) #Changing the mode would center the label and make it move, so this stops that
    tk.Label(self.top_frame, **style(20), text = "Mode:").grid(row = 0, column = 0, sticky = "E") #Does not need to be re-referenced
    self.mode_lbl.grid(row = 0, column = 1, sticky = "W") #"W" and "E" mean West and East, so they are as close as possible above the pad
    self.top_frame.grid(row = 0, column = 0, columnspan = 2)

    self.progress_dvar = tk.DoubleVar(self, value = 0) #Double has the same purpose as a float
    self.progress_dvar.trace("w", self.update_bar) #When updated, call self.update_bar
    self.progress_pb = ttk.Progressbar(self.top_frame, style = "TProgressbar", variable = self.progress_dvar, length = 1000, mode = "determinate")
    self.progress_pb.grid(row = 1, column = 0, columnspan = 2) #Two columns as the labels for 'Mode:' and current mode take a column each
    self.time_lbl = tk.Label(self.top_frame, **style(20)) #Label to display the progress, updated with 'self.update_bar'
    self.time_lbl.grid(row = 2, column = 0, columnspan = 2)
    self.update_bar() #So that the time's denominator is the length of the track selected

    self.category_frame = tk.Frame(self, height = 30, width = 1100, **style()) #One-row frame with each category listed
    self.category_frame.grid_propagate(False) #Each category should have a set size
    grid_config(self.category_frame) #Set it to same column widths as track frames so everything's in line
    for i in range(len(COLUMN_WIDTHS)):
      tk.Label(self.category_frame, text = "<{}>".format(ATTR_NAMES[i]), **style(12)).grid(row = 0, column = i) #Place down each one
      #Note that the less that/greater than symbols are just to look cool
    self.category_frame.grid(row = 1, column = 0, sticky = "W") #Place it down, also displaying every widget within it
    
    self.canvas = tk.Canvas(self, **style(), height = 375, width = 1100, highlightthickness = 0) #Widgets will be placed on this canvas
    self.song_frame = tk.Frame(self.canvas, **style()) #This frame goes on the canvas and the track frames are placed on this
    self.scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview, activebackground = BG, troughcolor = BG, **style())
    #Scrollbars are not customisable, hence why it does not fit in with the theme
    self.canvas.configure(yscrollcommand = self.scrollbar.set) #When it moves, alter the position of the scrollbar to account for it

    self.canvas.grid(row = 2, column = 0, pady = 10) #Add 10 units of spacing
    self.canvas.create_window((0, 0), window = self.song_frame, anchor = "n") #In the top-left corner (hence (0, 0))
    #This is placed down on the canvas so that when the scrollbar (which is bound to all children of self.canvas) moves, this frame moves
    self.scrollbar.grid(row = 2, column = 1, sticky = "NSW") #The 'NS' stretches it out up and down instead of being small

    self.song_frame.bind("<Configure>", self.on_frame_config) #Whenever a widget changes this frame's confiuration, calls the method
    self.bind("<Shift_L>", self.shift_pressed) #Note that there is no binding that encompasses both shifts
    if len(self.tracks) != 0: #This does not need to be done if there are not tracks and will raise exceptions
      self.bind("<space>", self.space_pressed)
      self.bind("<Return>", self.enter_pressed)
      for k, v in KEY_MOVE.items(): #For the arrow keys
        self.bind(k, lambda event, v = v: self.change_selection(v))

    self.track_frames = []
    for i in range(len(self.tracks)): #Iterate through self.tracks
      self.track_frames.append(TrackFrame(self.song_frame, self.tracks[i])) #Create frame that's controlled by its corresponding track
      self.track_frames[i].grid(row = i, column = 0) #Row should increment each time so they aren't all in the same place
    if len(self.tracks) != 0: #Would raise an IndexError otherwise as there wouldn't be anythin to highlight
      self.track_frames[0].highlight = range(len(COLUMN_WIDTHS)) #Highlight all columns in the first TrackFrame object
    self.entry_present = False #Whether or not there is an entry widget on screen (disables shift and space callbacks to not hinder typing)

    self.player = pyglet.media.Player() #Creates a track

    if len(self.tracks) != 0:
      self.play_thread = PlayThread(1, self.tracks[0], self) #Creates an instance of a class that inherits from threading.Thread
      self.play_thread.start() #Now all methods in this thread can be called at any time.

    self.shift_pressed(increment = 0) #Set up things within it without changing anything
    
    self.mainloop() #Done by default in IDLE, but when nothing is happening, this stops the program from closing

  def save(self):
    if len(self.tracks) == 0: #If there are no tracks, there is nothing to save
      print("Not saved")
      return #Stop anything else from happening below
    #Save order
    order = [track.num for track in self.tracks]
    os.chdir(FILE_PATH + r"\Config") #Navigate to 'Config' in the directory of this file
    with open("Order.txt", "w") as file: #Automatically closes after dedentation
      for n in order:
        file.write(str(n) + "\n") #Easier to read if each one is a newline and allows for numbers with > 1 digits
    print("Saved order as \n{}".format(order))
    
    #Save effects
    effects = {}
    for track in self.tracks:
      effects[str(track)] = track.compile_effects() #'compile_effects' is an ordered list of all useful attributes
    with open("Effects.json", "w") as file: #Closes 'file' when finished
      json.dump(effects, file) #Put 'effects' into 'Effects.json' as a dictionary
    print("Saved effects")
  
  def update_bar(self, *events): #Automatically adds extra arguments when called
    """Usage of *map below: map applies 'to_minutes' to each one. The 'format'
    method requires 2 arguments in this case, but 1 was given, an iterable of
    length 2, so, by 'starring' it, it unpacks the map object into 2 arguments.
    """
    if len(self.tracks) == 0: #Dividing by zero never ends well
      self.time_lbl.config(text = "00:00 / 00:00") #Default if there are no files
    else: #Gets length, converts it to minutes and displays at the end
      self.time_lbl.config(text = "{} / {}".format(*map(to_minutes, (self.progress_dvar.get(), self.tracks[self.track_selection[0]].length))))
  
  def on_frame_config(self, event):
    print("Config")
    """'bbox' is short for 'bounding box', so, by setting it to "all", it finds
    everything that's in the canvas. Alternatively, this can be a tuple,
    (n, e, s w). Called whenever """
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
    if self.mode == 2 and not self.entry_present: #Edit
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
      return #Only play if order or select

    if self.mode == 1: #Order, save
      self.save()
      return

    if self.track_selection != self.selection: #New item selected
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
      self.progress_pb.config(maximum = self.tracks[self.track_selection[0]].length)
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
    os.chdir(FILE_PATH + r"\Tracks")
    try:
      source = pyglet.media.load(repr(track_obj))
    except:
      print("Diagnostic:")
      print("os.listdir() = {}\nrepr(track_obj) = {}, CWD = {}".format(os.listdir(), repr(track_obj), os.getcwd()))
      sys.exit()
    self.player.queue(source)
    print(track_obj.trim[0])
    self.progress_dvar.set(track_obj.trim[0])
    self.focus_set()
    
  def shift_pressed(self, event = None, increment = 1): #Increment mode
    if self.tracks[self.selection[0]].playing:
      return
    self.mode = (self.mode + increment) % 3
    self.mode_lbl.config(text = MODES[self.mode])
    if len(self.tracks) != 0:
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
      self.save()
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
        if seek > track.length - track.trim[1]:
          seek = track.length - track.trim[1]
      if change[1] != 0:
        self.player.seek(seek)
        self.progress_dvar.set(self.player.time)
        self.update_bar()

    bottom = int(self.scrollbar.get()[1] * len(self.track_frames))
    if not self.selection[0] in range(bottom - 5, bottom):
      self.canvas.yview("moveto", (self.selection[0] / len(self.track_frames)))

  def end(self):
    self.player.pause()
    self.save()
    if len(self.tracks) != 0 and self.tracks[self.selection[0]].playing:
      print("Running")
      self.end = True
    else:
      print("Not running")
      if hasattr(self, "play_thread"):
        self.play_thread.parent.destroy()
      else:
        self.destroy()

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
    condition = lambda:(self.parent.player.time) < (self.track.length - self.track.trim[1])
    if not condition():
##      print("Progress = {}".format(track_frame_obj.track.trim[0]))
      self.parent.progress_dvar.set(track_frame_obj.track.trim[0])
    while condition():
      if not self.track.playing:
        self.parent.player.pause()
        return
      if self.parent.end:
        self.parent.destroy()
        return

      start_fade = self.track.length - self.track.trim[1] - self.track.fade
      if self.track.fade != 0 and self.parent.player.time >= start_fade:
        self.parent.player.volume = (1 - ((self.parent.player.time - start_fade) / self.track.fade)) #NOT WORKING
##        print(self.parent.player.volume)
      else:
        self.parent.player.volume = self.track.volume / 100
      self.parent.update()
##      if self.parent.player.time < self.parent.progress_dvar.get() and self.parent.progress_dvar.get() > 1:
      if self.parent.progress_dvar.get() >= self.track.length - self.track.trim[0]:
        print("END")
        break
      if self.parent.progress_dvar.get() - self.parent.player.time > 1:
        print("Backtracked")
        break
      else:
        self.parent.progress_dvar.set(self.parent.player.time)
##      else:
##        print("Looks like it skipped back")
    #Run code below if ended by getting to the end
    print("Exited")
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
    
    variables = tuple(self.track.trim) + (self.track.volume, self.track.fade)
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
    self.text = (CHARS[0], CHARS[self.track.loop + 2], "'{}'".format(add_ellipses(self.track.name)), "({}s, {}s)".format(*self.track.trim), to_minutes(int(self.track.length)), "{}%".format(self.track.volume), "{}s".format(self.track.fade))
    for i in range(1, len(self.labels)):
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
      valid = is_float(value) and float_(value) <= (self.track.length - (self.track.trim[0] + self.track.trim[1]))
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
