#! /usr/bin/env python
import os, sys, json, re
import pdfplumber

import textwrap, shutil

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

REPORTS_DIR = os.getenv("REPORTS_DIR")
FORMAT_JSON = os.getenv("FORMAT_JSON")
PARSED_JSON = os.getenv("PARSED_JSON")
TMP_JSON = os.getenv("TMP_JSON")
REPORT_NAME_FORMAT = os.getenv("REPORT_NAME_FORMAT")
YEAR_START = os.getenv("YEAR_START")
YEAR_END = os.getenv("YEAR_END")

BOXES = [ 'lbox', 'rbox', 'tbox', 'lchart', 'rchart' ]

class TextNotFoundError(Exception):
    def __init__(self, pattern, search_text):
        message = (f'{repr(pattern)}\n{repr(search_text)}')
        super().__init__(message)

# -------------- HELPER --------------
def clean(val):
    if isinstance(val, list):
        if len(val) != 1:
            val = [ clean(v) for v in val ]
            return val
        else:
            val = val[0]
    return val
#    return int(val) if val.isdigit() else val
# ------------------------------------

# ------------- CLEANING --------------
def fix_offset(i, offset, pdf, meta, categories):
    offset += 2
    print(f'offset: {offset}')
    print(f'page: {i}')
    print(f'new page: {i - offset}')

    page = pdf.pages[i - 1 - offset]
    box_text = get_box_text(page, meta)

    ts_boxes = meta.get('method', dict()).get('text_scrape')
    if ts_boxes is None: ts_boxes = ['lbox', 'rbox']
    index = get_lrbox_index(box_text, ts_boxes, categories)

    meta['PPA_exception'] = meta.get('PPA_exception', dict())
    meta['PPA_exception'][str(i - meta['Pages Per Agency'])] = 2
    return offset, page, box_text, index

def except_page(meta, page, i):
    if not meta.get('except'): return False
    page_text = page.extract_text()

    for val in meta['except']:
        if isinstance(val, int) and i == val:
            return True
        if isinstance(val, str) and val in page_text:
            return True
    return False
# ------------------------------------

def get_format_dict():
    with open(FORMAT_JSON, "r") as file:
        format_dict = json.load(file)

    if os.path.exists(TMP_JSON):
        open_tmp = input("Open tmp format file? (y/n) ")
        if open_tmp == 'y':
            with open(TMP_JSON, "r") as file:
                format_dict = json.load(file)
    return format_dict

def write_to_file(dict_dump, filepath):
    with open(filepath, 'w') as file:
        json.dump(dict_dump, file, indent=1)

def change_year_format(format_dict, year, prior):
    if prior not in format_dict: return format_dict[year]

    for category in format_dict[year]['categories']:
        cbase = format_dict[year]['categories'][category]
        pbase = format_dict[prior]['categories'][category]
        for item in cbase:
            if item == 'subheadings': continue
            if not cbase[item]:
                cbase[item] = pbase.get(item)

        if 'subheadings' in cbase:
            sbase = cbase['subheadings']
            psbase = pbase.get('subheadings', dict())
            for subheading in sbase:
                if subheading is None:
                    sbase[subheading] = psbase.get(subheading)
                else:
                    for item in sbase[subheading]:
                        item_val = sbase[subheading][item]
                        if not item_val:
                            sbase[subheading][item] = psbase.get(subheading, dict()).get(item, item_val)

    write_to_file(format_dict, TMP_JSON)

def get_agency_range(meta):
    pages_per_agency = int(meta["Pages Per Agency"])
    exceptions = meta.get('PPA_exception', dict())

    all_start = meta.get('All Start')
    all_end = meta.get('All End')
    if all_start and all_end:
        ranges = [[all_start, all_end, pages_per_agency]]
    else:
        index0 = int(meta["Urban Systems (Start Page)"])
        index1 = int(meta["Rural Systems (Start Page)"])
        index2 = int(meta["Shared Ride (Start Page)"])

        ranges = [[index0, index1 - 2, pages_per_agency], 
                  [index1, index2 - 2, pages_per_agency]]

    i = 0
    for except_start in sorted(int(e) for e in exceptions.keys()):
        except_step = exceptions[str(except_start)]
        except_end = except_start + except_step

        while(i < len(ranges) and ranges[i][0] < except_start):
            i += 1

        if i != 0 and ranges[i-1][1] > except_end:
            original_end = ranges[i-1][1]
            ranges[i-1][1] = except_start
            ranges.insert(i, [except_start, except_end, except_step])
            ranges.insert(i+1, [except_end, original_end, ranges[i-1][2]])
        else:
            ranges.insert(i, [except_start, except_end, except_step])
            ranges[i+1][0] = except_end

    expanded_ranges = []
    for r in ranges:
        expanded_ranges += list(range(*r))

    return expanded_ranges

