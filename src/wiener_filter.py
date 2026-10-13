import numpy as np
import librosa

from preprocess import load_audio, save_audio


def wiener_filter(audio, sample_rate):
    n_fft = 512
    hop_length = 128

    stft = librosa.stft(
        audio,
        n_fft=n_fft,
        hop_length=hop_length
    )

    power = np.abs(stft) ** 2

    noise_power = 4.0 * np.percentile(
        power,
        20,
        axis=1,
        keepdims=True
    )

    estimated_clean_power = np.maximum(
        power - noise_power,
        1e-10
    )

    gain = estimated_clean_power / (
        estimated_clean_power + noise_power + 1e-10
    )

    gain = np.maximum(gain, 0.05)

    enhanced_stft = gain * stft

    enhanced_audio = librosa.istft(
        enhanced_stft,
        hop_length=hop_length,
        length=len(audio)
    )
    enhanced_audio = enhanced_audio / (np.max(np.abs(enhanced_audio)) + 1e-9) * 0.9
    return enhanced_audio


if __name__ == "__main__":
    audio, sr = load_audio("data/noisy/noisy/classroom sound.mp3")

    enhanced = wiener_filter(audio, sr)

    save_audio("outputs/wiener_filter.wav", enhanced, sr)
    print("Wiener filtresi tamamlandı.")