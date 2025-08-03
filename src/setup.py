#! /usr/bin/env python
from enum import Enum
import json, os, subprocess, shlex, sys
import pdfplumber

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

REPORTS_DIR = os.getenv("REPORTS_DIR")
FORMAT_JSON = os.getenv("FORMAT_JSON")
TMP_JSON = os.getenv("TMP_JSON")
REPORT_NAME_FORMAT = os.getenv("REPORT_NAME_FORMAT")
YEAR_START = os.getenv("YEAR_START")
YEAR_END = os.getenv("YEAR_END")

BOXES = [ 'lbox', 'rbox', 'tbox', 'lchart', 'rchart' ]
remap = lambda x: [x[0], x[2], x[1], x[3]]

class ReturnType(Enum):
    SHOW = 1
    DRAW = 2
    CROP = 3
    RETURN = 4
    ERROR = 5
    PAGE = 6

    LBOX = 101
    RBOX = 102
    TBOX = 103
    LCHART= 104
    RCHART = 1105

class Boxes:
    def __init__(self, page, current, prior):
        top = 0
        bottom = int(page.height)
        left = 0
        right = int(page.width)
        mid_x = int((right + left) / 2)
        mid_y = int((top + bottom) / 2)

        self.lbox = [left, top, mid_x, mid_y]
        self.rbox = [mid_x, top, right, mid_y]
        self.tbox = [left, top, right, mid_y]
        self.lchart = [left, mid_y, mid_x, bottom]
        self.rchart = [mid_x, mid_y, right, bottom]

        if prior:
            for box in BOXES:
                for i in range(4):
                    if prior['categories'][box][i] is not None:
                        setattr(self, box, prior['categories'][box])

        self.exists = True
        for box in BOXES:
            for i in range(4):
                if current['categories'][box][i] is None:
                    self.exists = False
                else:
                    getattr(self, box)[i] == current['categories'][box][i]

    def print(self):
        for box in BOXES:
            val = getattr(self, box)
            print(f'{box}: [ {" ".join(str(r) for r in remap(val))} ]')

# -------------- HELPER --------------

def get_format_dict():
    with open(FORMAT_JSON, "r") as file:
        format_dict = json.load(file)

    if os.path.exists(TMP_JSON):
        open_tmp = input("Open tmp format file? (y/n) ")
        if open_tmp == 'y':
            with open(TMP_JSON, "r") as file:
                format_dict = json.load(file)
    return format_dict

def print_help():
    print(
          "h, help\t\t\t\t to print this help\n"
          "exit\t\t\t\t to exit\n"
          "c, crop\t\t\t\t to output the cropped text\n"
          "R, return\t\t\t to save the result to tmp and continue\n"
          "P, page\t\t\t\t to view the next agency's page\n"
          "<box> <dimension> [+/-] <num>\t to set/change one dimension\n"
          "<box> [ x0 x1 y0 y1 ]\t\t to set all dimensions\n"
          "\n"
          "<box> can be lbox, rbox, tbox, lchart, rchart\n"
          "<dimensions> can be x0, x1, y0, y1"
          )
    return

def write_to_tmp(dict_dump):
    with open(TMP_JSON, 'w') as file:
        json.dump(dict_dump, file, indent=1)

def verify_nums(vals):
    x0, y0, x1, y1 = vals
    if (x0 < 0 or x1 <= x0 or y0 < 0 or y1 <= y0):
        print("\nError! Bounding box violates page dimensions.")
        return False

    return True
# ------------------------------------

