import os
import os.path as op
import glob

class Dir:
    """
    def __init__(self, path):
        self.path = self.current = path
        folders = [name[len(path) + 1:-1] for name in glob.glob(op.join(path, "**\\*\\"), recursive = True)]
        print(folders)
        self.tree = []
        return
        for i in range(len(folders)):
            print(self.tree, "&", folders)
            self.tree.append(folders[i][0])
        print(self.tree)"""
    def __init__(self, path):
        self.path = path.split("\\")
        self.current = []
        print(self.path)
        self.tree = tree_dict(path)

    def down(self, folder):
        self.current.append(folder)
    
    def up(self):
        if self.current != []:
            del self.current[-1]
        else:
            raise Exception("At highest level already")

    def list(self, folder = None):
        if folder is None:
            current = self.current
        else:
            current = self.current + folder.split("\\")
        remaining = self.tree
        for folder in current:
            remaining = remaining[folder]
        return set(remaining)
    
    def __repr__(self):
        return str(set(self.list()))[1:-1].replace("'", "")

def tree_dict(path_): #Not mine (adapted from stackoverflow.com)
    file_token = ''
    for root, dirs, files in os.walk(path_):
        tree = {directory: tree_dict(os.path.join(root, directory)) for directory in dirs}
        tree.update({file: file_token for file in files})
        return tree  # note we discontinue iteration trough os.walk


test = Dir(r"C:\Users\alexs\Desktop\osdotwalk")
