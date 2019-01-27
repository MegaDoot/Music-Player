import tkinter as tk
import tkinter.ttk as ttk
import threading

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.pb_iv = tk.IntVar(self, value = 0)
        self.pb = ttk.Progressbar(self, variable = self.pb_iv, length = 1000)
        self.time_lbl = tk.Label(font = ("Consolas", 20))
        
        self.time_lbl.grid(row = 1, column = 1)
        self.pb.grid(row = 0, column = 0)

        self.pb_iv.trace("w", self.trace)
        
        self.bind("<space>", self.pause_play)
        
        self.mainloop()
    
    def trace(self, *args):
        self.time_lbl.config(text = self.pb_iv.get())
    
    def pause_play(self, *args):
        pass

if __name__ == '__main__':
    app = App()