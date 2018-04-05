import requests
import os
import json
import sys
from csv import DictReader, Sniffer


def csvs_from_envvar():
    json = os.environ.get("INPUT_JSON")
    if json is None:
        url = os.environ.get("INPUT_JSON_URL")
        json = requests.get(url).text
    config = json.loads(json)

    return [requests.get(url).text for url in config["file_relationships"]]

def csvs_from_argv():
    data = []
    for path in sys.argv[1:]:
        with open(path) as f:
            data.append(f.read())
    return data

def read_csvs(csvs):
    list_of_lists_of_dicts = [
        list(DictReader(csv.splitlines(), dialect=Sniffer().sniff(csv)))
        for csv in csvs]
    key_sets = [list_of_dicts[0].keys()
                for list_of_dicts in list_of_lists_of_dicts]
    return key_sets

if __name__ =="__main__":
    csvs = csvs_from_argv() if sys.argv[1:] else csvs_from_envvar()
    union = read_csvs(csvs)
    print(union)

