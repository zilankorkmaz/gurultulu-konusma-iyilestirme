"""DeepFilterNet3 ile toplu konuşma iyileştirme.

Kullanım (proje kökünden):
    python src/enhance_deepfilternet.py                      # data/noisy -> outputs/deepfilternet
    python src/enhance_deepfilternet.py --input_dir data/noisy_testset_wav --limit 10

Girdi klasörünün alt klasör düzenini korur: örneğin
data/extra_noise_set/noisy/gürültü/12.5dB/dosya.wav,
outputs/extra_noise/deepfilternet/gürültü/12.5dB/dosya.wav olarak yazılır.

Notlar:
- DeepFilterNet 48 kHz ile çalışır. Girdi hangi örnekleme frekansında olursa olsun
  48 kHz'e çevrilip modele verilir, çıktı --out_sr (varsayılan 16 kHz) ile kaydedilir.
  PESQ (geniş bant) 16 kHz istediği için çıktıyı 16 kHz tutuyoruz.
- --model_dir verilmezse model ilk çalıştırmada otomatik indirilir.
"""
import argparse
import csv
import time
from pathlib import Path

import torch
import torchaudio
import librosa
from df.enhance import enhance, init_df

PROJE = Path(__file__).resolve().parent.parent
SES_UZANTILARI = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def main():
    ap = argparse.ArgumentParser(description="DeepFilterNet3 ile klasördeki tüm .wav dosyalarını iyileştirir.")
    ap.add_argument("--input_dir", default=str(PROJE / "data" / "noisy"), help="Gürültülü kayıtların klasörü")
    ap.add_argument("--output_dir", default=str(PROJE / "outputs" / "deepfilternet"), help="Çıktı klasörü")
    ap.add_argument("--model_dir", default=None, help="Yerel DeepFilterNet3 klasörü (yoksa otomatik indirilir)")
    ap.add_argument("--out_sr", type=int, default=16000, help="Çıktı örnekleme frekansı (varsayılan 16000)")
    ap.add_argument("--limit", type=int, default=None, help="Sadece ilk N dosyayı işle (deneme için)")
    args = ap.parse_args()

    in_dir, out_dir = Path(args.input_dir), Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(f for f in in_dir.rglob("*") if f.suffix.lower() in SES_UZANTILARI)[: args.limit]
    if not files:
        raise SystemExit(f"{in_dir} içinde ses dosyası bulunamadı.")

    model, df_state, _ = init_df(model_base_dir=args.model_dir, log_level="ERROR")
    model_sr = df_state.sr()  # 48000
    to_out = torchaudio.transforms.Resample(model_sr, args.out_sr) if args.out_sr != model_sr else None

    log_rows, total_audio, total_time = [], 0.0, 0.0
    for i, f in enumerate(files, 1):
        y, _ = librosa.load(str(f), sr=model_sr, mono=True)  # 48 kHz'e çevirir
        audio = torch.from_numpy(y).unsqueeze(0)
        t0 = time.perf_counter()
        with torch.no_grad():
            enhanced = enhance(model, df_state, audio)
        dt = time.perf_counter() - t0
        if to_out is not None:
            enhanced = to_out(enhanced)
        output_file = out_dir / f.relative_to(in_dir)
        output_file = output_file.with_suffix(".wav")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(output_file), enhanced.cpu(), args.out_sr)

        dur = audio.shape[-1] / model_sr
        total_audio, total_time = total_audio + dur, total_time + dt
        log_rows.append({"file": f.stem, "duration_s": round(dur, 3), "process_s": round(dt, 3), "rtf": round(dt / dur, 4)})
        print(f"[{i}/{len(files)}] {f.name}  süre={dur:.2f}s  işlem={dt:.2f}s")

    with open(out_dir / "_timing.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=log_rows[0].keys())
        w.writeheader()
        w.writerows(log_rows)
    print(f"\nBitti: {len(files)} dosya, toplam ses {total_audio:.1f}s, işlem {total_time:.1f}s, "
          f"gerçek zaman oranı (RTF) {total_time / total_audio:.3f}")


if __name__ == "__main__":
    main()
