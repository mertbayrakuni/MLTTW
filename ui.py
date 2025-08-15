# ui.py — kursbul.net Assistant (frontend-only)
from __future__ import annotations
from pathlib import Path
import sys, os, time, json
from typing import List, Tuple, Optional

import gradio as gr
import requests
from dotenv import load_dotenv

# Make project root importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Env + Logging
load_dotenv(PROJECT_ROOT / ".env")
from MLApp.utils.logging_setup import setup_logging, get_logger, LOG_FILE
setup_logging()
log = get_logger("ui")

# ------------------------------- backend adapter -------------------------------

def _history_to_messages(history_tuples: List[Tuple[str, str]], system_prompt: str) -> list[dict]:
    msgs = []
    if system_prompt and system_prompt.strip():
        msgs.append({"role": "system", "content": system_prompt.strip()})
    for user, bot in history_tuples:
        if user:
            msgs.append({"role": "user", "content": user})
        if bot:
            msgs.append({"role": "assistant", "content": bot})
    return msgs

def call_backend_chat(prompt: str,
                      history_tuples: List[Tuple[str, str]],
                      system_prompt: str) -> str:
    """
    POSTs to your backend. Adjust the path/field names to your API.
    Expected JSON response with 'answer' or 'text'.
    """
    base = os.getenv("KURSBUL_API_BASE", "").rstrip("/")
    if not base:
        raise RuntimeError("KURSBUL_API_BASE is not set")

    url = f"{base}/chat"        # <- change if your route is different
    payload = {
        "prompt": prompt,
        "messages": _history_to_messages(history_tuples, system_prompt),
        # include whatever your backend expects:
        # "top_k": 5, "mode": "chat", ...
    }
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("KURSBUL_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    log.debug("POST %s", url)
    r = requests.post(url, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    answer = data.get("answer") or data.get("text") or data.get("message")
    if not answer:
        raise ValueError(f"Backend reply missing text: {data}")
    return answer

# ----------------------------- optional course search --------------------------

_COURSES = None
def load_courses_df():
    """Loads a local CSV/XLSX if present. If none found, returns empty DF."""
    global _COURSES
    if _COURSES is not None:
        return _COURSES
    import pandas as pd
    candidates = [
        PROJECT_ROOT / "enriched_courses_final.csv",
        PROJECT_ROOT / "Online_Courses.csv",
        PROJECT_ROOT / "online_courses.csv",
        PROJECT_ROOT / "enriched_courses_final.xlsx",
    ]
    for p in candidates:
        try:
            if p.suffix.lower() == ".xlsx":
                df = pd.read_excel(p)
            else:
                df = pd.read_csv(p)
            if not df.empty:
                _COURSES = df
                log.info("Loaded course dataset: %s (%s rows)", p.name, len(df))
                return _COURSES
        except Exception:
            continue
    import pandas as pd
    _COURSES = pd.DataFrame()
    return _COURSES

def search_courses(query: str,
                   max_price: Optional[float],
                   durations: List[str],
                   providers: List[str],
                   top_k: int = 8):
    """
    Simple local filter — replace with a real backend search if you prefer.
    """
    import pandas as pd
    df = load_courses_df()
    cards_md = "### Sonuçlar\n"
    if df.empty:
        examples = [
            {"title":"Python for Everybody","provider":"Coursera","price":"Free","duration":"≈ 40 saat","url":"https://www.coursera.org/"},
            {"title":"Modern React + Redux","provider":"Udemy","price":"₺","duration":"≈ 25 saat","url":"https://www.udemy.com/"},
            {"title":"SQL Fundamentals","provider":"Codecademy","price":"Freemium","duration":"≈ 10 saat","url":"https://www.codecademy.com/"},
        ]
        for e in examples:
            cards_md += f"- **{e['title']}** — {e['provider']} · {e['duration']} · {e['price']}  \n  {e['url']}\n"
        return cards_md, pd.DataFrame(examples)

    work = df.copy()
    cols = {c.lower(): c for c in work.columns}
    def col(name):
        return cols.get(name, next((c for c in work.columns if name in c.lower()), None))

    title_c = col("title") or col("name") or col("course")
    prov_c  = col("provider") or col("platform")
    price_c = col("price") or col("ucret") or col("cost")
    dur_c   = col("duration") or col("süre") or col("length") or col("hafta")

    if query and title_c:
        work = work[work[title_c].astype(str).str.contains(query, case=False, na=False)]
    if providers and prov_c:
        work = work[work[prov_c].astype(str).str.lower().isin([p.lower() for p in providers])]
    if max_price is not None and price_c:
        def _parse(v):
            try:
                v = str(v).replace("₺","").replace("$","").replace(",","").strip()
                return float(v)
            except Exception:
                return None
        work["_price_num"] = work[price_c].map(_parse)
        work = work[(work["_price_num"].isna()) | (work["_price_num"] <= max_price)]

    rank_cols = [c for c in work.columns if "rating" in c.lower() or "enroll" in c.lower()]
    if rank_cols:
        work = work.sort_values(rank_cols[0], ascending=False)
    else:
        work = work.sort_values(title_c, ascending=True)

    out = work.head(top_k)
    cards_md = "### Sonuçlar\n"
    for _, row in out.iterrows():
        t = str(row.get(title_c, "İsimsiz Kurs"))
        pr = str(row.get(prov_c, ""))
        du = str(row.get(dur_c, ""))
        pc = str(row.get(price_c, ""))
        url = str(next((row.get(c) for c in ["url","link","site","page","course_url"] if c in row.index), "")) or "#"
        meta = " · ".join([x for x in [pr or None, du or None, pc or None] if x])
        line = f"- **{t}**" + (f" — {meta}" if meta else "")
        cards_md += f"{line}  \n  {url}\n"

    keep = [c for c in [title_c, prov_c, dur_c, price_c, "url"] if c and c in out.columns]
    small = out[keep].rename(columns={title_c:"title", prov_c:"provider", dur_c:"duration", price_c:"price"})
    return cards_md, small.reset_index(drop=True)

# ----------------------------- logs helper ------------------------------------

def tail_log(n_lines: int = 200) -> str:
    try:
        p = Path(LOG_FILE)
        if not p.exists():
            return f"(no log yet) Expected at: {p}"
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-n_lines:]
        return "".join(lines) or "(empty)"
    except Exception as e:
        return f"Cannot read log: {e}"

# ----------------------------- chat wiring ------------------------------------

def respond(message: str,
            chat_history: List[Tuple[str,str]],
            system_prompt: str,
            auto_search: bool,
            max_price: Optional[float],
            durations: List[str],
            providers: List[str]):

    log.info("User: %s", message[:200])
    chat_history = chat_history + [(message, "")]
    try:
        answer = call_backend_chat(message, chat_history[:-1], system_prompt)
    except Exception as e:
        log.exception("Backend chat failed")
        answer = f"❌ Sunucuya ulaşılamadı: {e}"

    chat_history[-1] = (message, answer)

    results_md, results_df = ("", None)
    if auto_search:
        try:
            results_md, results_df = search_courses(message, max_price, durations, providers)
        except Exception:
            log.exception("Course search failed")

    return chat_history, results_md, results_df

def clear_chat():
    return [], ""

def export_chat(history: List[Tuple[str,str]]):
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = PROJECT_ROOT / "logs" / "chats"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = [{"user": u, "assistant": a} for (u, a) in history]
    path = out_dir / f"chat-{ts}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("Saved chat export: %s", path)
    return f"Kaydedildi: {path}"

# ----------------------------------- UI ---------------------------------------

def build_ui():
    theme = gr.themes.Soft(primary_hue="indigo", neutral_hue="slate")
    with gr.Blocks(theme=theme, title="kursbul — Asistan") as demo:
        gr.Markdown("## kursbul — Asistan")

        with gr.Row(equal_height=True):
            # Left: Chat
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label=None,
                    height=520,
                    bubble_full_width=False,
                    show_copy_button=True
                )

                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Ne öğrenmek istiyorsun? Örn: 'Ücretsiz Python başlangıç kursu'",
                        scale=6
                    )
                    send = gr.Button("Gönder", variant="primary", scale=1)
                with gr.Row():
                    clear = gr.Button("Temizle")
                    export = gr.Button("Dışa Aktar")
                with gr.Accordion("Gelişmiş", open=False):
                    system_prompt = gr.Textbox(
                        label="Sistem talimatı (opsiyonel)",
                        value="",
                        lines=3
                    )

                # Quick chips
                with gr.Row():
                    ex1 = gr.Button("Ücretsiz Python başlangıç kursu")
                    ex2 = gr.Button("React + TypeScript yol haritası")
                    ex3 = gr.Button("Veri bilimine hızlı giriş")

            # Right: Search + Logs
            with gr.Column(scale=2):
                with gr.Tab("Arama"):
                    auto_search = gr.Checkbox(value=True, label="Soru gönderince otomatik arama yap")
                    with gr.Accordion("Filtreler", open=False):
                        max_price = gr.Number(value=None, label="Maks. Fiyat (₺) — boş: sınırsız")
                        durations = gr.CheckboxGroup(
                            choices=["<5 saat","5–10 saat","10–20 saat","20–40 saat","40+ saat"],
                            value=["10–20 saat"],
                            label="Süre (tavsiye amaçlı)"
                        )
                        providers = gr.CheckboxGroup(
                            choices=["Coursera","Udemy","edX","Codecademy","LinkedIn Learning"],
                            label="Platform"
                        )
                    results_md = gr.Markdown("")
                    results_df = gr.Dataframe(type="pandas", interactive=False, label="Tablo görünümü")

                with gr.Tab("Logs"):
                    n_lines = gr.Slider(50, 2000, value=400, step=50, label="Son N satır")
                    log_box = gr.Textbox(value=tail_log(400), lines=18, interactive=False, label="logs/app.log", show_copy_button=True)
                    refresh = gr.Button("Yenile")
                    refresh.click(lambda n: tail_log(int(n)), n_lines, log_box)
                    gr.Timer(2.0).tick(lambda n: tail_log(int(n)), n_lines, log_box)

        # State
        state = gr.State([])  # list[(user, assistant)]

        # Wiring
        def _on_send(user_msg, history, sys_prompt, auto_s, price, dur, provs):
            if not (user_msg and user_msg.strip()):
                return gr.update(), history, results_md, results_df
            new_history, md, df = respond(user_msg, history, sys_prompt, auto_s, price, dur, provs)
            return new_history, new_history, md, df

        send.click(
            _on_send,
            inputs=[msg, state, system_prompt, auto_search, max_price, durations, providers],
            outputs=[chatbot, state, results_md, results_df]
        ).then(lambda: "", None, msg)

        clear.click(lambda: ([], []), None, [chatbot, state])
        export.click(lambda h: export_chat(h), state, results_md)

        # quick chips fill the input
        ex1.click(lambda: "Ücretsiz Python başlangıç kursu", None, msg)
        ex2.click(lambda: "React + TypeScript yol haritası", None, msg)
        ex3.click(lambda: "Veri bilimine hızlı giriş", None, msg)

        gr.Markdown("Made with ❤️ for **kursbul.net**")

    return demo

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("GRADIO_HOST", "127.0.0.1")
    port = int(os.getenv("GRADIO_PORT", "7860"))
    app = build_ui()
    log.info("Launching Gradio at http://%s:%d", host, port)
    app.queue().launch(server_name=host, server_port=port, inbrowser=True, show_error=True)
