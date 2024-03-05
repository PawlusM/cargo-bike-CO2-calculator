import pickle

def save_results(filename: str, results):
    with open(filename, 'wb') as f:
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


def load_results(filename: str):
    with open(filename, 'rb') as f:
        results = pickle.load(f)
    return results