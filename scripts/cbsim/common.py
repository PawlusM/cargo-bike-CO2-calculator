import pickle, json


def save_results(filename: str, results):
    with open(filename, 'wb') as f:
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


def load_results(filename: str):
    with open(filename, 'rb') as f:
        results = pickle.load(f)
    return results


def load_dict_from_json(filename):
    with open(filename, 'r') as file:
        dict = json.load(file)
    return dict


def save_dict_to_json(dict, filename):
    with open(filename, 'a') as file:
        file.write(json.dumps(dict))
