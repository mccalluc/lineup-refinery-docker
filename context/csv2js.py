import requests
import os
import json
import sys
import urllib
from csv import DictReader, Sniffer


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


def get_column(column, list_of_dicts):
    '''
    >>> get_column('a', [{'a':1}, {'b':2}])
    [1, None]
    '''
    return [d.get(column) for d in list_of_dicts]


def all_numbers(l):
    '''
    >>> all_numbers(['1','one'])
    False
    >>> all_numbers(['-1.1e-1'])
    True
    >>> all_numbers([])
    True
    '''
    return all([is_number(x) for x in l if x is not None])


def is_number(s):
    '''
    >>> is_number('1')
    True
    >>> is_number('z')
    False
    '''
    if s is None:
        return None
    try:
        float(s)
        return True
    except ValueError:
        return False


def make_column_def(header, rows):
    '''
    >>> make_column_def(['x', 'y'], [{'x': '1'}, {'y': 'one'}])
    [{'column': 'x', 'type': 'number'}, {'column': 'y', 'type': 'string'}]
    '''
    column_def = []
    for col in header:
        col_type = 'number' if all_numbers(get_column(col, rows)) else 'string'
        column_def.append({'column': col, 'type': col_type})
    return column_def


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
    <BLANKLINE>
    var outside_data = [
      {
        id: "data",
        name: "Data",
        desc: { separator:"\\t", primaryKey:"x", columns:[{"column": "x", "type": "number"}] },
        url: "data:text/plain;charset=utf-8,x%0A1"
      }
    ];
    <BLANKLINE>
    '''  # noqa: E501

    column_def_json = json.dumps(make_column_def(data['header'], data['rows']))
    tsv_encoded = urllib.parse.quote(make_tsv(data['header'], data['rows']))
    return '''
var outside_data = [
  {{
    id: "data",
    name: "Data",
    desc: {{ separator:"\\t", primaryKey:"{}", columns:{} }},
    url: "data:text/plain;charset=utf-8,{}"
  }}
];
'''.format(primary_key, column_def_json, tsv_encoded)


if __name__ == '__main__':
    csvs = csvs_from_argv() if sys.argv[1:] else csvs_from_env()
    primary_key = 'id'
    data = read_csvs(csvs, primary_key)
    js = make_outside_data_js(data, primary_key)
    print(js)
