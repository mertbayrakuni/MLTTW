from pathlib import Path
import sys, os
from dotenv import load_dotenv
import gradio as gr

# project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# env
load_dotenv(PROJECT_ROOT / ".env")

# logging
from MLApp.utils.logging_setup import setup_logging, get_logger
setup_logging()
log = get_logger("ui")

# hook your real function(s) here
try:
    from MLApp.translator import translate_text  # change to your fn
except Exception as e:
    log.warning("Using dummy translate_text: %s", e)
    def translate_text(text: str, target_lang: str) -> str:
        return f"[demo] {text} -> ({target_lang})"

def analyze_text(text: str, lang: str) -> str:
    log.info("analyze_text called | len=%s lang=%s", len(text or ""), lang)
    try:
        if not text or not text.strip():
            return "⚠️ Lütfen bir metin girin."
        result = translate_text(text, lang)
        log.debug("result snippet: %s", str(result)[:250])
        return result
    except Exception:
        log.exception("Error in analyze_text")
        return "❌ Bir hata oluştu. Ayrıntılar: logs/app.log"

def build_ui():
    with gr.Blocks(title="MLTTW Gradio UI") as demo:
        gr.Markdown("# MLTTW — quick test UI")
        with gr.Row():
            prompt = gr.Textbox(label="Input", lines=8, placeholder="Metni yapıştır…")
            with gr.Column():
                lang = gr.Dropdown(
                    label="Target language", choices=["tr", "en", "de", "fr"], value="en"
                )
                run_btn = gr.Button("Run", variant="primary")
                clear_btn = gr.Button("Clear")
        out = gr.Markdown(label="Output")
        run_btn.click(analyze_text, [prompt, lang], [out])
        clear_btn.click(lambda: ("", gr.update(value="en"), ""), None, [prompt, lang, out])
        gr.Markdown("Made with ❤️ Gradio")
    return demo

if __name__ == "__main__":
    port = int(os.getenv("GRADIO_PORT", "7860"))
    host = os.getenv("GRADIO_HOST", "127.0.0.1")
    app = build_ui()
    log.info("Launching Gradio at http://%s:%d", host, port)
    app.queue().launch(server_name=host, server_port=port, inbrowser=True, show_error=True)