def process_input(usr_input, boxes): # lbox, rbox, tbox, lchart, rchart):
    if usr_input == 'h' or usr_input == 'help':
        print_help()
        return { ReturnType.ERROR }
    if usr_input == 'exit':
        exit(0)
    if usr_input == 'c' or usr_input == 'crop':
        return { ReturnType.CROP } 
    if usr_input == 'R'or usr_input == 'return':
        return { ReturnType.RETURN, ReturnType.SHOW }
    if usr_input == 'P' or usr_input == 'page':
        return { ReturnType.PAGE, ReturnType.DRAW }

    args = shlex.split(usr_input)
    if len(args) < 3:
        print(f"Invalid number of arguments Expected 3, given {len(args)}.")
        return { ReturnType.ERROR } 

    if args[0] == 'lbox' or args[0] == 'l':
        name = 'lbox'
    elif args[0] == 'rbox' or args[0] == 'r':
        name = 'rbox'
    elif args[0] == 'tbox' or args[0] == 't':
        name = 'tbox'
    elif args[0] == 'lchart' or args[0] == 'lc':
        name = 'lchart'
    elif args[0] == 'rchart' or args[0] == 'rc':
        name = 'rchart'
    else:
        print(f'Invalid selector "{args[0]}.". Must be lbox or rbox.')
        return { ReturnType.ERROR }

    dimensions = getattr(boxes, name)

    if args[1] == '[' and args[-1] == ']':
        vals = args[2:-1]
        if not all(v.isdigit() for v in vals):
            print("Invalid input: could not parse for dimensions.")
            return { ReturnType.ERROR }

        vals = remap([int(v) for v in vals])
        if not verify_nums(vals): return { ReturnType.ERROR }
        setattr(boxes, name, vals)

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
            print(f"Invalid number of arguments. "
                   "Expected 4, given {len(args)}.")
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
        
def loop(pdf, pagenum, pages_per_agency, boxes):
    print()
    print_help()
    print()

    pagenum -= 1
    page = pdf.pages[pagenum]
    print(f"height: {page.height}, width: {page.width}, "
          f"mid_x: {int(page.width/2)}\n")

    status = { ReturnType.DRAW, ReturnType.SHOW }

    while True:
        if ReturnType.PAGE in status:
            pagenum += pages_per_agency
            page = pdf.pages[pagenum]
        if ReturnType.SHOW in status:
            boxes.print()
        if ReturnType.DRAW in status:
            try:
                im = page.to_image(resolution=150)
                for box in BOXES:
                    val = getattr(boxes, box)
                    im.draw_rect(tuple(val))
                im.show()
            except ValueError as e:
                print("\nError! Bounding box violates page dimensions.")

        usr_input = input("\n>> ")
        status = process_input(usr_input, boxes)

        if ReturnType.CROP in status:
            try:
                for box in BOXES:
                    print(f'{box}:')
                    boxcrop = page.crop(getattr(boxes, box))
                    print(boxcrop.extract_text())
                    print()

            except ValueError as e:
                print("\nError! Bounding box violates page dimensions.")

        if ReturnType.RETURN in status:
            result = dict()
            for box in BOXES:
                result |= {box:getattr(boxes, box)}
            return result

def main(format_dict):
    for y in range(int(YEAR_START), int(YEAR_END) + 1):
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        startpage = format_dict[year]['meta']["Urban Systems (Start Page)"]
        pages_per_agency = format_dict[year]['meta']["Pages Per Agency"]

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)
            page = pdf.pages[startpage - 1]

            boxes = Boxes(page, format_dict[year], format_dict.get(prior))
            if boxes.exists: continue

            print(f'Year: {year}')
            result = loop(pdf, startpage, pages_per_agency, boxes)

        format_dict[year]['categories'] |= result
        write_to_tmp(format_dict)


if __name__ == '__main__':
    format_dict = get_format_dict()

    if len(sys.argv) == 3 and sys.argv[1] == "year":
        y = int(sys.argv[2])
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        startpage = format_dict[year]['meta']["Urban Systems (Start Page)"]
        pages_per_agency = format_dict[year]['meta']["Pages Per Agency"]

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)
            page = pdf.pages[startpage - 1]

            boxes = Boxes(page, format_dict[year], format_dict.get(prior))

            print(f'Year: {year}')
            result = loop(pdf, startpage, pages_per_agency, boxes)

        format_dict[year]['categories'] |= result
        write_to_tmp(format_dict)

    else:
        main(format_dict)
