import pickle
with open("output/table_meta.pkl", "rb") as f:
    data = pickle.load(f)
print(data)