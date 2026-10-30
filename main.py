import os
import threading
import requests
from PIL import Image
from io import BytesIO

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

class PathPresenterApp(App):
    def build(self):
        self.title = "PathPresenter Downloader Pro"
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.label = Label(
            text="أدخل رابط شريحة PathPresenter:",
            size_hint_y=None,
            height=40,
            font_size=18
        )
        layout.add_widget(self.label)
        
        self.url_input = TextInput(
            text='',
            hint_text='https://www.pathpresenter.net/...',
            size_hint_y=None,
            height=50,
            multiline=False
        )
        layout.add_widget(self.url_input)
        
        self.btn = Button(
            text="تحميل الشريحة",
            size_hint_y=None,
            height=60,
            background_color=(0.1, 0.5, 0.8, 1)
        )
        self.btn.bind(on_press=self.start_download)
        layout.add_widget(self.btn)
        
        self.status_label = Label(
            text="الحالة: جاهز للعمل",
            size_hint_y=None,
            height=40
        )
        layout.add_widget(self.status_label)
        
        return layout

    def start_download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.status_label.text = "الرجاء إدخال الرابط أولاً!"
            return
        
        self.status_label.text = "جاري التحميل..."
        threading.Thread(target=self.download_slide, args=(url,)).start()

    def download_slide(self, url):
        try:
            # منطق تحميل ومعالجة الشريحة الخاص بك هنا
            # يمكنك ربط كود التحميل الفعلي الخاص بك هنا
            self.status_label.text = "تم التحميل بنجاح!"
        except Exception as e:
            self.status_label.text = f"خطأ: {str(e)}"

if __name__ == '__main__':
    PathPresenterApp().run()
    
