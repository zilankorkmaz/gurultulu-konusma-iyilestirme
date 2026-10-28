from pathlib import Path

from preprocess import load_audio, save_audio
from spectral_subtraction import spectral_subtraction
from wiener_filter import wiener_filter

PROJE = Path(__file__).resolve().parent.parent
GIRIS = PROJE / "data" / "extra_noise_set" / "noisy"
CIKIS = PROJE / "outputs" / "extra_noise"


def main():
    dosyalar = sorted(GIRIS.rglob("*.wav"))
    if not dosyalar:
        print("data/extra_noise_set/noisy içinde dosya bulunamadı.")
        return

    print(f"{len(dosyalar)} dosya bulundu.")

    for i, dosya in enumerate(dosyalar, start=1):
        goreli = dosya.relative_to(GIRIS)
        try:
            audio, sr = load_audio(str(dosya))

            ss = spectral_subtraction(audio, sr)
            save_audio(str(CIKIS / "spectral_subtraction" / goreli), ss, sr)

            wf = wiener_filter(audio, sr)
            save_audio(str(CIKIS / "wiener_filter" / goreli), wf, sr)
        except Exception as e:
            print(f"HATA ({goreli}): {e}")

        if i % 50 == 0 or i == len(dosyalar):
            print(f"{i}/{len(dosyalar)} işlendi")

    print(f"\nBitti. Sonuçlar: {CIKIS}")


if __name__ == "__main__":
    main()