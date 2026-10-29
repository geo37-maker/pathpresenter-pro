import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image, ImageTk

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://pathpresenter.net/'
}

def get_slide_base_url(url):
    if ".dzi" in url or "_files" in url:
        return url.replace(".dzi", "_files")
    
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        raise Exception(f"فشل الاتصال بالرابط (كود: {resp.status_code})")
        
    match = re.search(r'["\'](https?://[^"\']+\.dzi)["\']', resp.text)
    if match:
        return match.group(1).replace('.dzi', '_files')
        
    match_files = re.search(r'["\'](https?://[^"\']+_files)["\']', resp.text)
    if match_files:
        return match_files.group(1)
        
    raise ValueError("تعذر استخراج مسار الشريحة تلقائياً.")

def download_tile(task):
    url, c, r, ext = task
    try:
        res = requests.get(f"{url}/{c}_{r}.{ext}", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return c, r, res.content
    except:
        pass
    return c, r, None

class SlideDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("مُحمل شرائح PathPresenter الاحترافي")
        self.root.geometry("450x350")
        self.root.config(bg="#f0f0f0")

        # عنوان الواجهة
        title_label = tk.Label(root, text="تطبيق تحميل الشرائح الرقمية HD", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#333")
        title_label.pack(pady=15)

        # خانة إدخال الرابط
        tk.Label(root, text="ألصق رابط الشريحة هنا:", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w", padx=30)
        self.url_entry = tk.Entry(root, width=45, font=("Arial", 11))
        self.url_entry.pack(pady=5, padx=30)

        # زر التحميل المباشر
        self.download_btn = tk.Button(root, text="بدء التحميل الآن", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", command=self.start_download)
        self.download_btn.pack(pady=20, ipadx=10, ipady=5)

        # حقل الحالة والتقدم
        self.status_label = tk.Label(root, text="جاهز للاستخدام", font=("Arial", 10), bg="#f0f0f0", fg="gray")
        self.status_label.pack(pady=10)

    def start_download(self):
        target_url = self.url_entry.get().strip()
        if not target_url:
            messagebox.showerror("خطأ", "الرجاء لصق رابط الشريحة أولاً!")
            return

        self.download_btn.config(state=tk.DISABLED)
        self.status_label.config(text="جاري معالجة وتحميل الشريحة...", fg="blue")
        self.root.update()

        try:
            base_url = get_slide_base_url(target_url)
            zoom_level = 14
            output_name = "pathology_slide.png"

            ext = "jpeg"
            test_url = f"{base_url}/{zoom_level}/0_0.{ext}"
            if requests.get(test_url, headers=HEADERS).status_code != 200:
                ext = "jpg"

            max_c, max_r = 0, 0
            c = 0
            while c < 300:
                if requests.get(f"{base_url}/{zoom_level}/{c}_0.{ext}", headers=HEADERS).status_code != 200:
                    max_c = c
                    break
                c += 1
            
            r = 0
            while r < 300:
                if requests.get(f"{base_url}/{zoom_level}/0_{r}.{ext}", headers=HEADERS).status_code != 200:
                    max_r = r
                    break
                r += 1

            if max_c == 0 or max_r == 0:
                raise Exception("فشل تحديد أبعاد الشبكة للشريحة.")

            sample = Image.open(BytesIO(requests.get(f"{base_url}/{zoom_level}/0_0.{ext}", headers=HEADERS).content))
            tw, th = sample.size
            
            canvas = Image.new('RGB', (max_c * tw, max_r * th))
            tasks = [(base_url, c, r, ext) for r in range(max_r) for c in range(max_c)]
            
            completed = 0
            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = {executor.submit(download_tile, t): t for t in tasks}
                for f in as_completed(futures):
                    c, r, content = f.result()
                    if content:
                        canvas.paste(Image.open(BytesIO(content)), (c * tw, r * th))
                    completed += 1
                    self.status_label.config(text=f"جاري التحميل: {completed}/{len(tasks)} جزء", fg="blue")
                    self.root.update()

            canvas.save(output_name, "PNG")
            self.status_label.config(text="تم التحميل بنجاح حفظ باسم pathology_slide.png", fg="green")
            messagebox.SUCCESS = messagebox.showinfo("نجاح", f"تم تحميل الشريحة وحفظها بنجاح باسم:\n{output_name}")

        except Exception as e:
            self.status_label.config(text="حدث خطأ أثناء التحميل", fg="red")
            messagebox.showerror("خطأ", str(e))
        finally:
            self.download_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = SlideDownloaderApp(root)
    root.mainloop()
    
