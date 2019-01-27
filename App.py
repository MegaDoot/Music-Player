"""
Usage:
  Shift to change mode
  Up and down buttons to change selected track
  Left and right to change selected attribute (edit mode only)
"""

import tkinter as tk
import tkinter.ttk as ttk
import random
import threading
import time
import os

py_path = os.__file__[:-10]
paths = os.environ["PATH"].split(";")
if not py_path in paths:
  os.environ["PATH"] += py_path + ";"
  print("Added python to PATH")
try:
  import pyglet
except ImportError:
  os.system("echo pyglet not found; installing & python -m pip install pyglet")
  import pyglet

tracks_path = os.path.dirname(__file__) + r"\Tracks"
attr_names = ("State", "Loop", "Name", "Trim", "Duration","Volume", "Fade Time")
modes = ("Play", "Order", "Edit")
hl_bg = "#4c4c4c" #Colour for when highlighted
bg = "#212121"
fg = "#afafaf"
chars = "4;ar" #Pause, play, tick, cross in Webdings font
key_move = {
  "<Right>":(lambda column:(0, 2 if column in (3 , 6) else 1)),
  "<Left>":(lambda column:(0, -2 if column in (1 , 5) else -1)),
  "<Up>":(lambda column:(-1, 0)),
  "<Down>":(lambda column:(1, 0))
}
cutoff_length = 35
column_widths = (80, 80, 420, 130, 130, 130, 130)

def style(size = 0): 
  result = {
    "bg":bg,
    }
  if size != 0:
    result["fg"] = fg
    result["font"] = ["Consolas", size]
  return result

def replace(dictionary, *kv): #For debugging purporses
  copy = dictionary.copy()
  for k, v in kv:
    copy[k] = v
  return copy

def add_ellipses(string):
  if len(string) >= cutoff_length:
    string = string[:cutoff_length - 3] + "..."
  return string

def grid_config(frame):
  frame.grid_rowconfigure(0, weight = 1)
  for i in range(len(column_widths)):
    frame.grid_columnconfigure(i, minsize = column_widths[i], weight = 1)

to_minutes = lambda seconds: "{}:{}".format(*map(two_digit, divmod(round(seconds), 60)))

two_digit = lambda n: ("0" if len(str(n)) == 1 else "") + str(n)

class App(tk.Tk):
  def __init__(self):
    super().__init__()
    self.configure(**style()) #bg value in dictionary returned only
    self.title("W.I.P")
    self.pack_propagate(True)
    self.resizable(0, 0)
    self.protocol("WM_DELETE_WINDOW", self.end)

    ttk_style = ttk.Style()
    ttk_style.theme_use("default")
    ttk_style.configure("TProgressbar", thickness = 5)

    self.tracks = [Track("Track #{}".format(i + 1), random.randint(5, 10)) for i in range(20)]
    self.selection = (0, 0) #Selected track, selected attribute (edit mode only)
    self.track_selection = (0, 0)
    self.modulo = (len(self.tracks), len(column_widths))
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

    self.progress_dv = tk.DoubleVar(self, value = 0)
    self.progress_dv.trace("w", self.update_bar)
    self.progress_pb = ttk.Progressbar(self.top_frame, maximum = len(self.tracks[0]), style = "TProgressbar", variable = self.progress_dv, length = 1000, mode = "determinate")
    self.progress_pb.grid(row = 1, column = 0, columnspan = 2)
    self.time_lbl = tk.Label(self.top_frame, **style(20))
    self.time_lbl.grid(row = 2, column = 0, columnspan = 2)
    self.update_bar()

    self.category_frame = tk.Frame(self, height = 30, width = 1100, **style())
    self.category_frame.grid_propagate(False)
    grid_config(self.category_frame)
    for i in range(len(column_widths)):
      tk.Label(self.category_frame, text = "<{}>".format(attr_names[i]), **style(12)).grid(row = 0, column = i)
    self.category_frame.grid(row = 1, column = 0, sticky = "W")
    
    self.canvas = tk.Canvas(self, **style(), height = 375, width = 1100, highlightthickness = 0)
    self.song_frame = tk.Frame(self.canvas, **style())
    self.scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview, activebackground = bg, troughcolor = bg, **style())
    self.canvas.configure(yscrollcommand = self.scrollbar.set)

    self.canvas.grid(row = 2, column = 0, pady = 10)
    self.canvas.create_window((0, 0), window = self.song_frame, anchor = "n")
    self.scrollbar.grid(row = 2, column = 1, sticky = "NSW")

    self.song_frame.bind("<Configure>", self.on_frame_config)
    self.bind("<Shift_L>", self.inc_mode)
    self.bind("<space>", self.play_pause)
    for k, v in key_move.items():
      self.bind(k, lambda event, v = v: self.change_selection(v))

    self.track_frames = []
    for i in range(len(self.tracks)):
      self.track_frames.append(TrackFrame(self.song_frame, self.tracks[i]))
      self.track_frames[i].grid(row = i, column = 0)
    self.track_frames[0].highlight = range(len(column_widths))

    self.play_thread = PlayThread(1, self.tracks[0], self)
    self.play_thread.start()

    self.inc_mode(increment = 0)
    
    self.mainloop()
  
  def update_bar(self, *events):
    self.time_lbl.config(text = "{} / {}".format(to_minutes(self.progress_dv.get()), to_minutes(len(self.tracks[self.track_selection[0]]))))
  
  def on_frame_config(self, event):
    self.canvas.configure(scrollregion = self.canvas.bbox("all"))
  
  def play_pause(self, *args):
    if self.mode != 0:
      return
    if self.track_selection != self.selection:
      for i in range(len(self.track_frames)):
        self.track_frames[i].playing_state_set(False)
      self.progress_dv.set(0)
    self.track_selection = self.selection[:]
    self.update_bar()
    track_frame_obj = self.track_frames[self.track_selection[0]]
    track_frame_obj.playing_state_set("toggle")
    if track_frame_obj.track.playing:
      self.play_thread.play()
    
  def inc_mode(self, event = None, increment = 1):
    self.mode = (self.mode + increment) % 3
    self.mode_lbl.config(text = modes[self.mode])
    self.change_selection(lambda column:(0, 0))

  def change_selection(self, change):
    change = change(self.selection[1])
    self.selection =  [(self.selection[i] + change[i]) % self.modulo[i] for i in range(2)]

    for obj in self.track_frames:
      obj.highlight = []
    track_frame_obj = self.track_frames[self.selection[0]]
    if self.mode == 2:
      track_frame_obj.highlight = [self.selection[1]]
    else:
      track_frame_obj.highlight = range(len(column_widths))
      self.selection[1] = 1

    bottom = int(self.scrollbar.get()[1] * len(self.track_frames))
    if not self.selection[0] in range(bottom - 5, bottom):
      self.canvas.yview("moveto", (self.selection[0] / len(self.track_frames)))
    
    ##if not self.tracks[self.selection[0]].playing:
      ##self.update_bar()

  def end(self):
    if self.tracks[self.selection[0]].playing:
      print("Running")
      self.end = True
    else:
      print("Not running")
      self.play_thread.parent.destroy()

class PlayThread(threading.Thread):
  def __init__(self, thread_id, track, parent):
    super().__init__(daemon = True)
    self.id = thread_id
    self.track = track
    self.parent = parent
  
  def run(self):
    self.play()

  def play(self):
    track_frame_obj = self.parent.track_frames[self.parent.selection[0]]
    self.track = track_frame_obj.track
    condition = lambda:self.parent.progress_dv.get() < len(self.track)
    if not condition():
      self.parent.progress_dv.set(0)
    while condition():
      if not self.track.playing:
        return
      if self.parent.end:
        self.parent.destroy()
        return
      self.parent.update()
      time.sleep(0.1)
      self.parent.progress_dv.set(self.parent.progress_dv.get() + 0.1)
      self.parent.update_bar()
    #Run below if ended by getting to the end
    track_frame_obj.playing_state_set(False)

class Track:
  def __init__(self, name, track_length, trim_values = (0, 0), volume_modifier = 100, fade_time = 0, loop = False):
    self.name = name
    self.length = track_length
    self.trim = trim_values[:]
    self.volume = volume_modifier
    self.fade = fade_time
    self.loop = loop
    self.playing = False

  def __len__(self):
    return self.length

  def __repr__(self):
    return "(Name: '{}', Length: {}, Trim: {}, Volume Modifier: {}, Fade Time: {}, Loop: {}, Playing: {})".format(self.name, to_minutes(self.length), self.trim, self.volume, self.fade, self.loop, self.playing)

class TrackFrame(tk.Frame):
  def __init__(self, parent, track):
    super().__init__(parent, width = 1100, height = 75, bd = 0)
    self.grid_propagate(False)

    self.track = track
    self.update_text()
    
    grid_config(self)
    for i in range(len(self.text)):
      style_dict = style(14)
      if i in (0, 1):
        style_dict["font"][0] = "Webdings"
      tk.Label(self, **style_dict, text = self.text[i]).grid(row = 0, column = i, sticky = "NESW")
    self._highlight = []

  def update_text(self):
    self.text = (chars[0], chars[self.track.loop + 2], "'{}'".format(add_ellipses(self.track.name)), "(-{}s, -{}s)".format(*self.track.trim), to_minutes(len(self.track)), "{}%".format(self.track.volume), "{}s".format(self.track.fade))
  
  @property
  def highlight(self):
    return self._highlight
  
  @highlight.setter
  def highlight(self, value):
    self._highlight = value
    for i in range(len(self.winfo_children())):
      self.winfo_children()[i].config(bg = (hl_bg if i in self.highlight else style()["bg"]))
  
  def playing_state_set(self, value):
    if value == "toggle":
      self.track.playing = not self.track.playing
    else:
      self.track.playing = value #Toggle
    self.winfo_children()[0].config(text = chars[self.track.playing])

if __name__ == "__main__":
  app = App()
