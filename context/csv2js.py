import requests
import os
import json
import sys
import logging

from tabular import Tabular


def csvs_from_env():
    input_json_envvar = os.environ.get("INPUT_JSON")
    input_json_url_envvar = os.environ.get("INPUT_JSON_URL")
    input_json_path = '/var/input.json'

    logging.basicConfig(level=logging.INFO)
    if input_json_envvar:
        logging.info('Reading from envar')
        input_json = input_json_envvar
    elif input_json_url_envvar:
        logging.info('Reading from url from envar')
        input_json = requests.get(input_json_url_envvar).text
    elif os.path.isfile(input_json_path):
        logging.info('Reading from local file')
        with open(input_json_path) as f:
            input_json = f.read()
    else:
        # Even if there is an error, we need to express that in the
        # response, somehow, so the JS can present it to the user.
        return ['data\nmissing']

    config = json.loads(input_json)
    return [requests.get(url).text for url in config["file_relationships"]]


def csvs_from_argv():
    data = []
    for path in sys.argv[1:]:
        with open(path) as f:
            data.append(f.read())
    return data


if __name__ == '__main__':
    csvs = csvs_from_argv() if sys.argv[1:] else csvs_from_env()
    tab = Tabular(csvs)
    print(tab.make_outside_data_js())
