from pathlib import Path

import librosa
import soundfile as sf
import numpy as np

TARGET_SAMPLE_RATE = 16000


def load_audio(file_path, target_sr=TARGET_SAMPLE_RATE):
    audio, sample_rate = librosa.load(
        file_path,
        sr=target_sr,
        mono=True
    )
    return audio, sample_rate


def save_audio(file_path, audio, sample_rate=TARGET_SAMPLE_RATE):
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(file_path, audio, sample_rate)

def mix_at_snr(clean, noise, snr_db):
    if len(noise) < len(clean):
        noise = np.tile(noise, int(np.ceil(len(clean) / len(noise))))
    start = np.random.randint(0, len(noise) - len(clean) + 1)
    noise = noise[start:start + len(clean)]

    p_clean = np.mean(clean ** 2)
    p_noise = np.mean(noise ** 2) + 1e-12
    scale = np.sqrt(p_clean / (p_noise * 10 ** (snr_db / 10)))
    return clean + scale * noise

if __name__ == "__main__":
    input_path = "data/noisy/noisy/classroom sound.mp3"
    output_path = "outputs/on_islenmis.wav"

    audio, sample_rate = load_audio(input_path)
    save_audio(output_path, audio, sample_rate)

    print(f"Örnekleme frekansı: {sample_rate} Hz")
    print(f"Ses uzunluğu: {len(audio) / sample_rate:.2f} saniye")
    print(f"Kaydedildi: {output_path}")