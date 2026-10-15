"""Birleşik İşleme Servisi (Pipeline Katmanı).

Bu modül, Gradio arayüzünden gelen ses verilerini (dosya yolu veya canlı mikrofon kaydı)
standart 16 kHz mono formata dönüştürür, istenen gürültü azaltma algoritmalarını
(Spektral Çıkarma, Wiener Filtresi, DeepFilterNet) çalıştırır ve
görselleştirme çıktısıyla birlikte arayüzün beklediği paketi üretir.
"""

import os
import time
import tempfile
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, Union

import numpy as np
import soundfile as sf
import librosa

# Algoritma modüllerini içe aktar
from preprocess import TARGET_SAMPLE_RATE
from spectral_subtraction import spectral_subtraction
from wiener_filter import wiener_filter
from visualization import create_comparison_plot

# DeepFilterNet için Lazy (Tembel) Model Yükleyici
_DF_MODEL = None
_DF_STATE = None
_DF_AVAILABLE = None


def _get_deepfilternet():
    """DeepFilterNet modelini belleğe bir kez yükler (Singleton)."""
    global _DF_MODEL, _DF_STATE, _DF_AVAILABLE
    if _DF_AVAILABLE is False:
        return None, None
    if _DF_MODEL is not None:
        return _DF_MODEL, _DF_STATE

    try:
        import torch
        from df.enhance import init_df
        # Modeli başlat (İlk seferde indirir veya yerel önbellekten alır)
        _DF_MODEL, _DF_STATE, _ = init_df(log_level="ERROR")
        _DF_AVAILABLE = True
        return _DF_MODEL, _DF_STATE
    except Exception as e:
        print(f"[UYARI] DeepFilterNet yüklenemedi: {e}")
        _DF_AVAILABLE = False
        return None, None


def enhance_with_deepfilternet(audio: np.ndarray, sr: int) -> np.ndarray:
    """Tek bir ses dizisi üzerinde DeepFilterNet ile gürültü temizleme uygular."""
    model, df_state = _get_deepfilternet()
    if model is None:
        raise RuntimeError("DeepFilterNet modeli yüklenemedi. Gerekli paketlerin kurulu olduğundan emin olun.")

    import torch
    import torchaudio
    from df.enhance import enhance

    model_sr = df_state.sr()  # 48000 Hz
    # Model 48 kHz beklediği için gerekirse 48 kHz'e dönüştür
    if sr != model_sr:
        audio_48k = librosa.resample(audio, orig_sr=sr, target_sr=model_sr)
    else:
        audio_48k = audio

    tensor_in = torch.from_numpy(audio_48k).float().unsqueeze(0)
    with torch.no_grad():
        enhanced_tensor = enhance(model, df_state, tensor_in)

    # Çıktıyı tekrar 16 kHz standart frekansa dönüştür
    to_16k = torchaudio.transforms.Resample(model_sr, TARGET_SAMPLE_RATE)
    enhanced_16k = to_16k(enhanced_tensor).squeeze(0).cpu().numpy()

    # Normalizasyon
    max_val = np.max(np.abs(enhanced_16k)) + 1e-9
    enhanced_16k = (enhanced_16k / max_val) * 0.9
    return enhanced_16k


