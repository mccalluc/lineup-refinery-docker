import gzip
import requests
import os
import json
import sys
import logging

from io import BytesIO
from tabular import Tabular


def path_content_dict_from_env():
    '''
    >>> os.environ['INPUT_JSON'] = """
    ... {{"file_relationships": [
    ...    "{repo}/fixtures/fake.csv",
    ...    "{repo}/fixtures/abc.txt.gz"
    ... ]}}
    ... """.format(repo='https://raw.githubusercontent.com/refinery-platform/'
    ...                 'lineup-refinery-docker/v0.0.8')
    >>> d = path_content_dict_from_env()
    >>> d.keys()
    dict_keys(['fake.csv', 'abc.txt.gz'])
    >>> d['fake.csv']
    b'a,b,c\\n1,2,3\\n7,8,9'
    '''
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
    path_content_dict = {}
    for url in config["file_relationships"]:
        path = os.path.basename(url)
        while path in path_content_dict:
            path = 'duplicate_' + path
        path_content_dict[path] = requests.get(url).content
    return path_content_dict


def path_content_dict_from_argv():
    path_content_dict = {}
    for path in sys.argv[1:]:
        with open(path, 'rb') as f:
            path_content_dict[path] = f.read()
    return path_content_dict


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
    path_content_dict = path_content_dict_from_argv() if sys.argv[1:] \
        else path_content_dict_from_env()
    # "latin_1" seems likely to be correct... If it becomes an issue,
    # we could have another user supplied parameter.
    path_unzip_dict = {
        path: try_unzip(content).decode('latin_1')
        for (path, content) in path_content_dict.items()}
    tab = Tabular(path_unzip_dict.values())  # TODO
    print(tab.make_outside_data_js())
