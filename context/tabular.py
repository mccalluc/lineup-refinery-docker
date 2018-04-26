import urllib
from csv import DictReader, Sniffer, Error
import json
import re
from math import log2

PRIMARY_KEY = 'id'


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
    >>> is_categorical(['x'] * 100 + list(range(100)))
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


def parse_to_dicts(csv):
    '''
    >>> gtc = '\\n'.join(['#1.2', '1\\t1', 'NAME\\tDESCRIPTION\\tfoo',
    ...                   'a\\tb\\tc'])
    >>> lod = parse_to_dicts(gtc)
    >>> lod[0]
    OrderedDict([('NAME', 'a'), ('DESCRIPTION', 'b'), ('foo', 'c')])
    '''
    lines = csv.splitlines()
    if lines[0] == '#1.2':
        # GTC format:
        # http://software.broadinstitute.org/cancer/software/genepattern/file-formats-guide#GCT
        lines = lines[2:]
    dialect = Sniffer().sniff('\n'.join(lines[:10]))
    return list(DictReader(lines, dialect=dialect))


def add_k_v_to_each(k, v, list_of_dicts):
    '''
    >>> l_of_d = [{'a': 1}, {'a': 2}]
    >>> add_k_v_to_each('path', 'fake.csv', l_of_d)
    [{'a': 1, 'path': 'fake.csv'}, {'a': 2, 'path': 'fake.csv'}]
    '''
    for d in list_of_dicts:
        d[k] = v
    return list_of_dicts

FILE_COLUMN = 'Refinery file'


class Tabular():

    def __init__(self, path_data_dict=None,
                 # header and rows kwargs are just for making
                 # unit tests more clear.
                 header=None, rows=None):
        '''
        Preserve order:
        >>> csv = 'q,u,i,c,k,b,r,o,w,n\\n1,2,3,4,5,6,7,8,9,10'
        >>> tabular = Tabular({'fake.csv': csv})
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
        >>> tabular = Tabular({'fake.csv': csv, 'fake.tsv': tsv})
        >>> tabular.header
        ['z', 'c', 'Refinery file', 'b']
        >>> tabular.rows[0]
        {'z': '1', 'c': '2', 'Refinery file': 'fake.csv', 'id': 0}
        >>> tabular.rows[1]
        {'z': '3', 'b': '4', 'Refinery file': 'fake.tsv', 'id': 1}

        If source data has a "Refinery file" column, it gets clobbered.)
        >>> csv = 'Refinery file,c\\n1,2'
        >>> tsv = 'Refinery file\\tb\\n3\\t4'
        >>> tabular = Tabular({'fake.csv': csv, 'fake.tsv': tsv})
        >>> tabular.header
        ['Refinery file', 'c', 'b']
        >>> tabular.rows[0]
        {'Refinery file': 'fake.csv', 'c': '2', 'id': 0}
        >>> tabular.rows[1]
        {'Refinery file': 'fake.tsv', 'b': '4', 'id': 1}

        Longer column:
        >>> csv = 'a\\nx\\ny\\nz'
        >>> tabular = Tabular({'fake.csv': csv})
        >>> tabular.header
        ['a']
        >>> tabular.rows[0]
        {'a': 'x', 'id': 0}
        >>> tabular.rows[1]
        {'a': 'y', 'id': 1}
        >>> tabular.rows[2]
        {'a': 'z', 'id': 2}

        # Missing header values:
        # >>> csv = 'a,b,c,d,\\n1,2,3,4,\\n1,2,3,4,5'
        # >>> tabular = Tabular([csv])
        # >>> tabular.header
        # ['a', 'c']
        # >>> tabular.rows
        # [{'a': '1', 'c': '3', 'id': 0}]
        '''
        if path_data_dict is None:
            self.header = header
            self.rows = rows
            return
        dict_of_lists_of_dicts = {}
        for path, csv in path_data_dict.items():
            try:
                list_of_dicts = parse_to_dicts(csv)
            except Error as e:
                assert str(e) == 'Could not determine delimiter'
                # Perhaps because it is a single column... Treat it that way.
                lines = csv.splitlines()
                key = lines[0]
                list_of_dicts = [{key: line} for line in lines[1:]]
            # If there is only one file, we don't need
            # an extra column to distinguish it.
            if len(path_data_dict) > 1:
                add_k_v_to_each(FILE_COLUMN, path, list_of_dicts)
            dict_of_lists_of_dicts[path] = list_of_dicts

        self.header = []
        for l_of_d in dict_of_lists_of_dicts.values():
            for k in l_of_d[0].keys():
                if k not in self.header:
                    self.header.append(k)

        dict_rows = [d for l_of_d in dict_of_lists_of_dicts.values()
                     for d in l_of_d]
        id_rows = [{**d, **{PRIMARY_KEY: i}}
                   for (i, d) in enumerate(dict_rows)]
        self.rows = id_rows

    def make_outside_data_js(self):
        '''
        >>> csv = 'a\\n1'
        >>> tabular = Tabular({'fake.csv': csv})
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
