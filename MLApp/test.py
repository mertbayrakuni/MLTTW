import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
import string
import re

# Eğitim URL'leri
urls = [
    "https://talktoweb.com/egitimler/grafik-tasarim-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/almanca-dil-kursu",
    "https://talktoweb.com/egitimler/dijital-pazarlama-ve-sosyal-medya-sertifika-programi",
    "https://talktoweb.com/egitimler/ozan-sihay-ile-uretken-yapay-zeka",
    "https://talktoweb.com/egitimler/grafik-tasarim-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/ui-ux-tasarim-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/video-efekt-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/lightroom-ile-retouch-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/dijital-pazarlama-ve-sosyal-medya-sertifika-programi",
    "https://talktoweb.com/egitimler/grafik-tasarim-ve-video-efekt-uzmanligi-egitimi/",
    "https://talktoweb.com/egitimler/grafik-tasarim-video-efekt-egitimi/",
    "https://talktoweb.com/egitimler/ui-ux-tasarim-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/web-tasarim-front-end-uzmanligi-haziran/",
    "https://talktoweb.com/egitimler/video-efekt-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/blender-3d-tasarim-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/3ds-max-egitimi",
    "https://talktoweb.com/egitimler/web-tasarim-front-end-uzmanligi-sertifika-programi/",
    "https://talktoweb.com/egitimler/ui-ux-tasarim-uzmanligi-sertifika-programi",
    "https://talktoweb.com/egitimler/dijital-pazarlama-ve-sosyal-medya-sertifika-programi",
    "https://talktoweb.com/egitimler/dijital-pazarlama-ve-sosyal-medya-uzmanligi",
    "https://talktoweb.com/egitimler/web-tasarim-front-end-uzmanligi-egitimi/",
    "https://talktoweb.com/egitimler/grafik-tasarimi-ve-video-efekt-uzmanligi-egitimi/",
    "https://talktoweb.com/egitimler/dijital-pazarlama-ve-sosyal-medya-egitimi",
    "https://talktoweb.com/egitimler/ui-ux-tasarim-uzmanligi-sertifika-programi",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def clean_content(program_content):
    cleaned_lines = []

    for line in program_content:
        cleaned_line = line
        for punc in string.punctuation:
            cleaned_line = cleaned_line.replace(punc, '')
        cleaned_lines.append(cleaned_line.strip())

    return cleaned_lines


def clean_content_regex(program_content):
    cleaned_lines = []

    for line in program_content:
        cleaned_line = re.sub(r'[^\w\sçğıöşüÇĞİÖŞÜ]', '', line)
        cleaned_lines.append(cleaned_line.strip())

    return cleaned_lines


def get_education_content(url):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else 'Başlık bulunamadı'
        program_content = []

        program_header = soup.find(
            lambda tag: tag.name in ['h2', 'h3', 'h4'] and 'eğitim programı' in tag.get_text().lower())

        if program_header:
            next_node = program_header.find_next_sibling()
            while next_node and next_node.name not in ['h2', 'h3', 'h4']:
                if next_node.name in ['p', 'ul', 'ol', 'div']:
                    program_content.append(next_node.get_text(strip=True))
                next_node = next_node.find_next_sibling()

        if not program_content:
            program_div = soup.find('div', class_=lambda x: x and 'program' in x.lower()) or \
                          soup.find('div', id=lambda x: x and 'program' in x.lower())
            if program_div:
                program_content = [p.get_text(strip=True) for p in program_div.find_all(['p', 'li'])]

        cleaned_lines = clean_content(program_content)

        return {
            'url': url,
            'title': title,
            'content': '\n'.join(cleaned_lines) if program_content else 'Eğitim programı içeriği bulunamadı'
        }

    except Exception as e:
        return {
            'url': url,
            'error': str(e)
        }


def save_education_programs(file_path):
    with open(file_path, "w", encoding="utf-8") as f_out:
        for url in urls:
            result = get_education_content(url)

            if 'error' in result:
                print(f"[HATA] {result['url']} - {result['error']}")
                continue

            print(f"\n=== {result.get('title', 'Başlık Bulunamadı')} ===")
            print(f"URL: {result.get('url', 'URL Yok')}")
            print("\nEğitim Programı İçeriği:")
            print(result['content'])

            f_out.write(f"=== {result.get('title', 'Başlık Bulunamadı')} ===\n")
            f_out.write(f"URL: {result.get('url', 'URL Yok')}\n")
            f_out.write(result['content'] + "\n\n")


def analyze_top_words(file_path, top_n=20):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    stopwords = {
        've', 'ile', 'bu', 'bir', 'için', 'gibi', 'de', 'da', 'ne', 'nasıl',
        'nedir', 'mi', 'niçin', 'neden', 'olan', 'olarak', 'veya', 'ya', 'ki', 'çok',
        'en', 'ama', 'fakat', 'ancak', 'ya da', 'hem', 'ise', 'şu', 'o', 'şey',
        'tüm', 'daha', 'her', 'kadar', 'sonra', 'önce', 'çünkü',
    }

    words = re.findall(r'\b[a-zçğıöşü]{3,}\b', text.lower())
    filtered_words = [word for word in words if word not in stopwords]
    return Counter(filtered_words).most_common(top_n)


def plot_word_frequencies(top_words):
    labels, counts = zip(*top_words)
    plt.figure(figsize=(12, 6))
    plt.bar(labels, counts, color='skyblue')
    plt.title("Eğitim Programlarında En Sık Geçen 20 Kelime")
    plt.xlabel("Kelimeler")
    plt.ylabel("Frekans")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("kelime_frekanslari.png", dpi=300)
    plt.show()


def export_words_to_excel(top_words, file_name="en_sik_kelimeler.xlsx"):
    df = pd.DataFrame(top_words, columns=["Kelime", "Frekans"])
    df.to_excel(file_name, index=False)
    print(f"[✓] Excel dosyası oluşturuldu: {file_name}")


# Ana akış
save_education_programs("egitim_programlari.txt")
top_words = analyze_top_words("egitim_programlari.txt")
plot_word_frequencies(top_words)
export_words_to_excel(top_words)
