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
