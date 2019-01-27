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

modes = ("Play", "Order", "Edit")
hl_bg = "#4c4c4c" #Colour for when highlighted
bg = "#212121"
fg = "#afafaf"
chars = "4;" #Pause and play in Webdings font
key_move = {
  "<Right>":(lambda column:(0, 2 if column in (2 , 5) else 1)),
  "<Left>":(lambda column:(0, -2 if column in (1 , 4) else -1)),
  "<Up>":(lambda column:(-1, 0)),
  "<Down>":(lambda column:(1, 0))
}
column_widths = (100, 400) + (150,) * 4

def style(size = 0): 
  result = {
    "bg":bg,
    }
  if size != 0:
    result["fg"] = fg
    result["font"] = ["Consolas", size]
  return result

def replace(dictionary, k, v):
  copy = dictionary.copy()
  copy[k] = v
  return copy

to_minutes = lambda seconds: "{}:{}".format(*map(two_digit, divmod(round(seconds), 60)))

two_digit = lambda n: ("0" if len(str(n)) == 1 else "") + str(n)

class App(tk.Tk):
  def __init__(self):
    super().__init__()
    self.configure(**style()) #bg value in dictionary returned only
    self.title("W.I.P")
    self.pack_propagate(0)
    self.resizable(0, 0)

    ttk_style = ttk.Style()
    ttk_style.theme_use("default")
    ttk_style.configure("TProgressbar", thickness = 5)

    self.tracks = [Track("Track #{}".format(i + 1), random.randint(10, 30)) for i in range(20)]
    self.selection = (0, 0) #Selected track, selected attribute (edit mode only)
    self.track_selection = (0, 0)
    self.modulo = (len(self.tracks), 6)
    self.mode = 0
    self.top_frame = tk.Frame(height = 60, width = 1120, **style())
    self.mode_lbl = tk.Label(self.top_frame, **style(20)) #style dictionary kwargs with font size as 20

    self.top_frame.grid_propagate(1)
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
    
    self.canvas = tk.Canvas(self, **style(), height = 375, width = 1100, highlightthickness = 0)
    self.song_frame = tk.Frame(self.canvas, **style())
    self.scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview, activebackground = bg, troughcolor = bg, **style())
    self.canvas.configure(yscrollcommand = self.scrollbar.set)

    self.canvas.grid(row = 1, column = 0, pady = 10)
    self.canvas.create_window((0, 0), window = self.song_frame, anchor = "n")
    self.scrollbar.grid(row = 1, column = 1, sticky = "NSW")

    self.song_frame.bind("<Configure>", self.on_frame_config)
    self.bind("<Shift_L>", self.inc_mode)
    self.bind("<space>", self.play_pause)
    for k, v in key_move.items():
      self.bind(k, lambda event, v = v: self.change_selection(v))

    self.track_frames = []
    for i in range(len(self.tracks)):
      self.track_frames.append(TrackFrame(self.song_frame, self.tracks[i]))
      self.track_frames[i].grid(row = i, column = 0)
    self.track_frames[0].highlight = range(6)

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
    self.track_selection = self.selection[:]
    self.update_bar()
    track_frame_obj = self.track_frames[self.track_selection[0]]
    track_frame_obj.playing_state_set("toggle")
    print(track_frame_obj.track.playing)
    """
      ##self.progress_pb.start(interval = 50)##round(10000 / len(track_frame_obj.track)))
      for i in range(10 * len(track_frame_obj.track)):
        self.progress_dv.set(self.progress_dv.get() + 0.1)
        self.update()
        time.sleep(0.1)
      track_frame_obj.playing_state_set(False)
    else:
      self.progress_pb.stop()
      ##self.progress_dv.set(0)
    """
  

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
      track_frame_obj.highlight = range(6)
      self.selection[1] = 1

    bottom = int(self.scrollbar.get()[1] * len(self.track_frames))
    if not self.selection[0] in range(bottom - 5, bottom):
      self.canvas.yview("moveto", (self.selection[0] / len(self.track_frames)))
    
    ##if not self.tracks[self.selection[0]].playing:
      ##self.update_bar()

class PlayThread(threading.Thread):
  def __init__(self, thread_id, track, parent):
    super().__init__()
    self.id = thread_id
    self.track = track
    self.parent = parent
  
  def run(self):
    print("Starting thread", self.id)
    while self.parent.progress_dv.get() < len(self.track):
      if self.track.playing:
        time.sleep(0.1)
        self.parent.progress_dv.set(self.parent.progress_dv.get() + 0.1)
        self.parent.update_bar()
    print("Exiting thread", self.id)
  
  def pause(self):
    pass

class Track:
  def __init__(self, name, track_length, trim_values = (0, 0), volume_modifier = 100, fade_time = 0):
    self.name = name
    self.length = track_length
    self.trim = trim_values[:]
    self.volume = volume_modifier
    self.fade = fade_time
    self.playing = False

  def __len__(self):
    return self.length

class TrackFrame(tk.Frame):
  def __init__(self, parent, track):
    super().__init__(parent, width = 1100, height = 75, bd = 0)
    self.grid_propagate(0)

    self.track = track

    text = (chars[0], "'{}'".format(track.name), "(-{}s, -{}s)".format(*track.trim), to_minutes(len(track)), "{}%".format(track.volume), "{}s".format(track.fade))
    self.grid_rowconfigure(0, weight = 1)
    for i in range(6):
      self.grid_columnconfigure(i, minsize = column_widths[i], weight = 1)
      style_dict = style(20)
      if i == 0:
        style_dict["font"][0] = "Webdings"
      tk.Label(self, **style_dict, text = text[i]).grid(row = 0, column = i, sticky = "NESW")
    self._highlight = []
  
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
