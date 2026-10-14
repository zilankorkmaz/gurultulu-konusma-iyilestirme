import csv
from collections import Counter
from pathlib import Path

from preprocess import load_audio, save_audio
from spectral_subtraction import spectral_subtraction
from wiener_filter import wiener_filter

PROJE = Path(__file__).resolve().parent.parent
VB_KLASORU = PROJE / "data" / "voicebank"
CIKIS = PROJE / "outputs" / "voicebank"


def log_dosyasini_bul():
    for yol in VB_KLASORU.rglob("log_testset.txt"):
        return yol
    return None


def log_oku(log_yolu):
    bilgi = {}
    if log_yolu is None:
        return bilgi
    metin = log_yolu.read_text(encoding="utf-8", errors="ignore")
    for satir in metin.splitlines():
        parca = satir.split()
        if len(parca) < 3:
            continue
        try:
            snr = float(parca[-1])
        except ValueError:
            continue
        ad = parca[0].replace(".wav", "")
        gurultu = " ".join(parca[1:-1])
        bilgi[ad] = (gurultu, snr)
    return bilgi


def main():
    dosyalar = sorted(
        f for f in VB_KLASORU.rglob("*.wav")
        if "noisy" in f.parent.name.lower()
    )

    if not dosyalar:
        print("data/voicebank içinde gürültülü kayıt bulunamadı.")
        return

    log_yolu = log_dosyasini_bul()
    bilgi = log_oku(log_yolu)
    print(f"{len(dosyalar)} dosya bulundu, log'da {len(bilgi)} kayıt var.")

    sayac = Counter(bilgi.values())
    print("Gürültü türü ve SNR dağılımı:")
    for (gurultu, snr), adet in sorted(sayac.items()):
        print(f"  {gurultu:12s} {snr:5.1f} dB  ->  {adet} kayıt")
    print()

    CIKIS.mkdir(parents=True, exist_ok=True)
    liste_yolu = CIKIS / "dosya_listesi.csv"

    with open(liste_yolu, "w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(["dosya", "gurultu", "snr_db"])

        for i, dosya in enumerate(dosyalar, start=1):
            gurultu, snr = bilgi.get(dosya.stem, ("bilinmiyor", ""))
            yazici.writerow([dosya.name, gurultu, snr])

            try:
                audio, sr = load_audio(str(dosya))

                ss = spectral_subtraction(audio, sr)
                save_audio(
                    str(CIKIS / "spectral_subtraction" / dosya.name), ss, sr
                )

                wf = wiener_filter(audio, sr)
                save_audio(
                    str(CIKIS / "wiener_filter" / dosya.name), wf, sr
                )
            except Exception as e:
                print(f"HATA ({dosya.name}): {e}")

            if i % 50 == 0 or i == len(dosyalar):
                print(f"{i}/{len(dosyalar)} işlendi")

    print(f"\nBitti. Sonuçlar: {CIKIS}")
    print(f"Dosya listesi: {liste_yolu}")


if __name__ == "__main__":
    main()