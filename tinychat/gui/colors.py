from collections import namedtuple
import re

colored_text = namedtuple("colored_text", ("text", "tags"))

colors = {
    "white": "white",
    "snow": "snow",
    "lightgray": "lightgray",  # default lightgray
    "gray": "darkgray",  # default darkgray
    "darkgray": "gray",  # default gray
    "black": "black",
    "lightblue": "lightblue",
    "blue": "blue",
    "darkblue": "darkblue",
    "turquoise": "turquoise",
    "cyan": "cyan",
    "lightcyan": "lightcyan",
    "green": "limegreen",  # default limegreen
    "darkgreen": "darkgreen",
    "lightyellow": "lightyellow",
    "yellow": "yellow",
    "gold": "gold",
    "brown": "brown",
    "orange": "orange",
    "darkorange": "darkorange",
    "lightpink": "lightpink",
    "pink": "pink",
    "orangered": "orangered2",  # default orangered
    "red": "red",
    "purple": "purple",
    "violet": "blueviolet",  # default blueviolet
    "darkviolet": "darkviolet"
}

expr = '[+](' + '|'.join(colors.keys()) + ")[(].+"


def configure_tags(textbox):
    for color1, color2 in colors.items():
        textbox.tag_configure(color1, foreground=color2)


def clear_tags(textbox):
    for color in colors.keys():
        textbox.tag_remove(color, "1.0", "end")


def set_color(text, color):
    return colored_text(text, [(color, 0, len(text))])


def convert_indexes(ctext):
    tags_conv = []

    for color, s, e in ctext.tags:
        sln = ctext.text[:s].count('\n') + 1
        sch = s - ctext.text[:s].rfind('\n') - 1

        eln = ctext.text[:e].count('\n') + 1
        ech = e - ctext.text[:e].rfind('\n') - 1

        tags_conv.append((color, (sln, sch), (eln, ech)))

    return colored_text(ctext.text, tags_conv)


def parse(text):
    tags = []
    formatted_text = ""

    t_stack = []
    w_stack = []

    m = re.search(expr, text)

    if not m:
        return colored_text(text, [])

    s = m.span()[0]
    formatted_text += text[:s]

    while s < len(text):
        e_m = re.search(expr, text[s + 1:])

        if not e_m:
            e = len(text) - 1
        else:
            e = s + e_m.span()[0]

        ct = text[s:e + 1]

        color = ct[1:ct.find('(')]

        # if color not in colors.keys():
        #     s = e+1
        #     continue

        f_s = len(formatted_text)

        if t_stack:
            cc, sc = t_stack.pop()

            if sc < f_s - 1:
                tags.append((cc, sc, f_s - 1))

            w_stack.append(cc)

        t_stack.append((color, f_s))

        frac_s = s + len(color) + 2
        frac = text[frac_s:e + 1]
        i = 0

        while t_stack and i < len(frac) and ')' in frac[i:]:
            idx = i + frac[i:].index(')')
            formatted_text += frac[i:idx]

            color, sc = t_stack.pop()
            ec = len(formatted_text)

            if sc < ec:
                tags.append((color, sc, ec))

            if w_stack:
                bcolor = w_stack.pop()
                t_stack.append((bcolor, ec + 1))

            i = idx + 1

        formatted_text += frac[i:]
        s = e + 1

    return colored_text(formatted_text, tags)


def parse2(text):
    tags = []
    formatted_text = ""

    t_stack = []

    m = re.search(expr, text)

    if not m:
        return colored_text(text, [])

    s = m.span()[0]
    formatted_text += text[:s]

    while s < len(text):
        e_m = re.search(expr, text[s + 1:])

        if not e_m:
            e = len(text) - 1
        else:
            e = s + e_m.span()[0]

        ct = text[s:e + 1]

        color = ct[1:ct.find('(')]

        # if color not in colors.keys():
        #     s = e + 1
        #     continue

        f_s = len(formatted_text)

        t_stack.append((color, f_s))

        frac_s = s + len(color) + 2
        frac = text[frac_s:e + 1]
        i = 0

        while t_stack and i < len(frac) and ')' in frac[i:]:
            idx = i + frac[i:].index(')')
            formatted_text += frac[i:idx]

            color, sc = t_stack.pop()
            ec = len(formatted_text)

            tags.append((color, sc, ec))

            i = idx + 1

        formatted_text += frac[i:]
        s = e + 1

    return colored_text(formatted_text, tags)
