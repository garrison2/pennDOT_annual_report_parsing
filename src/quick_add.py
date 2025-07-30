#! /usr/bin/env python
import json

with open("format.json") as file:
    format_dict = json.load(file)

for year in format_dict:
    categories = format_dict[year]['categories']
    categories = {'name':[None, None, None, None, None]} | categories
    format_dict[year]['categories'] = categories

with open("format_test.json", 'w') as file:
    json.dump(format_dict, file, indent=1)

