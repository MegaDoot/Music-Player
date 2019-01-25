import tkinter as tk
import random

modes = ("Select Mode", "Order Mode")
hl_bg = "#4c4c4c" #Colour for when highlighted

style = lambda size = 10: {
    "bg":"#ffffff",
    "fg":"#111111",
    "font":("Comic Sans Ms", size)
}

to_minutes = lambda seconds: "{}:{}".format(*divmod(seconds, 60))

class App(tk.Tk):
  def __init__(self):
    super().__init__()
    self.configure(bg = style()["bg"]) #bg value in dictionary returned
    self.title("W.I.P")

    self.mode_lbl = tk.Label(**style(20), pady = 10) #style dictionary kwargs with font size as 20
    self.mode = modes[0] #Calls setter
    self.mode_lbl.grid(row = 0, column = 0)
    
    self.canvas = tk.Canvas(self, borderwidth = 4, relief = "solid", bg = "black")
    self.song_frame = tk.Frame(self.canvas, bg = "black")
    self.song_scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview)
    self.canvas.configure(yscrollcommand = self.song_scrollbar.set)

    self.canvas.grid(row = 1, column = 0)
    self.song_frame.grid(row = 0, column = 0) #Within canvas
    self.song_scrollbar.grid(row = 1, column = 1, sticky = "NSW")

    track_frames = []
    for i in range(len(tracks)):
      track_frames.append(TrackFrame(self.canvas, tracks[i]))
      track_frames[i].grid(row = i, column = 0)
    
    print(track_frames[0].winfo_children())
    
    self.mainloop()
  
  @property
  def mode(self):
    return self._mode
  
  @mode.setter
  def mode(self, value):
    print("Setter")
    self._mode = value
    self.mode_lbl.config(text = "Mode = ({})".format(self._mode))

class Track:
  def __init__(self, name, track_length, trim_values = (0, 0), volume_modifier = 100):
    self.name = name
    self.length = track_length
    self.trim = trim_values[:]
    self.volume_mod = volume_modifier
  
  def play(self):
    pass

class TrackFrame(tk.Frame):
  def __init__(self, parent, track):
    super().__init__(parent, width = 500, height = 50)
    self.grid_propagate(0)

    text = ("'{}'".format(track.name), "(-{}, -{})".format(*track.trim), to_minutes(track.length), track.volume_mod)
    for i in range(4):
      self.grid_columnconfigure(i, weight = 1, minsize = 50)
      tk.Label(self, **style(20), text = text[i]).grid(row = 0, column = i, sticky = "EW")
    self._highlight = False
  
  @property
  def highlight(self):
    return _highlight
  
  @highlight.setter
  def highlight(self, value):
    self._highlight = value
    self.config(bg = (hl_bg if value else style()["bg"]))

if __name__ == "__main__":
  tracks = [Track("Track # {}".format(i), random.randint(30, 180)) for i in range(5)]
  app = App()

print(to_minutes(100))