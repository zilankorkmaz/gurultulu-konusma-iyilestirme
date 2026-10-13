import numpy as np
import librosa

from preprocess import load_audio, save_audio


def spectral_subtraction(audio, sample_rate, alpha=1.5):
    n_fft = 512
    hop_length = 128

    stft = librosa.stft(
        audio,
        n_fft=n_fft,
        hop_length=hop_length
    )

    magnitude = np.abs(stft)
    phase = np.angle(stft)

    noise_profile = 2.0 * np.percentile(
        magnitude,
        20,
        axis=1,
        keepdims=True
    )

    clean_magnitude = np.maximum(
        magnitude - alpha * noise_profile,
        0.02 * magnitude
    )

    enhanced_stft = clean_magnitude * np.exp(1j * phase)

    enhanced_audio = librosa.istft(
        enhanced_stft,
        hop_length=hop_length,
        length=len(audio)
    )
    enhanced_audio = enhanced_audio / (np.max(np.abs(enhanced_audio)) + 1e-9) * 0.9
    return enhanced_audio


if __name__ == "__main__":
    audio, sr = load_audio("data/noisy/noisy/classroom sound.mp3")

    enhanced = spectral_subtraction(audio, sr)

    save_audio("outputs/spectral_subtraction.wav", enhanced, sr)
    print("Spektral çıkarma tamamlandı.")