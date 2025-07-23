import pandas as pd
from deep_translator import GoogleTranslator

df = pd.read_csv("../enriched_courses_final.csv")


def translate_column(column, col_name):
    translated = []
    total = len(column)

    print(f"\n--- 📘 '{col_name}' sütunu çevriliyor ({total} satır) ---")

    for i, text in enumerate(column):
        if pd.isna(text):
            translated.append("")
        else:
            try:
                translated_text = GoogleTranslator(source='en', target='tr').translate(text)
                translated.append(translated_text)
            except Exception as e:
                print(f"[⚠️] Hata: {e} — metin: {text}")
                translated.append(text)

        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(f"    ➤ {i + 1}/{total} satır çevrildi...")

    return translated


for col in df.select_dtypes(include='object').columns:
    df[f"{col}_tr"] = translate_column(df[col], col)

df.to_csv("../translated_dataset.csv", index=False)
print("\n[✓] Çeviri tamamlandı, 'translated_dataset.csv' olarak kaydedildi.")
