#!/usr/bin/env sh

python ../csv2js.py $* > outside_data.js
python -m http.server 80
