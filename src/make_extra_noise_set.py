import csv
from pathlib import Path

import numpy as np

from preprocess import load_audio, save_audio

PROJE = Path(__file__).resolve().parent.parent
VB_KLASORU = PROJE / "data"
GURULTU_KLASORU = PROJE / "data" / "extra_noise"
CIKIS = PROJE / "data" / "extra_noise_set"

SNR_SEVIYELERI = [2.5, 7.5, 12.5, 17.5]
KAYIT_SAYISI = 50
TOHUM = 42
SES_UZANTILARI = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def noise_name(index):
    """Gürültü dosyasını loglarda güvenle kullanılacak kısa bir ada çevirir."""
    return f"noise_{index:02d}"


def mix_at_snr(clean, noise, snr_db, rng):
    if len(noise) < len(clean):
        noise = np.tile(noise, int(np.ceil(len(clean) / len(noise))))
    baslangic = rng.integers(0, len(noise) - len(clean) + 1)
    noise = noise[baslangic:baslangic + len(clean)]

    p_clean = np.mean(clean ** 2)
    p_noise = np.mean(noise ** 2) + 1e-12
    olcek = np.sqrt(p_clean / (p_noise * 10 ** (snr_db / 10)))
    karisim = clean + olcek * noise

    tepe = np.max(np.abs(karisim))
    if tepe > 0.99:
        karisim = karisim / tepe * 0.99
    return karisim


def main():
    gurultuler = sorted(
        f for f in GURULTU_KLASORU.iterdir()
        if f.suffix.lower() in SES_UZANTILARI
    )
    if not gurultuler:
        print("data/extra_noise içinde ses dosyası bulunamadı.")
        return

    temiz = sorted(
        f for f in VB_KLASORU.rglob("*.wav")
        if "clean" in f.parent.name.lower()
    )
    if not temiz:
        print("data/voicebank içinde temiz kayıt bulunamadı.")
        return

    rng = np.random.default_rng(TOHUM)
    idx = rng.choice(len(temiz), size=min(KAYIT_SAYISI, len(temiz)), replace=False)
    secilen = [temiz[i] for i in sorted(idx)]

    print(f"{len(gurultuler)} gürültü, {len(SNR_SEVIYELERI)} SNR, {len(secilen)} temiz kayıt")

    CIKIS.mkdir(parents=True, exist_ok=True)
    liste_yolu = CIKIS / "dosya_listesi.csv"
    log_yolu = CIKIS / "log_testset.txt"

    with (
        open(liste_yolu, "w", newline="", encoding="utf-8") as csv_file,
        open(log_yolu, "w", encoding="utf-8") as log_file,
    ):
        yazici = csv.writer(csv_file)
        yazici.writerow(["id", "dosya", "gurultu", "snr_db"])
        kayit_id = 1

        for g_index, g_yol in enumerate(gurultuler, start=1):
            gurultu_adi = noise_name(g_index)
            gurultu, _ = load_audio(str(g_yol))
            for snr in SNR_SEVIYELERI:
                for yol in secilen:
                    kayit_adi = f"extra_{kayit_id:04d}.wav"
                    kayit_id += 1
                    temiz_ses, sr = load_audio(str(yol))
                    karisim = mix_at_snr(temiz_ses, gurultu, snr, rng)
                    hedef = CIKIS / "noisy" / gurultu_adi / f"{snr}dB" / kayit_adi
                    save_audio(str(hedef), karisim, sr)
                    kayit_id_str = hedef.stem
                    yazici.writerow([
                        kayit_id_str,
                        hedef.relative_to(CIKIS).as_posix(),
                        gurultu_adi,
                        snr,
                    ])
                    log_file.write(f"{kayit_id_str} {gurultu_adi} {snr}\n")
            print(f"{gurultu_adi} ({g_yol.name}) tamam")

    print(f"\nBitti. Sonuçlar: {CIKIS}")
    print(f"Dosya listesi: {liste_yolu}")
    print(f"Analiz günlüğü: {log_yolu}")


if __name__ == "__main__":
    main()
