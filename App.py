import tkinter as tk
import random
import threading

modes = ("Select", "Order", "Edit")
hl_bg = "#4c4c4c" #Colour for when highlighted
bg = "#212121"
fg = "#afafaf"
chars = ";4" #Pause and play in Webdings font
key_move = {
  "<Right>":(lambda column:(0, 2 if column == 4 else 1)),
  "<Left>":(lambda column:(0, -2 if column == 1 else -1)),
  "<Up>":(lambda column:(-1, 0)),
  "<Down>":(lambda column:(1, 0))
}
column_widths = (50, 450, 200, 200, 200)

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

to_minutes = lambda seconds: "{}:{}".format(*map(two_digit, divmod(seconds, 60)))

two_digit = lambda n: ("0" if len(str(n)) == 1 else "") + str(n)

class App(tk.Tk):
  def __init__(self):
    super().__init__()
    self.configure(**style()) #bg value in dictionary returned only
    self.title("W.I.P")

    self.tracks = [Track("Track #{}".format(i + 1), random.randint(30, 180)) for i in range(10)]
    self.selection = (0, 0) #Selected track, selected attribute (edit mode only)
    self.modulo = (len(self.tracks), 5)
    self.mode = 0
    self.mode_frame = tk.Frame(height = 60, width = 1120, **style())
    self.mode_lbl = tk.Label(self.mode_frame, **style(20)) #style dictionary kwargs with font size as 20
    
    self.mode_frame.grid_propagate(0)
    for i in range(2):
      self.mode_frame.grid_columnconfigure(i, weight = 1, minsize = 100)
    self.mode_frame.grid_rowconfigure(0, weight = 1)
    tk.Label(self.mode_frame, **style(20), text = "Mode:").grid(row = 0, column = 0, sticky = "E")
    self.mode_lbl.grid(row = 0, column = 1, sticky = "W")
    self.mode_frame.grid(row = 0, column = 0, columnspan = 2)
    
    self.canvas = tk.Canvas(self, **style(), height = 375, width = 1100, highlightthickness = 0)
    self.song_frame = tk.Frame(self.canvas, **style())
    self.song_scrollbar = tk.Scrollbar(self, orient = "vertical", command = lambda *args: [print(args), self.canvas.yview(*args)], activebackground = bg, troughcolor = bg, **style())
    self.canvas.configure(yscrollcommand = self.song_scrollbar.set)

    self.canvas.grid(row = 1, column = 0)
    self.canvas.create_window((0, 0), window = self.song_frame, anchor = "n")
    self.song_scrollbar.grid(row = 1, column = 1, sticky = "NSW")

    self.song_frame.bind("<Configure>", self.on_frame_config)
    self.bind("<Shift_L>", self.inc_mode)
    for k, v in key_move.items():
      self.bind(k, lambda event, v = v: self.change_selection(v))

    self.track_frames = []
    for i in range(len(self.tracks)):
      self.track_frames.append(TrackFrame(self.song_frame, self.tracks[i]))
      self.track_frames[i].grid(row = i, column = 0)
    self.track_frames[0].highlight = range(5)

    self.inc_mode(increment = 0)
    
    self.mainloop()
  
  def on_frame_config(self, event):
    self.canvas.configure(scrollregion = self.canvas.bbox("all"))
  
  def inc_mode(self, event = None, increment = 1):
    self.mode = (self.mode + increment) % 3
    self.mode_lbl.config(text = modes[self.mode])
    self.change_selection(lambda column:(0, 0))

  def change_selection(self, change):
    change = change(self.selection[1])
    ##print("Before:", self.selection)
    self.selection =  [(self.selection[i] + change[i]) % self.modulo[i] for i in range(2)]
    ##print("After:", self.selection)
    val = 0.1 * self.selection[0]
    self.canvas.yview("moveto", val)
    for obj in self.track_frames:
      obj.highlight = []
    track_frame_obj = self.track_frames[self.selection[0]]
    if self.mode == 2:
      track_frame_obj.highlight = [self.selection[1]]
    else:
      track_frame_obj.highlight = range(5)
      self.selection[1] = 1
    #0 1, 0.1 0.6, 0.2 0.7
    ##self.song_scrollbar.set(val, val + 0.5)

class Track:
  def __init__(self, name, track_length, trim_values = (0, 0), volume_modifier = 100):
    self.name = name
    self.length = track_length
    self.trim = trim_values[:]
    self.volume_mod = volume_modifier
    self.playing = False
  
  def play_pause(self):
    self.playing = not self.playing #Toggle

class TrackFrame(tk.Frame):
  def __init__(self, parent, track):
    super().__init__(parent, width = 1100, height = 75, bd = 1)
    self.grid_propagate(0)

    text = (chars[0], "'{}'".format(track.name), "(-{}s, -{}s)".format(*track.trim), to_minutes(track.length), "{}%".format(track.volume_mod))
    self.grid_rowconfigure(0, weight = 1)
    for i in range(5):
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
    for i in range(5):
      self.winfo_children()[i].config(bg = (hl_bg if i in self.highlight else style()["bg"]))

if __name__ == "__main__":
  app = App()
