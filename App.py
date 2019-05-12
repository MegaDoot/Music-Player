r"""
431

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
import threading #For running more than one process at one time
import time #Pause certain amounts of time
import os #File management
import sys #Command line arguments and exiting process
import json #Loads/ dumps JSON files/dictionaries
import re #Regular expressions for checking validity of information entered
import turtle #Draws fade graph
#Also import pyglet, soundfile, mutagen.mp3 and eyed3

if getattr(sys, "frozen", False): #If executable
  print("Running as executable")
  FILE_PATH = os.path.dirname(sys.executable)
else:
  print("Running as python file")
  FILE_PATH = os.path.dirname(os.path.realpath(__file__)) #Location of this file

NAMES_COMMANDS = (
  ("pyglet","python -m pip install pyglet"), #Note that '-m' means module
  ("soundfile","python -m pip install soundfile"), #For using metadata to find length of file
  ("mutagen.mp3", "python -m pip install mutagen"), #Find length of .mp3 if metadata not available/erroneous/wrong format
  ("eyed3", "python -m pip install python-magic-bin==0.4.14 & python -m pip install eyed3"), #libmagic needed for eyed3, for .wav
)

PY_PATH = os.path.dirname(sys.executable) #Any library will do
PATHS = os.environ["PATH"].split(";") #PATH is separated by semicolons - produces a list containing each path
FFMPEG_PATH = FILE_PATH + r"\ffmpeg\ffmpeg-20190511-68bac50-win32-static\bin"

def add_path(path):
  if not path in PATHS: #Must be in paths to be used on the command line
    os.environ["PATH"] += ";" + path #Add to path (temporarily)

add_path(PY_PATH)
add_path(FFMPEG_PATH)

def imp(name):
  globals()[name] = __import__(name)

for i in range(len(NAMES_COMMANDS)):
  try:
    imp(NAMES_COMMANDS[i][0]) #Import the first string in the selected tuple
  except ImportError:
    os.system("echo {} not found; installing & {} & Pause".format(*NAMES_COMMANDS[i])) #Install it on the command line
    try: #Not guarunteed to wirj
      imp(NAMES_COMMANDS[i][0])
    except: #Note that errors raised by os.system are not caught (hence the exception that encompasses all)
      print("ERROR: Could not import library '{}' (see top of code for troubleshooting)".format(NAMES_COMMANDS[i][0]))

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
DEFAULT_PARAMS = (False, (0.0, 0.0), 100, (0.5, 0.0)) #When Config.json is missing the file (i.e. new file added), use these arguments

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
  frame.grid_propagate(False)
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
    ttk_style.configure("TProgressbar", thickness = 5, background = "#f40000") #Customise how thick the progress bar is

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
    self.scrollbar.grid(row = 2, column = 1, sticky = "NSE") #The 'NS' stretches it out up and down instead of being small

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
    print("Saved order")# as \n{}".format(order))
    
    #Save effects
    effects = {}
    for track in self.tracks:
      effects[str(track)] = track.compile_effects() #'compile_effects' is an ordered list of all useful attributes
    with open("Effects.json", "w") as file: #Closes 'file' when finished
      json.dump(effects, file) #Put 'effects' into 'Effects.json' as a dictionary
    print("Saved effects")
    print(effects)
  
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
  
  def enter_pressed(self, event): #Called when enter pressed, 'event' gives details, i.e. widget focus
    track_frame = self.track_frames[self.selection[0]] #Set to current highlighted track
    if not self.entry_present or self.mode != 2: #If no text entries on screen or not in edit mode
      return #Stop this procedure from doing anything else
    sel = self.selection[1]
    if sel in (3, 6): #If trim selected
      index = (3, 6).index(sel)
      selected_entry = None
      if event.widget in track_frame.stat_entries:
        selected_entry = track_frame.stat_entries.index(event.widget)
      if selected_entry in (0, 3) and track_frame.trace_trim(0): #If correct widget focus and valid input
        track_frame.stat_entries[selected_entry + 1].focus_set() #Put cursor on widget (doesn't have to be clicked)
      elif selected_entry in (1, 4) and track_frame.trace_trim(1): #If selected second (last) entry and valid input
        assign = [float_(track_frame.stat_entries[i].get()) for i in range(selected_entry - 1, selected_entry + 1)]
        if sel == 3:
          self.tracks[self.selection[0]].trim = assign #Set values to values typed
        elif sel == 6:
          self.tracks[self.selection[0]].fade = assign
          print(assign)
          print("Fade =", self.tracks[self.selection[0]].fade)
        track_frame.update_text() #Frame shows correct text
        track_frame.trim_frames[index].grid_remove() #Get rid of text boxes...
        track_frame.grid_widget(sel) #...and replace them with correct label displaying text
        self.entry_present = False #As there are now no entries on screen
    elif self.selection[1] == 5 and track_frame.trace_trim(2) and track_frame.trace_trim(3): #Volume
##      if self.selection[1] == 5: #If volume
      self.tracks[self.selection[0]].volume = int(track_frame.stat_entries[2].get()) #Set value
##      else: #elif self.selection[1] == 6, but 'else' by process of elimination
##        self.tracks[self.selection[0]].fade = float_(track_frame.stat_entries[3].get()) #'float_' also accepts '.'
      track_frame.update_text() #Text updates to be accurate to variables it represents
      track_frame.grid_widget(self.selection[1]) #Place down widget no. 5 or 6
      self.entry_present = False #Entries are no longer present, allowing other procedures to run

  def space_pressed(self, event):
    if self.entry_present: #Don't do anything if currently typing
      return #Stop any further code from running in this procedure
    if self.mode == 2: #Edit mode
      sel = self.selection[1] #Pointer for easier access and higher efficiency & readability
      track_frame = self.track_frames[self.selection[0]] #Pointer with a shorter name so any changes are between both
      if self.selection[1] == 1: #Loop mode
        track_frame.track.loop = not track_frame.track.loop #Toggle - when pressed, toggle between
      elif sel in (3, 6): #Trim or fade (both have 2 entries)
        print("Sel =", sel)
        index = {3:0, 6:1}[sel]
        track_frame.labels[sel].grid_remove() #Remove to add text entries instead
        track_frame.trim_frames[index].grid(row = 0, column = sel, sticky = "NESW") #Place down and fill entire allocated row and column
        track_frame.stat_entries[0 if sel == 3 else 3].focus_set() #Place cursor
        print(track_frame.trim_frames[index].winfo_children()[0].grid_info())
        self.entry_present = True #So it performs normally afterwards
      elif self.selection[1] == 5: #If volume
        track_frame.labels[self.selection[1]].grid_remove() #Remove selected label
        track_frame.unique_frame.grid(row = 0, column = self.selection[1], sticky = "NESW") #Uniqe: one text entry
        track_frame.stat_entries[self.selection[1] - 3].focus_set() #Set focus to current entry
        self.entry_present = True #I've explained what this does enough ties
      self.track_frames[self.selection[0]].update_text() #I've explained this one enough too
      return #Only play if order or select

    if self.mode == 1: #Order, save
      self.save() #When changed, save state (so that closing incorrectly will still save)
      return #Nothing else required

    if self.track_selection != self.selection: #New item selected
      self.player.pause() #Will stop previous track (would continue even if deleted)
      self.media_player(self.tracks[self.selection[0]]) #Reassign and reset everything
      ##self.music_thread.set_track(self.tracks[self.selection[0]])
      for i in range(len(self.track_frames)): #Iterate throught number of tracks
        self.track_frames[i].playing_state_set(False) #Stop each track from playing
      self.progress_dvar.set(0) #Reset progress

    self.track_selection = self.selection[:] #[:] stops track_selection from being a pointer to
    self.update_bar() #Set it to 0 seconds in
    track_frame_obj = self.track_frames[self.track_selection[0]] #Concise pointer for easier access
    track_frame_obj.playing_state_set("toggle") #Toggle sets it to the oppsite of current value
    if track_frame_obj.track.playing: #If a song is currently playing
      self.progress_pb.config(maximum = self.tracks[self.track_selection[0]].length) #Set maximum value to length of selected song
      seek_time = self.tracks[self.selection[0]].trim[0] #Start track at first trim value
      if self.player.time < seek_time: #Only set if it's below (otherwise, resume)
        if seek_time > 0: #This appears to be a bug with pyglet, where it will constantly reset set to 0 if 0
          print("trim[0] = {}".format(seek_time))
          self.player.seek(seek_time) #Set time to seek_time
      self.play_thread.play() #Play track
  
  def media_player(self, track_obj):
    """Resets self.player as it uses a queue that cannot be reversed or
    backtracked after reaching the end, so it is necessary to use just one
    track in the queue and delete it and reset it once the end is reached."""
    self.player.pause() #Stop current track as it will continue even if it has been deleted
    del self.player #Remove it from memory
    self.player = pyglet.media.Player() #Reset it to a new player object
    os.chdir(FILE_PATH + r"\Tracks") #Go to 'Tracks' folder in current working directory
    try: #Attempt - can cause errors (the cause of which is unknown to me)
      source = pyglet.media.load(repr(track_obj)) #Load name of track object
    except Exception as error: #No specific error, 'error' saved to record type
      print("Diagnostic:")
      print("Error type = '{}'".format(type(error))) #Tyoe of exception raised
      print("os.listdir() = {}\nrepr(track_obj) = {}, CWD = {}".format(os.listdir(), repr(track_obj), os.getcwd())) #General diagnostic
      sys.exit() #Stop program from running
    self.player.queue(source) #Add track to queue
    print(track_obj.trim[0])
    self.progress_dvar.set(track_obj.trim[0]) #Reset track to first trim value
    self.focus_set() #Set focus to root window
    
  def shift_pressed(self, event = None, increment = 1): #Increment mode
    if self.tracks[self.selection[0]].playing: #Don't change mode if track is currently playing (subject to change)
      return #Stop any further code from running (stops mode from changing)
    self.mode = (self.mode + increment) % 3 #If above 3 or below 0, loop back so it doesn't raise an IndexError
    self.mode_lbl.config(text = MODES[self.mode]) #Set label to display name of mode number from a list of names
    if len(self.tracks) != 0: #If list of tracks is not empty
      self.change_selection(lambda column:(0, 0)) #

  def change_selection(self, change):
    if self.entry_present: #If textboxes present on screen, don't allow mode change
      return #Stop this procedure from running
    change = change(self.selection[1]) #For easier usage, sets change to correct value (should this be skipped)
    self.selection =  [(self.selection[i] + change[i]) % self.modulo[i] for i in range(2)] #Change selection by given value

    if self.mode == 1: #If order mode
      pos = self.selection[0] #Currently selected track
      edits = (pos, (pos - change[0]) % len(self.tracks)) #Currently selected and new selected (what should be switched)
      self.tracks[edits[0]], self.tracks[edits[1]] = self.tracks[edits[1]], self.tracks[edits[0]] #Switch these two tracks
      for i in range(2): #Iterate through each 2 elements of edit
        self.track_frames[edits[i]].destroy() #Remove this frame from the grid manager permentantly
        new = edits[i] #Easier acess and more efficient
        self.track_frames[edits[i]] = TrackFrame(self.song_frame, self.tracks[new]) #Make new frame to replace old one as tracks are switched
        self.track_frames[edits[i]].grid(row = edits[i], column = 0) #Add new frame to grid in correct place
      self.save() #After each action, save state
    for obj in self.track_frames: #Go through each track frame
      obj.highlight = [] #Remove highlight from each widget
    track_frame_obj = self.track_frames[self.selection[0]] #For more concise and efficient access later
    if self.mode == 2: #If edit mode
      track_frame_obj.highlight = [self.selection[1]] #Set highlighted stat to highighted
    else: #Select or order mode
      track_frame_obj.highlight = range(len(COLUMN_WIDTHS)) #Set highlight to all stats in row (highlight whole row)
      self.selection[1] = 1 #Reset stat selection (so not preserved when goes back to edit mode)

      track = self.tracks[self.selection[0]] #Juance again, for easier access, readability, 'dryness' and efficiency
      if change[1] < 0: #If left pressed/goes backwards (serves purpose of changing stat selection and time within track)
        seek = self.player.time - 5 #5 backwards seconds
        if seek < track.trim[0]: #If it goes back too far (before it should)
          seek = track.trim[0] #Set it to earliest possible point (start of song)
        if seek == 0: #Bug with Pyglet where seeking to 0 causes constant juttering and not playing, just looping first part
          seek = 0.01 #Set to imperceptible time after start and 0.01 seems appropriate
      elif change[1] > 0: #If right arrow pressed, goes forward/right
        seek = self.player.time + 5 #Forward 5 seconds into the track
        if seek > track.length - track.trim[1]: #If number exceeds ending point of song
          seek = track.length - track.trim[1] #Set to latest possible point in the song
      if change[1] != 0: #If either check for greater or less than 0 correct
        self.player.seek(seek) #Set current time to time calculated to seek to
        self.progress_dvar.set(self.player.time) #Update progress variable to display correct time
        self.update_bar() #Update progress bar to display correct length

    bottom = int(self.scrollbar.get()[1] * len(self.track_frames)) #Track at the bottom currently visible tracks
    if not self.selection[0] in range(bottom - 5, bottom): #If selected track is not on screen
      self.canvas.yview("moveto", (self.selection[0] / len(self.track_frames))) #Move the canvas so that is the case

  def end(self):
    """Calls when root window closes"""
    if hasattr(self, "player"):
      self.player.pause() #Stop track from playing
    self.save() #Save current state
    if len(self.tracks) != 0 and self.tracks[self.selection[0]].playing:
      print("Running")
      self.end = True #Check in while loop in thread recognises this and stops safely
    else:
      print("Not running")
      if hasattr(self, "play_thread"): #If 'play_thread' is initialised
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
    print("play")
    self.parent.player.play()
    track_frame_obj = self.parent.track_frames[self.parent.selection[0]]
    self.track = track_frame_obj.track
    length = self.track.length
    trim = self.track.trim
    fade = self.track.fade
    fade_out_from = self.track.length - self.track.trim[1] - self.track.fade[1] #Start the fading out
    fade_in_until = self.track.trim[0] + self.track.fade[0]
    
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
      
##      if self.track.fade[1] != 0 and self.parent.player.time >= start_fade_end:
##        self.parent.player.volume = (1 - ((self.parent.player.time - start_fade_end) / self.track.fade[1]))
##      elif self.track.fade[0] != 0 and self.parent.player.time <= start_fade_start and self.parent.player.time > self.track.trim[0]:
##        self.parent.player.volume = self.parent.player.time / self.track.fade[0]
##      else:
##        self.parent.player.volume = self.track.volume / 100
      time = self.parent.player.time
      volume_mod = self.track.volume / 100
      if fade[0] != 0 and time <= fade_in_until and time >= trim[0]:
        volume_mod *= (time - trim[0]) / fade[0]
      if fade[1] != 0 and time <= length - trim[1] and time >= fade_out_from:
        volume_mod *= 1- ((time - fade_out_from) / fade[1])
      self.parent.player.volume = volume_mod
      self.parent.update()
##      if self.parent.player.time < self.parent.progress_dvar.get() and self.parent.progress_dvar.get() > 1:
      if self.parent.progress_dvar.get() >= self.track.length - self.track.trim[0]:
        print("END")
        break
      if self.parent.progress_dvar.get() - self.parent.player.time > 0.2:
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

    self.trim_frames = [tk.Frame(self, **style()) for i in range(2)]
    ##
    for i in range(2):
      entry_frame_config(self.trim_frames[i], 2)
    ##
    variables = tuple(self.track.trim) + tuple([self.track.volume]) + tuple(self.track.fade)
    self.stat_entries = []
    self.stat_svars = [tk.StringVar(value = variables[i]) for i in range(5)]
    self.unique_frame = tk.Frame(self, **style())

    #Loop below: 4 string variables for 5 entries (2 for trim, 1 for volume, 2 for fade)
    for i in range(5): #Terary operators: 0 or 1 for trim, 2 or 3 for independent stats
      if i == 2:
        col = 0
        frame = self.unique_frame
      else:
        if i < 2:
          col = i
          frame = self.trim_frames[0]
        else:
          col = i - 3
          frame = self.trim_frames[1]
      self.stat_entries.append(tk.Entry(frame, textvariable = self.stat_svars[i], width = (4 if i == 2 else 6), **ENTRY_KW))
      self.stat_entries[i].grid(row = 0, column = col, sticky = "EW") #0 if only one text entry
      if i == 2: #If third/volume
        entry_frame_config(self.unique_frame, 1)
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
    self.text = (CHARS[0], CHARS[self.track.loop + 2], "'{}'".format(add_ellipses(self.track.name)), "{}s, {}s".format(*self.track.trim), to_minutes(int(self.track.length)), "{}%".format(self.track.volume), "{}s, {}s".format(*self.track.fade))
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
