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
RESULTS_DIR = ROOT_DIR / "results"
ANALYSIS_DIR = RESULTS_DIR / "analysis"

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
    """data/noisy klasöründeki VoiceBank örnek ses dosyalarını listeler."""
    if not DATA_NOISY_DIR.exists():
        return []
    extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    files = sorted(f for f in DATA_NOISY_DIR.rglob("*") if f.suffix.lower() in extensions)
    return [[str(f)] for f in files[:5]]


def get_analysis_summary_html() -> str:
    """results/analysis/summary_by_method.csv tablosunu HTML'e çevirir."""
    csv_path = ANALYSIS_DIR / "summary_by_method.csv"
    if not csv_path.exists():
        return """
        <div style="padding: 20px; background: #f8fafc; border-radius: 10px; border: 1.5px dashed #94a3b8;
                    color: #475569; text-align: center;">
            <div style="font-size: 1.5rem;">📊</div>
            <b>Analiz sonuçları henüz oluşturulmadı.</b><br>
            <span style="font-size:0.9rem;">
                Sonuçlar üretmek için terminalde şu komutu çalıştırın:<br>
                <code style="background:#e2e8f0; padding:2px 6px; border-radius:4px;">
                    python scripts/evaluate_experiment.py
                </code>
            </span>
        </div>
        """
    import csv
    rows_html = ""
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            method = row.get("method", row.get("", "—"))
            pesq = row.get("PESQ", "—")
            stoi = row.get("STOI", "—")
            si_sdr = row.get("SI-SDR (dB)", "—")
            rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px 16px; font-weight: 700; color: #0f172a;">{method}</td>
                <td style="padding: 12px 16px; text-align: center; color: #1d4ed8; font-weight: 700;">{pesq}</td>
                <td style="padding: 12px 16px; text-align: center; color: #047857; font-weight: 700;">{stoi}</td>
                <td style="padding: 12px 16px; text-align: center; color: #b45309; font-weight: 700;">{si_sdr}</td>
            </tr>
            """
    return f"""
    <div style="overflow-x: auto; border: 1px solid #cbd5e1; border-radius: 10px;
                background: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.93rem; text-align: left;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                    <th style="padding: 12px 16px; font-weight: 700; color: #1e293b;">Yöntem / Model</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b;">PESQ (ort ± std)</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b;">STOI (ort ± std)</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b;">SI-SDR — ort ± std (dB)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """


def get_improvement_html() -> str:
    """results/analysis/improvement_vs_noisy.csv tablosunu HTML'e çevirir."""
    csv_path = ANALYSIS_DIR / "improvement_vs_noisy.csv"
    if not csv_path.exists():
        return "<p style='color:#94a3b8'>Veri yok.</p>"
    import csv
    rows_html = ""
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            method = row.get("Yöntem", "—")
            cells = "".join(
                f'<td style="padding:10px 14px; text-align:center; color:#0f172a; font-weight:600;">{row.get(k, "—")}</td>'
                for k in fieldnames if k != "Yöntem"
            )
            rows_html += f"""<tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:10px 14px; font-weight:700; color:#0f172a;">{method}</td>
                {cells}
            </tr>"""
    header_cells = "".join(
        f'<th style="padding:10px 14px; text-align:center; font-weight:700; color:#1e293b;">{k}</th>'
        for k in (fieldnames or []) if k != "Yöntem"
    )
    return f"""
    <div style="overflow-x:auto; border:1px solid #cbd5e1; border-radius:10px;
                background:#ffffff; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <table style="width:100%; border-collapse:collapse; font-size:0.92rem;">
            <thead><tr style="background:#f1f5f9; border-bottom:2px solid #cbd5e1;">
                <th style="padding:10px 14px; font-weight:700; color:#1e293b;">Yöntem</th>
                {header_cells}
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """


def get_analysis_graphs():
    """Grafik dosyalarını döndürür; yoksa None döner."""
    snr_png = ANALYSIS_DIR / "metrics_vs_snr.png"
    noise_png = ANALYSIS_DIR / "metrics_by_noise.png"
    return (str(snr_png) if snr_png.exists() else None,
            str(noise_png) if noise_png.exists() else None)


