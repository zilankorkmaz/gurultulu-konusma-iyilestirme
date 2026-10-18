"""AudioDenoiser - Ses İyileştirme Web Platformu (app.py).

Gelişmiş Derin Öğrenme (DeepFilterNet) ve Klasik DSP algoritmalarıyla (Wiener,
Spektral Çıkarma) ses kayıtlarındaki gürültüleri temizler ve analiz eder.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
DATA_NOISY_DIR = ROOT_DIR / "data" / "noisy"
CSS_FILE = ROOT_DIR / "assets" / "style.css"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr
from pipeline import process_audio_pipeline
from ui import components as ui_comp


def load_css() -> str:
    """assets/style.css dosyasından stil kurallarını okur."""
    if CSS_FILE.exists():
        return CSS_FILE.read_text(encoding="utf-8")
    return ""


def get_sample_audio_files():
    """data/noisy klasöründeki örnek ses dosyalarını listeler."""
    if not DATA_NOISY_DIR.exists():
        return []
    extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    files = sorted(f for f in DATA_NOISY_DIR.rglob("*") if f.suffix.lower() in extensions)
    return [[str(f)] for f in files[:5]]


def build_interface():
    """Ana Gradio arayüzünü oluşturur."""
    with gr.Blocks(title="AudioDenoiser — Ses İyileştirme Platformu") as demo:
        # Hero Başlık
        gr.HTML(ui_comp.hero_header())

        with gr.Row(equal_height=False):

            # ── SOL PANEL: Girdi ve Kontroller ──
            with gr.Column(scale=4, min_width=340):

                # 1. Ses Girişi Kartı (Gürültülü Ses)
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("📁", "1. Gürültülü Ses Girişi", "Gürültülü ses dosyasını yükleyin veya mikrofonla kaydedin"))
                    audio_input = gr.Audio(
                        sources=["upload", "microphone"],
                        type="filepath",
                        show_label=False,
                        elem_classes=["audio-uploader"]
                    )

                # 2. Referans Temiz Ses Kartı (Metrik Ölçümü İçin)
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("🎯", "2. Referans Temiz Ses (Opsiyonel)", "PESQ, STOI ve SI-SDR puanlarını ölçmek için stüdyo kaydı / temiz ses"))
                    ref_audio_input = gr.Audio(
                        sources=["upload"],
                        type="filepath",
                        show_label=False,
                        elem_classes=["audio-uploader"]
                    )



                # 2. Algoritma Seçimi Kartı
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("⚙️", "İyileştirme Algoritması", "Uygulamak istediğiniz filtreleme modelini belirleyin"))
                    method_radio = gr.Radio(
                        choices=[
                            "Tüm Modelleri Karşılaştır (A/B/C Analizi)",
                            "DeepFilterNet (Yapay Zeka / Derin Öğrenme)",
                            "Wiener Filtresi (İstatistiksel MMSE)",
                            "Spektral Çıkarma (Klasik STFT)",
                        ],
                        value="Tüm Modelleri Karşılaştır (A/B/C Analizi)",
                        show_label=False,
                        elem_classes=["method-radio-card"]
                    )

                # 3. Parametre İnce Ayarı Kartı
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("🎛️", "Parametre İnce Ayarı", "Spektral filtreleme agresiflik katsayısı"))
                    alpha_slider = gr.Slider(
                        minimum=0.5, maximum=3.0, value=1.5, step=0.1,
                        label="Alpha (Aşırı Çıkarma Katsayısı)",
                        info="Değer arttıkça daha fazla gürültü silinir; aşırı yüksek değerler müzikal gürültüye yol açabilir.",
                        elem_classes=["slider-container"]
                    )

                # 4. Ana Çalıştır Butonu (Canlı Mavi Buton)
                btn_process = gr.Button(
                    "⚡  Sesi İyileştir ve Spektrumu Analiz Et",
                    variant="primary",
                    size="lg",
                    elem_classes=["run-btn"]
                )

                # 5. Hazır Test Örnekleri (Varsa)
                examples = get_sample_audio_files()
                if examples:
                    with gr.Group(elem_classes=["panel-card"]):
                        gr.HTML(ui_comp.card_header("📂", "Hızlı Test Kayıtları", "Önceden hazırlanmış test seslerini doğrudan deneyin"))
                        gr.Examples(examples=examples, inputs=[audio_input], label="")

            # ── SAĞ PANEL: Çıktılar ve Grafikler ──
            with gr.Column(scale=6):

                # Durum / Bilgilendirme Çubuğu
                status_box = gr.Markdown(
                    "💡 **Hazır:** Sol panelden bir ses yükleyin veya hazır test kayıtlarından seçerek **'Sesi İyileştir'** butonuna tıklayın.",
                    elem_classes=["status-box"]
                )

                # İyileştirilmiş Ses Çıktıları Kartı
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("🔊", "İyileştirilmiş Ses Çıktıları", "Modeller tarafından filtrelenen sesleri dinleyin ve indirin"))
                    with gr.Row():
                        with gr.Column(elem_classes=["audio-output-item", "audio-card-spectral"]):
                            gr.HTML(ui_comp.audio_track_header("🔵 Spektral Çıkarma", "Klasik STFT", "pill-blue"))
                            audio_spectral = gr.Audio(show_label=False, interactive=False)

                        with gr.Column(elem_classes=["audio-output-item", "audio-card-wiener"]):
                            gr.HTML(ui_comp.audio_track_header("🟠 Wiener Filtresi", "MMSE Kazanç", "pill-orange"))
                            audio_wiener = gr.Audio(show_label=False, interactive=False)

                        with gr.Column(elem_classes=["audio-output-item", "audio-card-deep"]):
                            gr.HTML(ui_comp.audio_track_header("🟢 DeepFilterNet", "Derin Öğrenme", "pill-green"))
                            audio_deepfilter = gr.Audio(show_label=False, interactive=False)

                # 2. Nesnel Kalite Ölçütleri Kartı (PESQ, STOI, SI-SDR)
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("🏆", "Nesnel Kalite Ölçütleri", "Algoritmaların gürültü bastırma ve anlaşılabilirlik metrikleri"))
                    metrics_output = gr.HTML(ui_comp.metrics_table_html({}))

                # 3. Dalga Formu ve Spektrogram Görselleştirme Kartı
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("📊", "Dalga Formu & Spektrogram Analizi", "Orijinal sinyal ile modellerin gürültü baskılama başarısının frekans-zaman karşılaştırması"))
                    plot_output = gr.Plot(show_label=False, elem_classes=["plot-frame"])

        # Pipeline eşleştirme ve çalıştırma
        def map_and_run(audio, ref_audio, method, alpha):
            method_map = {
                "Tüm Modelleri Karşılaştır (A/B/C Analizi)": "Tümünü Karşılaştır",
                "DeepFilterNet (Yapay Zeka / Derin Öğrenme)": "DeepFilterNet",
                "Wiener Filtresi (İstatistiksel MMSE)": "Wiener Filtresi",
                "Spektral Çıkarma (Klasik STFT)": "Spektral Çıkarma",
            }
            clean_method = method_map.get(method)
            if not clean_method:
                if "DeepFilterNet" in str(method):
                    clean_method = "DeepFilterNet"
                elif "Wiener" in str(method):
                    clean_method = "Wiener Filtresi"
                elif "Spektral" in str(method):
                    clean_method = "Spektral Çıkarma"
                else:
                    clean_method = "Tümünü Karşılaştır"

            sp_out, wf_out, df_out, fig, status, m_dict = process_audio_pipeline(
                audio, clean_method, alpha, ref_audio_input=ref_audio
            )
            m_html = ui_comp.metrics_table_html(m_dict)
            return sp_out, wf_out, df_out, fig, status, m_html

        btn_process.click(
            fn=map_and_run,
            inputs=[audio_input, ref_audio_input, method_radio, alpha_slider],
            outputs=[audio_spectral, audio_wiener, audio_deepfilter, plot_output, status_box, metrics_output]
        )


    return demo


if __name__ == "__main__":
    demo_app = build_interface()
    demo_app.launch(
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
        css=load_css(),
        share=False,
        show_error=True
    )
