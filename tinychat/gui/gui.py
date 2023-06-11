from tkinter import *
from tkinter.scrolledtext import ScrolledText
from .colors import colored_text, configure_tags, clear_tags, convert_indexes, parse


class AppGui(Frame):
    width = 700
    height = 446

    def __init__(self, root, input_func, exit_func):
        self.root = root
        self.root.resizable(False, False)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        Frame.__init__(self, self.root, width=self.width, height=self.height, bg="gray26")
        self.pack()

        self.input_func = input_func
        self.exit_func = exit_func

        self.chat_text = ScrolledText(self, width=85, height=22,
                                      font=("Helvetica", 11), bg="gray26", fg="white",
                                      padx=10, pady=10, cursor="arrow #ffffff")

        configure_tags(self.chat_text)
        self.tags = []
        self.chat_text.config(state=DISABLED)

        self.input_text = Text(self, width=85, height=3, bg="gray36", padx=10, pady=6, fg="white")
        self.input_text.config(insertbackground="white")
        self.input_text.insert("1.0", "Введи сообщение или команду")
        self.input_text.bind("<Key>", self.input_key)
        self.input_text.bind("<KeyRelease>", self.input_clear)
        self.input_text.bind("<Up>", self.arrow_key)
        self.input_text.bind("<Down>", self.arrow_key)
        self.input_text.bind("<FocusIn>", self.focus_in)
        self.input_text.bind("<FocusOut>", self.focus_out)

        self.chat_text.place(x=0, y=0)
        self.input_text.place(x=0, y=395)

        self.command_list = ['']
        self.current_idx = -1  # decrease on arrow up and increase on arrow down

    def input_key(self, k):
        if k.keysym == "Return":
            text = self.input_text.get("1.0", "end")[:-1]  # Without newline
            if not text:
                return

            self.command_list.append(text)
            self.current_idx = -1

            self.input_text.config(state=DISABLED)

            self.input_func(text)

    def arrow_key(self, k):
        if k.keysym == "Up":
            self.current_idx = min(-1, max(-len(self.command_list), self.current_idx - 1))
        elif k.keysym == "Down":
            self.current_idx = min(-1, max(-len(self.command_list), self.current_idx + 1))

        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", self.command_list[self.current_idx])

    def input_clear(self, k):
        if k.keysym == "Return":
            self.input_text.config(state=NORMAL)
            self.input_text.delete("1.0", "end")
        else:
            text = self.input_text.get("1.0", "end")[:-1]
            self.command_list[-1] = text

    def focus_in(self, _):
        if self.input_text.get("1.0", "end") == "Введи сообщение или команду\n":
            self.input_text.delete("1.0", "end")

    def focus_out(self, _):
        if self.input_text.get("1.0", "end") == "\n":
            self.input_text.insert("1.0", "Введи сообщение или команду")

    def write(self, text):
        if isinstance(text, colored_text):
            text_p = text
        else:
            text_p = parse(text)

        self.chat_text.config(state=NORMAL)

        scroll_position = self.chat_text.yview()[1]

        index = self.chat_text.index("end").split('.')

        self.chat_text.insert("end", text_p.text + "\n")

        if text_p.tags:
            text_p = convert_indexes(text_p)

            ln = int(index[0]) - 2
            ch = int(index[1])

            for tag, s, e in text_p.tags:
                start_index = f"{ln + s[0]}.{ch + s[1]}"
                end_index = f"{ln + e[0]}.{ch + e[1]}"

                self.tags.append((tag, start_index, end_index))
                self.chat_text.tag_add(tag, start_index, end_index)

        if scroll_position == 1.0:
            self.chat_text.see("end")

        self.chat_text.config(state=DISABLED)

    def clear(self):
        self.chat_text.config(state=NORMAL)

        self.chat_text.delete("1.0", "end")

        clear_tags(self.chat_text)

        self.chat_text.config(state=DISABLED)

        self.command_list.clear()

    def close(self):
        self.exit_func()
        self.root.destroy()
