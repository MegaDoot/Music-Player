import tkinter as tk

style = lambda size = 10: {
    "bg":"#ffffff",
    "fg":"#111111",
    "font":("Sans Serif", size)
}

to_minutes = lambda seconds: "{}:{}".format(divmod(seconds, 60))

class App(tk.Tk):
  def __init__(self):
    return
    super().__init__()
    
    self.canvas = tk.Canvas(self, bd = 0, bg = "black")
    self.song_frame = tk.Frame(self.canvas, bg = "black")
    self.song_scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview)
    self.canvas.configure(yscrollcommand = self.song_scrollbar.set)
    
    self.mainloop()

class Track:
  def __init__(self, name, track_length, trim_values, volume_modifier):
    self.name = name
    self.length = track_length
    self.trim = trim_values[:]
    self.volume_mod = volume_modifier
  
  def play(self):
    pass

class TrackFrame(tk.Frame):
  def __init__(self, parent, track):
    super().__init__(parent)
    text = (track.name, "-{}, -{}".format(*track.trim), track.length, track.volume_mod)
    for i in range(4):
      tk.Label(**style(20), text = track[i]).grid(row = 0, column = i)

if __name__ == "__main__":
  app = App()

print(divmod(173, 60))