def load_input_audio(audio_input: Any, target_sr: int = TARGET_SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """Gradio'dan gelen dosya yolu ya da mikrofon dizisini 16 kHz mono numpy dizisine dönüştürür."""
    if audio_input is None:
        raise ValueError("Lütfen bir ses dosyası yükleyin veya mikrofonla kayıt yapın.")

    # 1. Durum: Dosya Yolu (str veya Path)
    if isinstance(audio_input, (str, Path)):
        audio, sr = librosa.load(str(audio_input), sr=target_sr, mono=True)
        return audio, sr

    # 2. Durum: Gradio Mikrofon Tuple'ı (sr, numpy_array)
    if isinstance(audio_input, tuple):
        sr, data = audio_input
        if data is None or len(data) == 0:
            raise ValueError("Kayıt edilen ses boş görünüyor.")

        # Çok kanallı (stereo) ise ortalamasını alıp mono yap
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # Integer veri tiplerini [-1.0, 1.0] aralığına normalize et
        if np.issubdtype(data.dtype, np.integer):
            max_int = np.iinfo(data.dtype).max
            data = data.astype(np.float32) / float(max_int)
        else:
            data = data.astype(np.float32)

        # Hedef örnekleme frekansına dönüştür
        if sr != target_sr:
            data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
            sr = target_sr

        return data, sr

    raise TypeError(f"Desteklenmeyen ses girdi formatı: {type(audio_input)}")


def save_temp_wav(audio: np.ndarray, sr: int = TARGET_SAMPLE_RATE) -> str:
    """Ses dizisini geçici bir .wav dosyasına yazar ve dosya yolunu döndürür."""
    temp_dir = Path(tempfile.gettempdir()) / "gurultu_iyilestirme_cache"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"enhanced_{time.time_ns()}.wav"
    sf.write(str(temp_path), audio, sr)
    return str(temp_path)


def process_audio_pipeline(
    audio_input: Any,
    method: str = "Tümünü Karşılaştır",
    alpha: float = 1.5
) -> Tuple[Optional[str], Optional[str], Optional[str], Any, str]:
    """Tüm arayüz işlemlerini yürüten ana pipeline fonksiyonu.

    Args:
        audio_input: Dosya yolu veya mikrofon verisi.
        method: "Spektral Çıkarma", "Wiener Filtresi", "DeepFilterNet" veya "Tümünü Karşılaştır".
        alpha: Spektral çıkarma için aşırı çıkarma katsayısı.

    Returns:
        (spectral_wav, wiener_wav, deepfilter_wav, matplotlib_fig, status_message)
    """
    try:
        t_start = time.perf_counter()
        audio, sr = load_input_audio(audio_input)
        duration = len(audio) / sr

        audio_dict = {"Gürültülü (Girdi)": (audio, sr)}
        spectral_out = None
        wiener_out = None
        deepfilter_out = None
        processed_methods = []

        # 1. Spektral Çıkarma
        if method in ["Spektral Çıkarma", "Tümünü Karşılaştır"]:
            enhanced_ss = spectral_subtraction(audio, sr, alpha=alpha)
            spectral_out = save_temp_wav(enhanced_ss, sr)
            audio_dict["Spektral Çıkarma"] = (enhanced_ss, sr)
            processed_methods.append("Spektral Çıkarma")

        # 2. Wiener Filtresi
        if method in ["Wiener Filtresi", "Tümünü Karşılaştır"]:
            enhanced_wf = wiener_filter(audio, sr)
            wiener_out = save_temp_wav(enhanced_wf, sr)
            audio_dict["Wiener Filtresi"] = (enhanced_wf, sr)
            processed_methods.append("Wiener Filtresi")

        # 3. DeepFilterNet
        if method in ["DeepFilterNet", "Tümünü Karşılaştır"]:
            try:
                enhanced_df = enhance_with_deepfilternet(audio, sr)
                deepfilter_out = save_temp_wav(enhanced_df, sr)
                audio_dict["DeepFilterNet"] = (enhanced_df, sr)
                processed_methods.append("DeepFilterNet")
            except Exception as e:
                print(f"[UYARI] DeepFilterNet çalıştırılamadı: {e}")
                if method == "DeepFilterNet":
                    return None, None, None, None, f"❌ DeepFilterNet Hatası: {e}"

        # Görselleştirme Grafiği Üret
        fig = create_comparison_plot(
            audio_dict,
            title=f"Karşılaştırmalı Analiz ({', '.join(processed_methods)})"
        )

        total_time = time.perf_counter() - t_start
        status_msg = (
            f"✅ **İşlem Tamamlandı!**\n\n"
            f"- **Uygulanan:** {', '.join(processed_methods)}\n"
            f"- **Ses Süresi:** {duration:.2f} saniye\n"
            f"- **Örnekleme Frekansı:** {sr} Hz\n"
            f"- **Toplam İşlem Süresi:** {total_time:.2f} saniye (RTF: {total_time / duration:.2f})"
        )

        return spectral_out, wiener_out, deepfilter_out, fig, status_msg

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return None, None, None, None, f"❌ **Hata Oluştu:** {str(exc)}"
