from pathlib import Path
import shutil
from preprocess import load_audio, save_audio
from spectral_subtraction import spectral_subtraction
from wiener_filter import wiener_filter

PROJE_KLASORU = Path(__file__).resolve().parent.parent
GIRIS_KLASORU = PROJE_KLASORU / "data" / "noisy"
CIKIS_KLASORU = PROJE_KLASORU / "outputs"

SES_UZANTILARI = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}

def eski_sonuclari_sil():
    for klasor in ["spectral_subtraction", "wiener_filter"]:
        yol = CIKIS_KLASORU / klasor
        if yol.exists():
            shutil.rmtree(yol)
    print("Eski sonuçlar silindi.\n")

def main():
    dosyalar = sorted(
        f for f in GIRIS_KLASORU.rglob("*")
        if f.suffix.lower() in SES_UZANTILARI
    )

    if not dosyalar:
        print("data/noisy içinde ses dosyası bulunamadı.")
        return

    print(f"{len(dosyalar)} dosya bulundu.\n")
    eski_sonuclari_sil()
    for i, dosya in enumerate(dosyalar, start=1):
        print(f"[{i}/{len(dosyalar)}] {dosya.name}")
        try:
            audio, sr = load_audio(str(dosya))

            ss = spectral_subtraction(audio, sr)
            save_audio(
                str(CIKIS_KLASORU / "spectral_subtraction" / f"{dosya.stem}.wav"),
                ss, sr
            )

            wf = wiener_filter(audio, sr)
            save_audio(
                str(CIKIS_KLASORU / "wiener_filter" / f"{dosya.stem}.wav"),
                wf, sr
            )
        except Exception as e:
            print(f"   HATA: {e}")

    print("\nTüm dosyalar işlendi.")


if __name__ == "__main__":
    main()