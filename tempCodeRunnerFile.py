if self.mode == 2:
      track_frame = self.track_frames[self.selection[0]]
      if self.selection[1] == 1: #Loop
        track_frame.track.loop = not track_frame.track.loop
      elif self.selection[1] == 3: #Trim
        print("Trim")
        if self.entry_present:
          pass
        else:
          track_frame.labels[3].grid_remove()
          track_frame.trim_frame.grid(row = 0, column = 3, sticky = "NESW")
          track_frame.trim_entries[0].focus_set()
          self.entry_present = True
      self.track_frames[self.selection[0]].update_text()

    if self.mode != 0:
      return
    if self.track_selection != self.selection:
      for i in range(len(self.track_frames)):
        self.track_frames[i].playing_state_set(False)
      self.progress_dvar.set(0)
    self.track_selection = self.selection[:]
    self.update_bar()
    track_frame_obj = self.track_frames[self.track_selection[0]]
    track_frame_obj.playing_state_set("toggle")
    if track_frame_obj.track.playing:
      self.progress_pb.config(maximum = len(self.tracks[self.track_selection[0]]))
      self.play_thread.play()