def build_interface():
    """Ana Gradio arayüzünü oluşturur."""
    with gr.Blocks(title="AudioDenoiser — Ses İyileştirme Platformu") as demo:
        # Hero Başlık
        gr.HTML(ui_comp.hero_header())

        with gr.Tabs():
            # ─────────────────────────────────────────────────────────
            # SEKME 1: Canlı Ses İyileştirme
            # ─────────────────────────────────────────────────────────
            with gr.Tab("🎙️ Canlı Ses İyileştirme"):
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

                        # 3. Algoritma Seçimi Kartı
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

                        # 4. Parametre İnce Ayarı Kartı
                        with gr.Group(elem_classes=["panel-card"]):
                            gr.HTML(ui_comp.card_header("🎛️", "Parametre İnce Ayarı", "Spektral filtreleme agresiflik katsayısı"))
                            alpha_slider = gr.Slider(
                                minimum=0.5, maximum=3.0, value=1.5, step=0.1,
                                label="Alpha (Aşırı Çıkarma Katsayısı)",
                                info="Değer arttıkça daha fazla gürültü silinir; aşırı yüksek değerler müzikal gürültüye yol açabilir.",
                                elem_classes=["slider-container"]
                            )

                        # 5. Ana Çalıştır Butonu
                        btn_process = gr.Button(
                            "⚡  Sesi İyileştir ve Spektrumu Analiz Et",
                            variant="primary",
                            size="lg",
                            elem_classes=["run-btn"]
                        )

                        # 6. Hazır Test Örnekleri (VoiceBank'tan)
                        examples = get_sample_audio_files()
                        if examples:
                            with gr.Group(elem_classes=["panel-card"]):
                                gr.HTML(ui_comp.card_header("📂", "VoiceBank Hızlı Test Kayıtları", "VoiceBank test kümesinden hazırlanmış örnek gürültülü sesler"))
                                gr.Examples(examples=examples, inputs=[audio_input], label="")

                    # ── SAĞ PANEL: Çıktılar ve Grafikler ──
                    with gr.Column(scale=6):

                        # Durum / Bilgilendirme Çubuğu
                        status_box = gr.Markdown(
                            "💡 **Hazır:** Sol panelden bir ses yükleyin veya VoiceBank test kayıtlarından seçerek **'Sesi İyileştir'** butonuna tıklayın.",
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

                        # Nesnel Kalite Ölçütleri Kartı (PESQ, STOI, SI-SDR)
                        with gr.Group(elem_classes=["panel-card"]):
                            gr.HTML(ui_comp.card_header("🏆", "Nesnel Kalite Ölçütleri", "Algoritmaların gürültü bastırma ve anlaşılabilirlik metrikleri"))
                            metrics_output = gr.HTML(ui_comp.metrics_table_html({}))

                        # Dalga Formu ve Spektrogram Görselleştirme Kartı
                        with gr.Group(elem_classes=["panel-card"]):
                            gr.HTML(ui_comp.card_header("📊", "Dalga Formu & Spektrogram Analizi", "Orijinal sinyal ile modellerin gürültü baskılama başarısının frekans-zaman karşılaştırması"))
                            plot_output = gr.Plot(show_label=False, elem_classes=["plot-frame"])

                # Pipeline bağlantısı
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

            # ─────────────────────────────────────────────────────────
            # SEKME 2: Model Karşılaştırma & Sonuçlar (results/analysis)
            # ─────────────────────────────────────────────────────────
            with gr.Tab("📈 Model Karşılaştırma & Sonuçlar"):

                gr.HTML("""
                <div style="padding: 14px 20px; background: linear-gradient(90deg, #f0f9ff, #e0f2fe);
                            border-left: 4px solid #0ea5e9; border-radius: 8px; margin-bottom: 12px; color: #0f172a;">
                    <b>ℹ️ Bu sekme</b> — <code>results/analysis/</code> klasöründeki toplu değerlendirme
                    çıktılarını (VoiceBank test kümesi, 4 yöntem, PESQ/STOI/SI-SDR) göstermektedir.
                    Yeni sonuçlar üretmek için terminalde:
                    <code style="background:#bae6fd; padding:2px 6px; border-radius:4px;">
                        python scripts/evaluate_experiment.py
                    </code>
                </div>
                """)

                # ── Ortalama Metrik Tablosu ──
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("📋", "Yöntem Başına Ortalama Metrikler (± std)", "VoiceBank test kümesi üzerinde ölçülen PESQ, STOI ve SI-SDR değerleri"))
                    summary_table_html = gr.HTML(get_analysis_summary_html())

                # ── İyileşme Tablosu ──
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("📈", "İşlemsiz Kayda Göre Ortalama İyileşme (Δ)", "Her yöntemin gürültülü girdiye kıyasla sağladığı kazanım"))
                    improvement_html = gr.HTML(get_improvement_html())

                # ── Grafikler ──
                snr_img, noise_img = get_analysis_graphs()
                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("📊", "SNR Seviyesine Göre PESQ & STOI & SI-SDR", "Her giriş SNR değerinde dört yöntemin karşılaştırmalı başarımı"))
                    if snr_img:
                        gr.Image(value=snr_img, show_label=False, show_download_button=True, elem_classes=["plot-frame"])
                    else:
                        gr.HTML("<p style='color:#94a3b8; padding:16px;'>Grafik henüz oluşturulmadı.</p>")

                with gr.Group(elem_classes=["panel-card"]):
                    gr.HTML(ui_comp.card_header("🔈", "Gürültü Türüne Göre PESQ & STOI & SI-SDR", "Cafe, Street, Car ve Babble gürültü türlerinde yöntem başarımları"))
                    if noise_img:
                        gr.Image(value=noise_img, show_label=False, show_download_button=True, elem_classes=["plot-frame"])
                    else:
                        gr.HTML("<p style='color:#94a3b8; padding:16px;'>Grafik henüz oluşturulmadı.</p>")

                # ── Yenile Butonu ──
                btn_refresh = gr.Button("🔄 Sonuçları Yenile", variant="secondary")

                def refresh_results():
                    return get_analysis_summary_html(), get_improvement_html()

                btn_refresh.click(
                    fn=refresh_results,
                    outputs=[summary_table_html, improvement_html]
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
