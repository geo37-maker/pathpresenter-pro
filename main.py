import os
import runpy
import traceback

err = None
try:
    here = os.path.dirname(os.path.abspath(__file__))
    runpy.run_path(os.path.join(here, "app.py"), run_name="__main__")
except BaseException:
    err = traceback.format_exc()

if err:
    from kivy.app import App
    from kivy.core.window import Window
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    class ErrorApp(App):
        def build(self):
            lbl = Label(text=err, size_hint_y=None,
                        text_size=(Window.width - 20, None),
                        halign="left", valign="top")
            lbl.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
            sv = ScrollView()
            sv.add_widget(lbl)
            return sv

    ErrorApp().run()
