import os
import pickle

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "table_meta.pkl")
with open(path, "rb") as f:
    data = pickle.load(f)
print(data)