import os
import re
import argparse
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://pathpresenter.net/'
}

def get_slide_base_url(url):
    print(f"[*] جاري فحص الرابط واستخراج إعدادات الشريحة...")
    if ".dzi" in url or "_files" in url:
        return url.replace(".dzi", "_files")
    
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        raise Exception(f"فشل الاتصال بالرابط، تأكد من صحته (كود الخطأ: {resp.status_code})")
        
    match = re.search(r'["\'](https?://[^"\']+\.dzi)["\']', resp.text)
    if match:
        return match.group(1).replace('.dzi', '_files')
        
    match_files = re.search(r'["\'](https?://[^"\']+_files)["\']', resp.text)
    if match_files:
        return match_files.group(1)
        
    raise ValueError("تعذر العثور على مسار الشريحة تلقائياً. يرجى تزويد الرابط المباشر لملف الـ DZI.")

def download_tile(task):
    url, c, r, ext = task
    try:
        res = requests.get(f"{url}/{c}_{r}.{ext}", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return c, r, res.content
    except:
        pass
    return c, r, None

def main():
    parser = argparse.ArgumentParser(description="أداة تحميل شرائح الأنسجة الرقمية بجودتها الأصلية")
    parser.add_argument("-u", "--url", required=True, help="رابط الشريحة")
    parser.add_argument("-o", "--output", default="slide_hd.png", help="اسم الصورة الناتجة")
    parser.add_argument("-z", "--zoom", type=int, default=14, help="مستوى التكبير (Zoom Level)")
    args = parser.parse_args()

    try:
        base_url = get_slide_base_url(args.url)
        print(f"[+] مسار التحميل الأساسي: {base_url}")
        
        ext = "jpeg"
        test_url = f"{base_url}/{args.zoom}/0_0.{ext}"
        if requests.get(test_url, headers=HEADERS).status_code != 200:
            ext = "jpg"

        print("[+] جاري فحص أبعاد وأجزاء الشريحة...")
        max_c, max_r = 0, 0
        c = 0
        while c < 300:
            if requests.get(f"{base_url}/{args.zoom}/{c}_0.{ext}", headers=HEADERS).status_code != 200:
                max_c = c
                break
            c += 1
            
        r = 0
        while r < 300:
            if requests.get(f"{base_url}/{args.zoom}/0_{r}.{ext}", headers=HEADERS).status_code != 200:
                max_r = r
                break
            r += 1

        if max_c == 0 or max_r == 0:
            raise Exception("فشل تحديد أبعاد الشريحة، قد يكون مستوى التكبير غير دقيق أو الرابط غير صالح.")

        print(f"[+] تم رصد الشبكة بنجاح: {max_c} عمود × {max_r} صف")
        
        sample = Image.open(BytesIO(requests.get(f"{base_url}/{args.zoom}/0_0.{ext}", headers=HEADERS).content))
        tw, th = sample.size
        
        canvas = Image.new('RGB', (max_c * tw, max_r * th))
        tasks = [(base_url, c, r, ext) for r in range(max_r) for c in range(max_c)]
        
        print(f"[+] جاري تحميل ودمج {len(tasks)} جزء بأقصى سرعة...")
        completed = 0
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(download_tile, t): t for t in tasks}
            for f in as_completed(futures):
                c, r, content = f.result()
                if content:
                    canvas.paste(Image.open(BytesIO(content)), (c * tw, r * th))
                completed += 1
                print(f"  -> التقدم: {completed}/{len(tasks)}", end="\r")

        print(f"\n[+] جاري حفظ الصورة النهائية...")
        canvas.save(args.output, "PNG")
        print(f"[✔] تم الحفظ بنجاح باسم: {args.output}")

    except Exception as e:
        print(f"[✕] حدث خطأ: {e}")

if __name__ == "__main__":
    main()
              
