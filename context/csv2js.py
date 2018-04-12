import requests
import os
import json
import sys
import urllib
from csv import DictReader, Sniffer
import re


def csvs_from_env():
    input_json_envvar = os.environ.get("INPUT_JSON")
    input_json_url_envvar = os.environ.get("INPUT_JSON_URL")
    input_json_path = '/var/input.json'

    if input_json_envvar:
        input_json = input_json_envvar
    elif input_json_url_envvar:
        input_json = requests.get(input_json_url_envvar).text
    elif os.path.isfile(input_json_path):
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


def read_csvs(csvs, primary_key):
    '''
    Normal:
    >>> csv = 'a,c\\n1,2'
    >>> tsv = 'a\\tb\\n3\\t4'
    >>> data = read_csvs([csv, tsv], 'id')
    >>> data['header']
    ['a', 'b', 'c']
    >>> data['rows']
    [{'a': '1', 'c': '2', 'id': 0}, {'a': '3', 'b': '4', 'id': 1}]

    Single column:
    >>> csv = 'a\\n1\\n2'
    >>> read_csvs([csv], 'id')
    {'header': ['a'], 'rows': [{'a': '1', 'id': 0}, {'a': '2', 'id': 1}]}
    '''

    list_of_lists_of_dicts = []
    for csv in csvs:
        try:
            list_of_dicts = list(
                DictReader(csv.splitlines(), dialect=Sniffer().sniff(csv)))
        except:
            lines = csv.splitlines()
            key = lines[0]
            list_of_dicts = [{key: line} for line in lines[1:]]
        list_of_lists_of_dicts.append(list_of_dicts)
    key_sets = [l_of_d[0].keys()
                for l_of_d in list_of_lists_of_dicts]
    key_union = set()
    for s in key_sets:
        key_union.update(s)

    rows = [d for l_of_d in list_of_lists_of_dicts for d in l_of_d]
    id_rows = [{**d, **{primary_key: i}} for (i, d) in enumerate(rows)]
    return {
        'header': sorted(key_union),
        'rows': id_rows
    }


def get_raw_column(column, list_of_dicts):
    '''
    >>> get_raw_column('a', [{'a':'1'}])
    ['1']
    '''
    includes_nones = [d.get(column) for d in list_of_dicts]
    return [val for val in includes_nones if val is not None]


def get_typed_column(column, list_of_dicts):
    '''
    >>> get_typed_column('a', [{'a':'1'}])
    [1]
    >>> get_typed_column('a', [{'a':'1.1'}])
    [1.1]
    '''
    return [typed(s) for s in get_raw_column(column, list_of_dicts)]
    # TODO: could this be a generator?


def all_type(l, t):
    '''
    >>> all_type([1, 'one'], int)
    False
    >>> all_type([-1.1e-1], float)
    True
    >>> all_type([], int)
    True
    '''
    return all(type(x) == t for x in l)


def typed(s):
    '''
    >>> typed('1.1')
    1.1
    >>> typed('0')
    0
    >>> typed('z')
    'z'
    '''
    assert type(s) in [str]
    try:
        return int(s)
    except TypeError:  # None
        return None
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def make_column_defs(header, rows):
    '''
    >>> col_def = make_column_defs(
    ...     ['int', 'float', 'string', 'missing'],
    ...     [
    ...         {'int': '10', 'float': '10.1', 'string': 'ten', 'missing': 'x'},
    ...         {'int': '2', 'float': '2.1', 'string': 'two'}
    ...     ])
    >>> col_def[0]
    {'column': 'int', 'type': 'number', 'domain': [2, 10], 'numberFormat': 'd'}
    >>> col_def[1]
    {'column': 'float', 'type': 'number', 'domain': [2.1, 10.1], 'numberFormat': '.1f'}
    >>> col_def[2]
    {'column': 'string', 'type': 'string'}
    >>> col_def[3]
    {'column': 'missing', 'type': 'string'}
    '''  # noqa
    col_defs = []
    for col in header:
        col_def = {'column': col}
        values = get_typed_column(col, rows)
        if all_type(values, int):
            col_def['type'] = 'number'
            col_def['domain'] = [min(values), max(values)]
            col_def['numberFormat'] = 'd'  # TODO: confirm this is valid
        elif all_type(values, float):
            col_def['type'] = 'number'
            col_def['domain'] = [min(values), max(values)]
            col_def['numberFormat'] = '.1f'  # TODO: guess decimal points
        # TODO: Guess categorical strings?
        else:
            col_def['type'] = 'string'
        col_defs.append(col_def)
    return col_defs


def make_tsv(header, rows):
    '''
    Normal:
    >>> header = ['x', 'y']
    >>> rows = [{'x': '1', 'y': '2'}]
    >>> make_tsv(header, rows)
    'x\\ty\\n1\\t2'

    Handles missing columns:
    >>> header = ['x', 'y']
    >>> rows = [{'y': '2'}]
    >>> make_tsv(header, rows)
    'x\\ty\\n\\t2'
    '''

    header_line = '\t'.join(header)
    lines = [header_line]
    for row in rows:
        line = '\t'.join([row.get(h) or '' for h in header])
        lines.append(line)
    return '\n'.join(lines)


def make_outside_data_js(data, primary_key):
    '''
    >>> header = ['x']
    >>> rows = [{'x': '1'}]
    >>> data = {'header': header, 'rows': rows}
    >>> print(make_outside_data_js(data, 'x'))
    var outside_data = [
      {
        "desc": {
          "columns": [
            {
              "column": "x",
              "domain": [ 1, 1 ],
              "numberFormat": "d",
              "type": "number" } ],
          "primaryKey": "x",
          "separator": "\\t" },
        "id": "data",
        "name": "Data",
        "url": "data:text/plain;charset=utf-8,x%0A1" } ];
    '''

    column_defs = make_column_defs(data['header'], data['rows'])
    tsv_encoded = urllib.parse.quote(
        make_tsv(data['header'], data['rows']))
    outside_data = [{
        'id': 'data',
        'name': 'Data',
        'desc': {
            'separator': '\t',
            'primaryKey': primary_key,
            'columns': column_defs},
        'url': 'data:text/plain;charset=utf-8,{}'.format(tsv_encoded)
    }]
    outside_data_json = json.dumps(outside_data,
                                   ensure_ascii=True, sort_keys=True, indent=2)
    outside_data_json_compressed = \
        re.sub(r'\s+(?=\S)(?!["{])', ' ', outside_data_json)
    # Compress each line which does not being with '"' or '{'.
    return 'var outside_data = {};'.format(outside_data_json_compressed)


if __name__ == '__main__':
    csvs = csvs_from_argv() if sys.argv[1:] else csvs_from_env()
    primary_key = 'id'
    data = read_csvs(csvs, primary_key)
    js = make_outside_data_js(data, primary_key)
    print(js)
