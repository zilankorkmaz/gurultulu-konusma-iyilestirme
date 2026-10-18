"""UI HTML Bileşenleri ve Şablonları (ui/components.py).

Gradio arayüzünde kullanılan modüler HTML bileşenleri ve kart şablonları.
"""

def hero_header() -> str:
    """Sayfa tepe hero başlık kartı."""
    return """
    <div class="header-hero">
        <div class="header-top">
            <div class="header-icon-box">🎙️</div>
            <div class="header-titles">
                <h1>AudioDenoiser</h1>
                <p>Yapay Zeka & Dijital Sinyal İşleme Tabanlı Profesyonel Ses İyileştirme Platformu</p>
            </div>
        </div>
        <div class="header-badges">
            <span class="hero-pill">⚡ DeepFilterNet v3 (Derin Öğrenme / SOTA)</span>
            <span class="hero-pill">🎛️ MMSE Wiener Filtresi</span>
            <span class="hero-pill">📊 Spektral Çıkarma (STFT)</span>
            <span class="hero-pill">📈 Frekans-Zaman Spektrogram Analizi</span>
        </div>
    </div>
    """


def card_header(icon: str, title: str, desc: str) -> str:
    """Panel kartları için başlık, ikon ve açıklama şablonu."""
    return f"""
    <div class="panel-card-header">
        <div class="panel-card-icon">{icon}</div>
        <div>
            <div class="panel-card-title">{title}</div>
            <div class="panel-card-desc">{desc}</div>
        </div>
    </div>
    """


def audio_track_header(title: str, pill_text: str, pill_class: str) -> str:
    """Ses çıktı kartı için özel başlık ve rozet."""
    return f"""
    <div class="audio-track-header">
        <span class="audio-track-title">{title}</span>
        <span class="audio-track-pill {pill_class}">{pill_text}</span>
    </div>
    """


def metrics_table_html(metrics_dict: dict) -> str:
    """Hesaplanan PESQ, STOI ve SI-SDR metriklerini şık bir HTML tablosu olarak döndürür."""
    if not metrics_dict:
        return """
        <div style="padding: 18px 22px; background: #ffffff !important; border-radius: 10px; border: 1.5px dashed #64748b; color: #0f172a !important; font-size: 0.95rem; text-align: center; line-height: 1.6; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="font-size: 1.3rem; margin-bottom: 6px;">💡</div>
            <div style="font-weight: 800; color: #0f172a !important; font-size: 1.05rem; margin-bottom: 6px;">Referans Temiz Ses Yüklenmedi</div>
            <div style="color: #1e293b !important; font-size: 0.95rem; font-weight: 500;">Sayısal kalite puanlarını (PESQ, STOI, SI-SDR) görmek için sol paneldeki <strong style="color: #2563eb !important; font-weight: 700;">'2. Referans Temiz Ses'</strong> kartına orijinal temiz ses kaydını yükleyebilirsiniz.</div>
        </div>

        """

    rows = []
    for method, scores in metrics_dict.items():
        pesq_val = scores.get("pesq")
        pesq_str = f"{pesq_val:.2f}" if pesq_val is not None else "—"
        stoi_val = scores.get("stoi")
        stoi_str = f"{stoi_val:.3f}" if stoi_val is not None else "—"
        sdr_val = scores.get("si_sdr")
        sdr_str = f"{sdr_val:+.1f} dB" if sdr_val is not None else "—"

        rows.append(f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 16px; font-weight: 700; color: #0f172a !important;">{method}</td>
            <td style="padding: 12px 16px; text-align: center; color: #1d4ed8 !important; font-weight: 700; font-size: 1rem;">{pesq_str}</td>
            <td style="padding: 12px 16px; text-align: center; color: #047857 !important; font-weight: 700; font-size: 1rem;">{stoi_str}</td>
            <td style="padding: 12px 16px; text-align: center; color: #b45309 !important; font-weight: 700; font-size: 1rem;">{sdr_str}</td>
        </tr>
        """)

    return f"""
    <div style="overflow-x: auto; border: 1px solid #cbd5e1; border-radius: 10px; background: #ffffff !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.92rem; text-align: left;">
            <thead>
                <tr style="background: #f1f5f9 !important; border-bottom: 2px solid #cbd5e1; color: #1e293b !important;">
                    <th style="padding: 12px 16px; font-weight: 700; color: #1e293b !important;">Yöntem / Model</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b !important;">PESQ (Kalite 1-4.5)</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b !important;">STOI (Anlaşılabilirlik 0-1)</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b !important;">SI-SDR (Gürültü Bastırma)</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """


