import gzip
import requests
import os
import json
import sys
import logging

from io import BytesIO
from tabular import Tabular


def bin_contents_from_env():
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
    return [requests.get(url).content for url in config["file_relationships"]]


def bin_contents_from_argv():
    data = []
    for path in sys.argv[1:]:
        with open(path, 'rb') as f:
            data.append(f.read())
    return data


def try_unzip(bin_content):
    '''
    >>> abc_gz = b'\\x1f\\x8b\\x08\\x08\\x1c\\x84\\xd6Z\\x00\\x03abc.txt\\x00KLJ\\xe6\\x02\\x00N\\x81\\x88G\\x04\\x00\\x00\\x00'
    >>> try_unzip(abc_gz)
    b'abc\\n'
    >>> try_unzip(b'abc\\n')
    b'abc\\n'
    '''  # noqa
    try:
        with gzip.GzipFile(fileobj=BytesIO(bin_content)) as f:
            return f.read()
    except OSError:
        return bin_content


if __name__ == '__main__':
    bin_contents = bin_contents_from_argv() if sys.argv[1:] \
        else bin_contents_from_env()
    # "latin_1" seems likely to be correct... If it becomes an issue,
    # we could have another user supplied parameter.
    csvs = [try_unzip(file).decode('latin_1') for file in bin_contents]
    tab = Tabular(csvs)
    print(tab.make_outside_data_js())
