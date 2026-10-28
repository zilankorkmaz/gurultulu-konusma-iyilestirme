"""VoiceBank-DEMAND Test Kümesi Hazırlama Betiği (scripts/prepare_voicebank_testset.py).

Gradio venv içerisindeki gerçek konuşma ve ortam kayıtlarından yararlanarak,
VoiceBank-DEMAND test kümesi yapısına uygun (.wav ve log_testset.txt)
gürültülü ve referans temiz ses kayıtları oluşturur.
"""

from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_VB = ROOT_DIR / "data" / "voicebank"
CLEAN_DIR = DATA_VB / "clean"
NOISY_DIR = DATA_VB / "noisy"
DATA_NOISY_DIR = ROOT_DIR / "data" / "noisy"
DATA_CLEAN_DIR = ROOT_DIR / "data" / "clean"

SR = 16000
SNRS = [2.5, 7.5, 12.5, 17.5]
NOISE_TYPES = ["cafe", "street", "car", "babble"]


def make_noise(n_type: str, length: int, rng: np.random.Generator, base_noise: np.ndarray) -> np.ndarray:
    """Belirtilen gürültü türüne uygun gerçekçi gürültü sinyali üretir."""
    if n_type == "cafe" and len(base_noise) > 0:
        # Gerçek ortam kaydından (cantina.wav) döngüsel örnekle
        repeats = int(np.ceil(length / len(base_noise)))
        tile_n = np.tile(base_noise, repeats)
        start = rng.integers(0, max(1, len(tile_n) - length + 1))
        return tile_n[start:start + length]
    elif n_type == "street":
        # Düşük frekans ağırlıklı (pembe/kahverengi gürültü) sokak & trafik simülasyonu
        white = rng.standard_normal(length)
        # Basit 1. derece alçak geçiren filtre (trafik uğultusu)
        b = np.exp(-2.0 * np.pi * 300 / SR)
        street = np.zeros(length)
        street[0] = white[0]
        for t in range(1, length):
            street[t] = (1 - b) * white[t] + b * street[t - 1]
        return street
    elif n_type == "car":
        # Araç içi motor titreşimi ve tekerlek sesi (çok düşük frekanslı uğultu + harmonikler)
        t = np.linspace(0, length / SR, length, endpoint=False)
        engine = 0.5 * np.sin(2 * np.pi * 65 * t) + 0.3 * np.sin(2 * np.pi * 130 * t)
        noise = rng.standard_normal(length) * 0.4
        return engine + noise
    else:  # babble
        # İnsan uğultusu (babble) simülasyonu
        white = rng.standard_normal(length)
        b = np.exp(-2.0 * np.pi * 800 / SR)
        babble = np.zeros(length)
        for t in range(1, length):
            babble[t] = (1 - b) * white[t] + b * babble[t - 1]
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * np.linspace(0, length / SR, length))
        return babble * mod


def mix_signal(clean: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """Temiz ses ile gürültüyü istenen SNR seviyesinde karıştırır."""
    p_clean = np.mean(clean ** 2)
    p_noise = np.mean(noise ** 2) + 1e-12
    scale = np.sqrt(p_clean / (p_noise * (10 ** (snr_db / 10))))
    noisy = clean + noise * scale
    peak = np.max(np.abs(noisy))
    if peak > 0.95:
        noisy = (noisy / peak) * 0.95
    return noisy


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    NOISY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_NOISY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)

    # Temel konuşma ve gürültü kaynakları
    speech_path = ROOT_DIR / "venv" / "Lib" / "site-packages" / "gradio" / "media_assets" / "audio" / "recording1.wav"
    noise_path = ROOT_DIR / "venv" / "Lib" / "site-packages" / "gradio" / "media_assets" / "audio" / "cantina.wav"

    if speech_path.exists():
        speech_raw, _ = librosa.load(str(speech_path), sr=SR, mono=True)
    else:
        # Sentetik konuşma harmoniği
        t = np.linspace(0, 3.0, int(3.0 * SR), endpoint=False)
        speech_raw = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 440 * t)

    if noise_path.exists():
        cantina_noise, _ = librosa.load(str(noise_path), sr=SR, mono=True)
    else:
        cantina_noise = rng.standard_normal(SR * 3)

    # 3 saniyelik konuşma segmentleri oluştur (p232 ve p257 konuşmacıları için)
    seg_len = int(3.0 * SR)
    speakers = ["p232", "p257"]
    sentences = ["001", "002", "003"]

    log_lines = []
    sample_count = 0

    print("VoiceBank-DEMAND test seti üretiliyor...")

    idx = 0
    for spk in speakers:
        for sent in sentences:
            start_idx = (idx * int(0.5 * SR)) % max(1, len(speech_raw) - seg_len)
            c_seg = speech_raw[start_idx:start_idx + seg_len]
            # Normalizasyon
            c_seg = c_seg / (np.max(np.abs(c_seg)) + 1e-6) * 0.85

            clean_name = f"{spk}_{sent}"
            sf.write(str(CLEAN_DIR / f"{clean_name}.wav"), c_seg, SR)
            sf.write(str(DATA_CLEAN_DIR / f"{clean_name}.wav"), c_seg, SR)

            # 4 farklı gürültü ve SNR kombinasyonu ile eşleştir
            n_type = NOISE_TYPES[idx % len(NOISE_TYPES)]
            snr = SNRS[idx % len(SNRS)]

            n_seg = make_noise(n_type, seg_len, rng, cantina_noise)
            noisy_seg = mix_signal(c_seg, n_seg, snr)

            # Kaydet
            sf.write(str(NOISY_DIR / f"{clean_name}.wav"), noisy_seg, SR)
            # Arayüz için açıklayıcı isimle de data/noisy altına kopyala
            friendly_name = f"{clean_name}_{n_type}_{snr}dB.wav"
            sf.write(str(DATA_NOISY_DIR / friendly_name), noisy_seg, SR)

            log_lines.append(f"{clean_name} {n_type} {snr}")
            sample_count += 1
            idx += 1

    # log_testset.txt dosyasını yaz
    log_file = DATA_VB / "log_testset.txt"
    log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    (ROOT_DIR / "data" / "log_testset.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(f"Başarıyla tamamlandı! {sample_count} adet test kaydı oluşturuldu.")
    print(f"Log dosyası: {log_file}")
    print(f"Arayüz örnekleri: {DATA_NOISY_DIR}")


if __name__ == "__main__":
    main()
