import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gui.app as appmod

msgs = []
appmod.messagebox.showinfo = lambda title, text, **k: msgs.append(("info", text))
appmod.messagebox.showerror = lambda title, text, **k: msgs.append(("error", text))
appmod.messagebox.askyesno = lambda title, text, **k: msgs.append(("ask", text)) or True

app = appmod.App()
app.v_font.set("Sarabun")
app.v_mode.set("thai")
seen = set()


def start():
    app.do_install()
    app.after(300, wait)


def wait():
    seen.add(app.v_status.get())
    if app.busy:
        app.after(200, wait)
        return
    print("statuses:", len(seen))
    for kind, text in msgs:
        print(kind, ascii(text[:300]))
    app.destroy()


app.after(1500, start)
app.mainloop()
