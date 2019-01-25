import tkinter as tk

class App(tk.Tk):
  def __init__(self):
    super().__init__()
    self.canvas = tk.Canvas(self, bd = 0, bg = "black")
    self.song_frame = tk.Frame(self.canvas, bg = "black")
    self.song_scrollbar = tk.Scrollbar(self, orient = "vertical", command = self.canvas.yview)
    self.canvas.configure(yscrollcommand = self.song_scrollbar.set)
    self.mainloop()

class Track:
  def __init__(self, name, length, stagger, volume_mod):
    self.name = name
    

if __name__ == "__main__":
  app = App()
