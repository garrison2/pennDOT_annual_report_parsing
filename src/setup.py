#! /usr/bin/env python
from enum import Enum
import json, os, subprocess, shlex
import pdfplumber

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

class ReturnType(Enum):
    SHOW = 1
    DRAW = 2
    CROP = 3
    RETURN = 4
    ERROR = 5

    LBOX = 6
    RBOX = 7
    TBOX = 8
    LCHART= 9
    RCHART = 10

REPORTS_DIR = os.getenv("REPORTS_DIR")
FORMAT_JSON = os.getenv("FORMAT_JSON")
REPORT_NAME_FORMAT = os.getenv("REPORT_NAME_FORMAT")
YEAR_START = os.getenv("YEAR_START")
YEAR_END = os.getenv("YEAR_END")

remap = lambda x: [x[0], x[2], x[1], x[3]]

boxes = { 'lbox', 'rbox', 'tbox', 'lchart', 'rchart' }

# -------------- HELPER --------------
def print_help():
    return
    print("top:+/- [num] to move top line\n"
          "bot:+/- [num] to move bottom line\n"
          "mid:+/- [num] to move mid line\n"
          "exit to exit\n"
          "h for this help\n"
          )

def write_to_tmp(dict_dump):
    with open('tmp.json', 'w') as file:
        json.dump(dict_dump, file, indent=1)

def verify_nums(vals):
    x0, y0, x1, y1 = vals
    if (x0 < 0 or x1 <= x0 or y0 < 0 or y1 <= y0):
        print("\nError! Bounding box violates page dimensions.")
        return False

    print(y0, y1, y1 <= y0)
    return True
# ------------------------------------

def process_input(usr_input, lbox, rbox, tbox, lchart, rchart):
    if usr_input == 'h' :
        print_help()
        return { ReturnType.ERROR }
    if usr_input == 'exit':
        exit(0)
    if usr_input == 'crop':
        return { ReturnType.CROP } 
    if usr_input == 'return':
        return { ReturnType.RETURN, ReturnType.SHOW }

    args = shlex.split(usr_input)
    if len(args) < 3:
        print(f"Invalid number of arguments ({len(args)}).")
        return { ReturnType.ERROR } 

    if args[0] == 'lbox' or args[0] == 'l':
        dimensions = lbox
    elif args[0] == 'rbox' or args[0] == 'r':
        dimensions = rbox
    elif args[0] == 'tbox' or args[0] == 't':
        dimensions = tbox
    elif args[0] == 'lchart' or args[0] == 'lc':
        dimensions = lchart
    elif args[0] == 'rchart' or args[0] == 'rc':
        dimensions = rchart
    else:
        print(f'Invalid selector "{args[0]}.". Must be lbox or rbox.')
        return { ReturnType.ERROR }

    if args[1] == '[' and args[-1] == ']':
        vals = args[2:-1]
        if not all(v.isdigit() for v in vals):
            print("Invalid input: could not parse for dimensions.")
            return { ReturnType.ERROR }

        vals = remap([int(v) for v in vals])
        if not verify_nums(vals): return { ReturnType.ERROR }
        for i in range(4):
            dimensions[i] = vals[i]
        return { ReturnType.DRAW, ReturnType.SHOW }

    else:
        d_map = {'x0':0, 'x1':2, 'y0':1, 'y1':3}

        if d_map.get(args[1]) is None:
            print(f'Invalid selector: "{args[1]}. Must be x0, x1, y0, or y1.')
            return { ReturnType.ERROR }

        if args[2] == '+':
            delta = 1
        elif args[2] == '-':
            delta = -1
        elif args[2].isdigit():
            tmp = dimensions[d_map[args[1]]]
            dimensions[d_map[args[1]]] = int(args[2])

            if verify_nums(dimensions): 
                return { ReturnType.DRAW, ReturnType.SHOW }
            else:
                dimensions[d_map[args[1]]] = tmp
                return { ReturnType.ERROR }

        else:
            print(f'Invalid selector "{args[2]}. Must be +/-.')
            return { ReturnType.ERROR }

        if len(args) < 4:
            print(f"Invalid number of arguments ({len(args)}). Expecting 4.")
            return { ReturnType.ERROR }

        if not args[3].isdigit():
            print("Invalid input: could not parse for integer.")
            return { ReturnType.ERROR }

        tmp = dimensions[d_map[args[1]]]
        dimensions[d_map[args[1]]] += delta * int(args[3])

        if verify_nums(dimensions): 
            return { ReturnType.DRAW, ReturnType.SHOW }
        else:
            dimensions[d_map[args[1]]] = tmp
            return { ReturnType.ERROR }


        return { ReturnType.DRAW, ReturnType.SHOW }
        
