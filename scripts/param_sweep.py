"""Klasik yöntemler için parametre analizi.

Spektral çıkarmada alpha, Wiener filtresinde gürültü çarpanı (noise_factor) için
farklı değerleri aynı kayıtlarda dener, PESQ/STOI/SI-SDR ortalamalarını karşılaştırır.
Ses dosyası kaydetmez; her şey bellekte yapılır.

Kullanım (proje kökünden):
  1) Tarama (200 kayıtlık ayar alt kümesi):
       python scripts/param_sweep.py
  2) Seçilen ayarlarla 824 kaydın tamamını ölç ve mevcut sonuçlarla birleştir:
       python scripts/param_sweep.py --final --ss_alpha 1.5 --wf_factor 8
     -> results/metrics_tuned.csv (noisy ve deepfilternet satırları results/metrics.csv'den alınır)
     Sonra: python src/analysis.py --results results/metrics_tuned.csv --testset_log data/voicebank/log_testset.txt --out_dir results/analysis_tuned

Not: Ayarlar test kümesinin rastgele bir alt kümesinde seçilir. En iyi ayar daha sonra
tüm 824 kayıtta raporlanır; raporda bunun bir sınırlılık olduğu belirtilmelidir.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE / "src"))

from preprocess import load_audio  # noqa: E402
from spectral_subtraction import spectral_subtraction  # noqa: E402
from wiener_filter import wiener_filter  # noqa: E402
from metrics import compute_metrics  # noqa: E402

SS_ALPHAS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]          # mevcut varsayılan: 1.5
WF_FACTORS = [1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0]             # mevcut varsayılan: 4.0
VARSAYILAN = {"spectral_subtraction": 1.5, "wiener_filter": 4.0}
METRIKLER = ["pesq", "stoi", "si_sdr"]


def main():
    ap = argparse.ArgumentParser(description="Klasik yöntemler için parametre analizi")
    ap.add_argument("--noisy_dir", default=str(PROJE / "data" / "voicebank" / "noisy_testset_wav"))
    ap.add_argument("--clean_dir", default=str(PROJE / "data" / "voicebank" / "clean_testset_wav"))
    ap.add_argument("--n", type=int, default=200, help="Kullanılacak kayıt sayısı (varsayılan 200)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out_dir", default=str(PROJE / "results" / "param_sweep"))
    ap.add_argument("--final", action="store_true", help="Seçilen ayarlarla tüm kayıtları ölç")
    ap.add_argument("--ss_alpha", type=float, default=1.5)
    ap.add_argument("--wf_factor", type=float, default=4.0)
    ap.add_argument("--results", default=str(PROJE / "results" / "metrics.csv"),
                    help="noisy ve deepfilternet satırlarının alınacağı mevcut sonuç dosyası")
    ap.add_argument("--out_csv", default=str(PROJE / "results" / "metrics_tuned.csv"))
    args = ap.parse_args()
    if args.final:
        return final(args)

    noisy = sorted(Path(args.noisy_dir).glob("*.wav"))
    noisy = [f for f in noisy if (Path(args.clean_dir) / f.name).exists()]
    if not noisy:
        raise SystemExit("Eşleşen gürültülü/temiz kayıt bulunamadı; klasör yollarını kontrol edin.")
    rng = np.random.default_rng(args.seed)
    if args.n < len(noisy):
        noisy = [noisy[i] for i in sorted(rng.choice(len(noisy), args.n, replace=False))]

    ayarlar = [("noisy", "-", None)]
    ayarlar += [("spectral_subtraction", a, a) for a in SS_ALPHAS]
    ayarlar += [("wiener_filter", k, k) for k in WF_FACTORS]
    print(f"{len(noisy)} kayıt × {len(ayarlar)} ayar = {len(noisy) * len(ayarlar)} ölçüm")

    rows, t0 = [], time.perf_counter()
    for i, f in enumerate(noisy, 1):
        y, sr = load_audio(str(f))
        ref, _ = load_audio(str(Path(args.clean_dir) / f.name))
        for yontem, etiket, deger in ayarlar:
            if yontem == "noisy":
                est = y
            elif yontem == "spectral_subtraction":
                est = spectral_subtraction(y, sr, alpha=deger)
            else:
                est = wiener_filter(y, sr, noise_factor=deger)
            m = compute_metrics(ref, est, sr=sr)
            rows.append({"file": f.stem, "method": yontem, "param": etiket, **m})
        if i % 20 == 0 or i == len(noisy):
            gecen = time.perf_counter() - t0
            print(f"  {i}/{len(noisy)}  ({gecen:.0f} sn, kalan ~{gecen / i * (len(noisy) - i):.0f} sn)")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "param_sweep_raw.csv", index=False)

    ozet = (df.groupby(["method", "param"], sort=False)[METRIKLER].mean().round(3).reset_index())
    ozet.to_csv(out / "param_sweep_summary.csv", index=False)

    md = [f"# Parametre Analizi ({len(noisy)} kayıt)", "",
          "Ortalama değerler; yüksek olan daha iyi. (*) = mevcut varsayılan ayar.", ""]
    for yontem, ad, pad in (("spectral_subtraction", "Spektral çıkarma", "alpha"),
                            ("wiener_filter", "Wiener filtresi", "gürültü çarpanı")):
        t = ozet[ozet["method"] == yontem].drop(columns="method").rename(columns={"param": pad})
        t[pad] = [f"{v}{' (*)' if v == VARSAYILAN[yontem] else ''}" for v in t[pad]]
        md += [f"## {ad}", "", t.to_markdown(index=False), ""]
        en_iyi = ozet[ozet["method"] == yontem].sort_values("pesq", ascending=False).iloc[0]
        md += [f"PESQ'ya göre en iyi {pad}: **{en_iyi['param']}** "
               f"(PESQ {en_iyi['pesq']}, STOI {en_iyi['stoi']}, SI-SDR {en_iyi['si_sdr']})", ""]
    taban = ozet[ozet["method"] == "noisy"].iloc[0]
    md += [f"İşlemsiz kayıt: PESQ {taban['pesq']}, STOI {taban['stoi']}, SI-SDR {taban['si_sdr']}", ""]
    (out / "param_sweep.md").write_text("\n".join(md), encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        renk = {"spectral_subtraction": "#2a78d6", "wiener_filter": "#eb6834"}
        fig, axes = plt.subplots(2, 3, figsize=(12, 6.5))
        for r, (yontem, ad, pad) in enumerate((("spectral_subtraction", "Spektral çıkarma", "alpha"),
                                               ("wiener_filter", "Wiener filtresi", "gürültü çarpanı"))):
            d = ozet[ozet["method"] == yontem]
            x = d["param"].astype(float)
            for c, (m, mad) in enumerate(zip(METRIKLER, ["PESQ", "STOI", "SI-SDR (dB)"])):
                ax = axes[r, c]
                ax.axhline(taban[m], color="#8a8a85", linewidth=1.5, linestyle="--", label="İşlemsiz")
                ax.plot(x, d[m], color=renk[yontem], linewidth=2, marker="o", markersize=7,
                        markeredgecolor="white", label=ad)
                vx = VARSAYILAN[yontem]
                ax.plot([vx], d.loc[x == vx, m], marker="o", markersize=12, markerfacecolor="none",
                        markeredgecolor="#2b2b28", markeredgewidth=1.5, linestyle="none", label="Mevcut ayar")
                ax.set_title(f"{ad} – {mad}", loc="left", fontsize=10)
                ax.set_xlabel(pad, fontsize=9)
                ax.grid(axis="y", color="#e4e3dd")
                for s in ("top", "right"):
                    ax.spines[s].set_visible(False)
                if c == 0:
                    ax.legend(fontsize=8, frameon=False)
        fig.tight_layout()
        fig.savefig(out / "param_sweep.png", dpi=180)
    except Exception as e:  # grafik isteğe bağlı
        print(f"Grafik çizilemedi: {e}")

    print("\n" + "\n".join(md))
    print(f"Çıktılar: {out}")


def final(args):
    noisy = sorted(Path(args.noisy_dir).glob("*.wav"))
    noisy = [f for f in noisy if (Path(args.clean_dir) / f.name).exists()]
    if not noisy:
        raise SystemExit("Eşleşen gürültülü/temiz kayıt bulunamadı; klasör yollarını kontrol edin.")
    eski = pd.read_csv(args.results)
    print(f"{len(noisy)} kayıt: spektral çıkarma alpha={args.ss_alpha}, Wiener gürültü çarpanı={args.wf_factor}")
    rows, t0 = [], time.perf_counter()
    for i, f in enumerate(noisy, 1):
        y, sr = load_audio(str(f))
        ref, _ = load_audio(str(Path(args.clean_dir) / f.name))
        for yontem, est in (("spectral_subtraction", spectral_subtraction(y, sr, alpha=args.ss_alpha)),
                            ("wiener_filter", wiener_filter(y, sr, noise_factor=args.wf_factor))):
            rows.append({"file": f.stem, "method": yontem, **compute_metrics(ref, est, sr=sr)})
        if i % 50 == 0 or i == len(noisy):
            gecen = time.perf_counter() - t0
            print(f"  {i}/{len(noisy)}  ({gecen:.0f} sn, kalan ~{gecen / i * (len(noisy) - i):.0f} sn)")
    yeni = pd.DataFrame(rows)
    korunan = eski[eski["method"].isin(["noisy", "deepfilternet"])]
    birlesik = pd.concat([korunan, yeni], ignore_index=True)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    birlesik.to_csv(args.out_csv, index=False)
    print(birlesik["method"].value_counts().to_string())
    print(f"Kaydedildi: {args.out_csv}")


if __name__ == "__main__":
    main()
