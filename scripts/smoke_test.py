"""Uçtan uca deneme: küçük bir sentetik test kümesi üretir, DeepFilterNet'i çalıştırır,
ölçütleri hesaplar ve analiz betiğini çağırır.

Gerçek VoiceBank-DEMAND verisi gelene kadar boru hattının çalıştığını doğrulamak içindir.
Ölçüt hesaplama kısmı geçicidir; ekibin değerlendirme modülü (src/metrics.py) hazır olunca
onunla değiştirilecektir.

Kullanım:
    python scripts/smoke_test.py --clean temiz.wav --noise trafik.wav --noise kafe.wav \
        --model_dir models/DeepFilterNet3 --work_dir smoke
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import librosa
import soundfile as sf
from pesq import pesq
from pystoi import stoi

SR = 16000
SNRS = [2.5, 7.5, 12.5, 17.5]  # VoiceBank-DEMAND test kümesinin SNR seviyeleri


def si_sdr(ref, est):
    ref, est = ref - ref.mean(), est - est.mean()
    a = np.dot(est, ref) / (np.dot(ref, ref) + 1e-12)
    t = a * ref
    return 10 * np.log10(np.sum(t ** 2) / (np.sum((est - t) ** 2) + 1e-12))


def mix(clean, noise, snr_db, rng):
    if len(noise) < len(clean):
        noise = np.tile(noise, int(np.ceil(len(clean) / len(noise))))
    start = rng.integers(0, len(noise) - len(clean) + 1)
    n = noise[start:start + len(clean)]
    pc, pn = np.mean(clean ** 2), np.mean(n ** 2) + 1e-12
    noisy = clean + n * np.sqrt(pc / (pn * 10 ** (snr_db / 10)))
    peak = np.max(np.abs(noisy))
    return noisy / peak * 0.9 if peak > 0.99 else noisy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", required=True)
    ap.add_argument("--noise", action="append", required=True)
    ap.add_argument("--model_dir", default=None)
    ap.add_argument("--work_dir", default="smoke")
    ap.add_argument("--segment_s", type=float, default=3.5)
    args = ap.parse_args()

    w = Path(args.work_dir)
    for d in ("clean", "noisy"):
        (w / d).mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)

    clean_all, _ = librosa.load(args.clean, sr=SR, mono=True)
    seg = int(args.segment_s * SR)
    segments = [clean_all[i:i + seg] for i in range(0, len(clean_all) - seg + 1, seg)]
    log = []
    for npath in args.noise:
        noise, _ = librosa.load(npath, sr=SR, mono=True)
        ntype = Path(npath).stem.replace("noise_", "")
        for si, c in enumerate(segments):
            for snr in SNRS:
                name = f"s{si}_{ntype}_{snr}"
                sf.write(w / "clean" / f"{name}.wav", c, SR)
                sf.write(w / "noisy" / f"{name}.wav", mix(c, noise, snr, rng), SR)
                log.append(f"{name} {ntype} {snr}")
    (w / "log_testset.txt").write_text("\n".join(log), encoding="utf-8")
    print(f"{len(log)} gürültülü kayıt üretildi.")

    cmd = [sys.executable, str(Path(__file__).parents[1] / "src" / "enhance_deepfilternet.py"),
           "--input_dir", str(w / "noisy"), "--output_dir", str(w / "deepfilternet")]
    if args.model_dir:
        cmd += ["--model_dir", args.model_dir]
    subprocess.run(cmd, check=True)

    rows = []
    for f in sorted((w / "clean").glob("*.wav")):
        ref, _ = librosa.load(f, sr=SR)
        for method, d in (("noisy", "noisy"), ("deepfilternet", "deepfilternet")):
            est, _ = librosa.load(w / d / f.name, sr=SR)
            n = min(len(ref), len(est))
            r, e = ref[:n], est[:n]
            rows.append({"file": f.stem, "method": method, "pesq": pesq(SR, r, e, "wb"),
                         "stoi": stoi(r, e, SR, extended=False), "si_sdr": si_sdr(r, e)})
    pd.DataFrame(rows).to_csv(w / "metrics.csv", index=False)

    subprocess.run([sys.executable, str(Path(__file__).parents[1] / "src" / "analysis.py"),
                    "--results", str(w / "metrics.csv"), "--testset_log", str(w / "log_testset.txt"),
                    "--out_dir", str(w / "analysis")], check=True)


if __name__ == "__main__":
    main()