def loop(page, current_dict, prior_dict):
    if current_dict['meta']['lbox']:

    if current_dict['meta']['lbox']:

    # turn lbox, rbox, tbox, lchart, rchart into an object, 
    # figure out how to get prior and current from the ojbect


    top = 0
    bottom = int(page.height)
    left = 0
    right = int(page.width)
    mid_x = int((right + left) / 2)
    mid_y = int((top + bottom) / 2)

    lbox = [left, top, mid_x, mid_y]
    rbox = [mid_x, top, right, mid_y]
    tbox = [left, top, right, mid_y]
    lchart = [left, mid_y, mid_x, bottom]
    rchart = [mid_x, mid_y, right, bottom]

    print_help()

    status = { ReturnType.DRAW, ReturnType.SHOW }

    while True:
        if ReturnType.SHOW in status:
            print()
            print(f'lbox:   [ {" ".join(str(r) for r in remap(lbox))} ]\n'
                  f'rbox:   [ {" ".join(str(r) for r in remap(rbox))} ]\n'
                  f'tbox:   [ {" ".join(str(r) for r in remap(tbox))} ]\n'
                  f'lchart: [ {" ".join(str(r) for r in remap(lchart))} ]\n'
                  f'rchart: [ {" ".join(str(r) for r in remap(rchart))} ]')

        if ReturnType.DRAW in status:
            try:
                im = page.to_image(resolution=150)
                im.draw_rect(tuple(lbox))
                im.draw_rect(tuple(rbox))
                im.draw_rect(tuple(tbox))
                im.draw_rect(tuple(lchart))
                im.draw_rect(tuple(rchart))
                im.show()
            except ValueError as e:
                print("\nError! Bounding box violates page dimensions.")

        usr_input = input("\n>> ")
        status = process_input(usr_input, lbox, rbox, tbox, lchart, rchart)

        if ReturnType.CROP in status:
            try:
                lcrop = page.crop(lbox)
                rcrop = page.crop(rbox)
                tcrop = page.crop(tbox)
                lccrop = page.crop(lchart)
                rccrop = page.crop(rchart)
            except ValueError as e:
                print("\nError! Bounding box violates page dimensions.")
            else:
                print(lcrop.extract_text())
                print(rcrop.extract_text())
                print(tcrop.extract_text())
                print(rccrop.extract_text())
                print(lccrop.extract_text())

        if ReturnType.RETURN in status:
            return {'lbox':lbox, 'rbox':rbox, 'tbox':tbox,
                    'lchart':lchart, 'rchat':rchart}

def main():
    with open(FORMAT_JSON, 'r') as file:
        format_dict = json.load(file)

    for y in range(int(YEAR_START), int(YEAR_END) + 1):
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        if (format_dict[year]['meta']['lbox'] and 
            format_dict[year]['meta']['rbox'] and 
            format_dict[year]['meta']['tbox'] and 
            format_dict[year]['meta']['lchart'] and 
            format_dict[year]['meta']['rchart']):
            continue

        pagenum = format_dict[year]['meta']["Urban Systems (Start Page)"]

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)
            page = pdf.pages[pagenum - 1]

            print(f'Year: {year}')

            result = loop(page, format_dict[year], format_dict.get[prior])

        format_dict[year]['meta'] |= result
        write_to_tmp(format_dict)


if __name__ == '__main__':
    main()
