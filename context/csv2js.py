import requests
import os
import json
import sys
import urllib
from csv import DictReader, Sniffer, Error
import re
from math import log2


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


PRIMARY_KEY = 'id'


class Tabular():

    def __init__(self, csvs=None,
                 # header and rows kwargs are just for making
                 # unit tests more clear.
                 header=None, rows=None):
        '''
        Preserve order:
        >>> csv = 'q,u,i,c,k,b,r,o,w,n\\n1,2,3,4,5,6,7,8,9,10'
        >>> tabular = Tabular([csv])
        >>> ''.join(tabular.header)
        'quickbrown'

        # TODO:
        # Preserve order with sparse data:
        # >>> csv = 'q,u,i,c,k,b,r,o,w,n\\n,,,,X\\n,,Y'
        # >>> tabular = Tabular([csv])
        # >>> ''.join(tabular.header)
        # 'quickbrown'

        Merge files:
        >>> csv = 'z,c\\n1,2'
        >>> tsv = 'z\\tb\\n3\\t4'
        >>> tabular = Tabular([csv, tsv])
        >>> tabular.header
        ['z', 'c', 'b']
        >>> tabular.rows
        [{'z': '1', 'c': '2', 'id': 0}, {'z': '3', 'b': '4', 'id': 1}]

        Longer column:
        >>> csv = 'a\\nx\\ny\\nz'
        >>> tabular = Tabular([csv])
        >>> tabular.header
        ['a']
        >>> tabular.rows
        [{'a': 'x', 'id': 0}, {'a': 'y', 'id': 1}, {'a': 'z', 'id': 2}]
        '''
        if csvs is None:
            self.header = header
            self.rows = rows
            return
        list_of_lists_of_dicts = []
        for csv in csvs:
            try:
                list_of_dicts = list(
                    DictReader(csv.splitlines(), dialect=Sniffer().sniff(csv)))
            except Error as e:
                assert str(e) == 'Could not determine delimiter'
                # Perhaps because it is a single column... Treat it that way.
                lines = csv.splitlines()
                key = lines[0]
                list_of_dicts = [{key: line} for line in lines[1:]]
            list_of_lists_of_dicts.append(list_of_dicts)

        self.header = []
        for l_of_d in list_of_lists_of_dicts:
            for k in l_of_d[0].keys():
                if k not in self.header:
                    self.header.append(k)

        dict_rows = [d for l_of_d in list_of_lists_of_dicts
                     for d in l_of_d]
        id_rows = [{**d, **{PRIMARY_KEY: i}}
                   for (i, d) in enumerate(dict_rows)]
        self.rows = id_rows

    def make_outside_data_js(self):
        '''
        >>> csv = 'a\\n1'
        >>> tabular = Tabular([csv])
        >>> print(tabular.make_outside_data_js())
        var outside_data = [
          {
            "desc": {
              "columns": [
                {
                  "column": "a",
                  "domain": [ 1, 1 ],
                  "numberFormat": "d",
                  "type": "number" } ],
              "primaryKey": "id",
              "separator": "\\t" },
            "id": "data",
            "name": "Data",
            "url": "data:text/plain;charset=utf-8,a%0A1" } ];
        '''

        column_defs = self._make_column_defs()
        tsv_encoded = urllib.parse.quote(self._make_tsv())
        outside_data = [{
            'id': 'data',
            'name': 'Data',
            'desc': {
                'separator': '\t',
                'primaryKey': PRIMARY_KEY,
                'columns': column_defs},
            'url': 'data:text/plain;charset=utf-8,{}'.format(tsv_encoded)
        }]
        outside_data_json = json.dumps(outside_data,
                                       ensure_ascii=True, sort_keys=True,
                                       indent=2)
        outside_data_json_compressed = \
            re.sub(r'\s+(?=\S)(?!["{])', ' ', outside_data_json)
        # Compress each line which does not being with '"' or '{'.
        return 'var outside_data = {};'.format(outside_data_json_compressed)

    def _make_column_defs(self):
        '''
        >>> tab = Tabular(
        ...    header=['int', 'float', 'string', 'missing'],
        ...    rows=[
        ...         {'int': '10', 'float': '10.1', 'string': 'ten', 'missing': 'x'},
        ...         {'int': '2', 'float': '2.1', 'string': 'two'}
        ...     ])
        >>> col_def = tab._make_column_defs()
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
        for col in self.header:
            col_def = {'column': col}
            values = get_typed_column(col, self.rows)
            if all_type(values, int):
                col_def['type'] = 'number'
                col_def['domain'] = [min(values), max(values)]
                col_def['numberFormat'] = 'd'  # TODO: confirm this is valid
            elif all_type(values, float):
                col_def['type'] = 'number'
                col_def['domain'] = [min(values), max(values)]
                col_def['numberFormat'] = '.1f'  # TODO: guess decimal points
            elif is_categorical(values):
                col_def['type'] = 'categorical'
            else:
                col_def['type'] = 'string'
            col_defs.append(col_def)
        return col_defs

    def _make_tsv(self):
        '''
        Normal:
        >>> tab = Tabular(
        ...    header=['x', 'y'],
        ...    rows=[{'x': '1', 'y': '2'}])
        >>> tab._make_tsv()
        'x\\ty\\n1\\t2'

        Handles missing columns:
        >>> tab = Tabular(
        ...    header=['x', 'y'],
        ...    rows=[{'y': '2'}])
        >>> tab._make_tsv()
        'x\\ty\\n\\t2'
        '''

        header_line = '\t'.join(self.header)
        lines = [header_line]
        for row in self.rows:
            line = '\t'.join([row.get(h) or '' for h in self.header])
            lines.append(line)
        return '\n'.join(lines)


def is_categorical(values):
    '''
    Smaller sets can have proportionally more diversity than larger sets.

    >>> is_categorical([1,1,2,2])
    False
    >>> is_categorical([1,1,2,2,2])
    True

    >>> is_categorical([1,1,2,2,3,3,3,3])
    False
    >>> is_categorical([1,1,2,2,3,3,3,3,3])
    True

    >>> is_categorical(range(100))
    False
    >>> is_categorical(['x' for i in range(100)] + list(range(100)))
    True

    It gets confused if a lot of uniform data leads the list...
    Might be premature optimization?
    '''
    return len(set(values[:100])) < log2(len(values))


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
    assert type(s) == str
    try:
        return int(s)
    except TypeError:  # None
        return None
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


if __name__ == '__main__':
    csvs = csvs_from_argv() if sys.argv[1:] else csvs_from_env()
    tab = Tabular(csvs)
    print(tab.make_outside_data_js())
