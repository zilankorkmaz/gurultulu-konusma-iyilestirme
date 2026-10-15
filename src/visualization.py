"""Ses görselleştirme modülü (Dalga Formu ve Spektrogram).

Bu modül, orijinal gürültülü ses ile filtrelenmiş seslerin zaman ve frekans
uzayındaki değişimlerini yan yana görselleştirerek Gradio ve analiz çıktıları için
yüksek kaliteli Matplotlib figürleri üretir.
"""

from typing import Dict, Tuple, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Başsız (headless) ortamlar ve web UI için GUI gerektirmeyen backend
import matplotlib.pyplot as plt
import librosa


# Grafik renk paleti (Gürültülü: Gri/Kırmızımsı, Yöntemler: Belirgin renkler)
SIGNAL_COLORS = {
    "noisy": "#d9534f",               # Kırmızımsı / Uyarı
    "spectral_subtraction": "#0275d8", # Mavi
    "wiener_filter": "#f0ad4e",        # Turuncu / Amber
    "deepfilternet": "#5cb85c",        # Yeşil / Başarı
    "default": "#5bc0de"
}


def _get_color(name: str) -> str:
    lower_name = name.lower()
    for key, color in SIGNAL_COLORS.items():
        if key in lower_name:
            return color
    return SIGNAL_COLORS["default"]


def create_comparison_plot(
    audio_dict: Dict[str, Tuple[np.ndarray, int]],
    title: str = "Gürültü Azaltma Karşılaştırmalı Analizi",
    max_duration: Optional[float] = 10.0
) -> plt.Figure:
    """Birden çok ses sinyali için Dalga Formu (Waveform) ve Spektrogram (Spectrogram) çizer.

    Args:
        audio_dict: { "Etiket": (audio_numpy_array, sample_rate) } biçiminde sözlük.
        title: Figürün üst ana başlığı.
        max_duration: Görselleştirme için maksimum süre (sn). Çok uzun dosyalarda ilk N saniye gösterilir.

    Returns:
        matplotlib.figure.Figure: Gradio `gr.Plot` ile doğrudan gösterilebilecek figür.
    """
    if not audio_dict:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "Görüntülenecek ses verisi yok.", ha="center", va="center")
        ax.axis("off")
        return fig

    num_signals = len(audio_dict)
    fig, axes = plt.subplots(
        nrows=num_signals,
        ncols=2,
        figsize=(14, 2.8 * num_signals),
        squeeze=False
    )
    fig.suptitle(title, fontsize=15, fontweight="bold", y=0.99)

    for idx, (label, (audio, sr)) in enumerate(audio_dict.items()):
        # Çok uzun sesleri sınırla
        if max_duration is not None and len(audio) > int(max_duration * sr):
            audio = audio[: int(max_duration * sr)]

        duration = len(audio) / sr
        time_axis = np.linspace(0, duration, len(audio))
        color = _get_color(label)

        # 1. SÜTUN: Dalga Formu (Waveform)
        ax_wave = axes[idx][0]
        ax_wave.plot(time_axis, audio, color=color, alpha=0.85, linewidth=0.8)
        ax_wave.set_title(f"{label} - Dalga Formu (Zaman Uzayı)", fontsize=11, fontweight="semibold")
        ax_wave.set_ylabel("Genlik", fontsize=10)
        ax_wave.set_xlim(0, duration)
        ax_wave.set_ylim(-1.05, 1.05)
        ax_wave.grid(True, linestyle="--", alpha=0.4)
        if idx == num_signals - 1:
            ax_wave.set_xlabel("Zaman (saniye)", fontsize=10)

        # 2. SÜTUN: Spektrogram (STFT Frekans-Zaman Uzayı)
        ax_spec = axes[idx][1]
        n_fft = 512
        hop_length = 128
        stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
        magnitude = np.abs(stft)
        # dB ölçeğine dönüştür (Gürültü farkının net görünmesi için)
        spec_db = librosa.amplitude_to_db(magnitude, ref=np.max)

        img = ax_spec.imshow(
            spec_db,
            aspect="auto",
            origin="lower",
            extent=[0, duration, 0, sr / 2000],  # Frekans kHz cinsinden
            cmap="magma",
            vmin=-80,
            vmax=0
        )
        ax_spec.set_title(f"{label} - Spektrogram (Frekans Uzayı)", fontsize=11, fontweight="semibold")
        ax_spec.set_ylabel("Frekans (kHz)", fontsize=10)
        if idx == num_signals - 1:
            ax_spec.set_xlabel("Zaman (saniye)", fontsize=10)

        # Renk çubuğu (dB seviyesi)
        cbar = fig.colorbar(img, ax=ax_spec, format="%+2.0f dB", pad=0.02)
        cbar.ax.tick_params(labelsize=8)

    plt.tight_layout()
    return fig