def get_box_text(page, meta) -> dict:
    box_text = dict()
    for box in meta['boxes']:
        dimensions = meta['boxes'][box]
        box_text[box] = page.crop(dimensions).extract_text()
    return box_text

def get_lrbox_index(box_text, boxes, categories) -> dict:
#    tmp_index = {'lbox':[], 'rbox':[]}
    tmp_index = { box:[] for box in boxes }
               
    for category in categories:
        box = categories[category]['box']
        if box != 'lbox' and box != 'rbox': continue

        search_text = box_text[box]
        pattern = categories[category]['name']
        if pattern is None:
            continue

        search = re.search(pattern, search_text, flags=re.DOTALL)
        if search:
            tmp_index[box].append((category, search.end()))
            continue

        raise TextNotFoundError(pattern, search_text)

    for box in tmp_index:
        tmp_index[box].sort(key=lambda x:x[1])

#    index = {'lbox':dict(), 'rbox':dict()}
    index = { box:dict() for box in boxes }
    for box in index:
        tmp_box = tmp_index[box]
        for i in range(len(tmp_box) - 1):
            name, start = tmp_box[i]
            end = tmp_box[i + 1][1]
            index[box][name] = (start, end)
        name, start = tmp_box[len(tmp_box) - 1]
        end = len(box_text[box])
        index[box][name] = (start, end)

    return index

def match_lrbox(cbase, text, start, end, silent = False):
    vals = dict()
    for subcat in cbase['subheadings']:
        scbase = cbase['subheadings'][subcat]
        if scbase['name'] == '': continue

        pattern = f"^{scbase['name'].upper()}.*$"
        search = re.search(pattern, text[start:end].upper(), re.MULTILINE)
        if search:
            tmp = text[start:end][search.start():search.end()]
            tmp = tmp[len(scbase['name']):]
            tmp = tmp.strip()
            tmp = tmp.split(scbase['delim'])
            tmp = [ r.strip() for r in tmp[1:] ] if len(tmp) > 1 else tmp
            vals[subcat] = clean(tmp)
        else:
            vals[subcat] = "_"
            if silent: continue
            err_text = textwrap.wrap(repr(text[start:end]),
                                     shutil.get_terminal_size()[0] - 16, 
                                     initial_indent='\t\t',
                                     subsequent_indent='\t\t')
            print(f'\tNot Found: {subcat} | {repr(scbase['name'])}')
            for line in err_text:
                print(line)

    if cbase['delim'] is not None:
        search = re.search(cbase['name'], text[start:end])
        if search:
            tmp = search.split(scbase['delim'])
            vals[subcat] = clean(tmp)



    return vals

def main(start = None):
    format_dict = get_format_dict()
    if os.path.exists(PARSED_JSON):
        with open(PARSED_JSON, 'r') as file: results = json.load(file)
    else:
        results = dict()

    csvs = dict()

    start = start if start else int(YEAR_START)
    end = int(YEAR_END) + 1

    for y in range(start, end):
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        change_year_format(format_dict, year, prior)

        meta = format_dict[year]['meta']
        categories = format_dict[year]['categories']

        results[year] = dict()

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)

            print(f'Year: {year}')

            offset = 0
            print(get_agency_range(meta))
            for i in get_agency_range(meta):
                page = pdf.pages[i - 1 - offset]
                if except_page(meta, page, i):
                    continue

                box_text = get_box_text(page, meta)

                ts_boxes = meta.get('method', dict()).get('text_scrape')
                if ts_boxes is None: ts_boxes = ['lbox', 'rbox']

                try:
                    index = get_lrbox_index(box_text, ts_boxes, categories)
                except TextNotFoundError as e:
                    print(get_agency_range(meta))
                    tmp = fix_offset(i, offset, pdf, meta, categories)
                    offset, page, box_text, index = tmp
                    write_to_file(format_dict, TMP_JSON)

                name = None
                vals = dict()
                for category in categories:
                    cbase = categories[category]
                    if cbase['name'] == '': continue

                    silent = False
                    if meta.get('silent') and category in meta['silent']:
                        silent = True

                    match cbase['box']:
                        case 'tbox':
                            name = box_text['tbox'].replace("\n", " ")
                            print(name)
                        case 'lchart' | 'rchart':
                            pass
                        case _:
                            try:
                                text = box_text[cbase['box']]
                                start, end = index[cbase['box']][category]
                            except KeyError as e:
                                print(f'box_text: {box_text}')
                                print(f'cbase: {cbase}')
                                print(f'page: {i}')
                                raise e

                            vals |= match_lrbox(cbase, text, start, end,
                                                silent = silent)

                results[year][name] = vals
                write_to_file(results, PARSED_JSON)

if __name__ == '__main__':
    start = None
    if len(sys.argv) == 3 and sys.argv[1] == 'year':
        start = int(sys.argv[2])
    main(start)
