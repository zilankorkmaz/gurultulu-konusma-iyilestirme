"""Yöntemlerin karşılaştırmalı analizi.

Girdi: ortak sonuç tablosu (CSV). Her satır bir kayıt-yöntem çiftidir:

    file,method,pesq,stoi,si_sdr[,noise_type,snr]

- method: "noisy" (işlem uygulanmamış), "spectral_subtraction", "wiener_filter", "deepfilternet"
- noise_type ve snr yoksa --testset_log ile VoiceBank-DEMAND log_testset.txt
  dosyasından eklenir (satır biçimi: "<dosya> <gürültü_türü> <snr>").

Çıktılar (--out_dir):
    summary_by_method.csv      yöntem başına ortalama ± std
    summary_by_noise.csv       yöntem x gürültü türü ortalamaları
    summary_by_snr.csv         yöntem x SNR ortalamaları
    improvement_vs_noisy.csv   işlemsiz kayda göre ortalama iyileşme
    wilcoxon_vs_deepfilternet.csv  eşleştirilmiş Wilcoxon testi (DeepFilterNet vs diğerleri)
    metrics_vs_snr.png, metrics_by_noise.png
    summary.md                 rapora yapıştırılabilir özet

Kullanım:
    python src/analysis.py --results results/metrics.csv \
        --testset_log data/log_testset.txt --out_dir results/analysis
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import wilcoxon

METRICS = {"pesq": "PESQ", "stoi": "STOI", "si_sdr": "SI-SDR (dB)"}
# Sabit sıra ve sabit renk: renk yönteme bağlıdır, sıralamaya değil.
METHOD_ORDER = ["noisy", "spectral_subtraction", "wiener_filter", "deepfilternet"]
METHOD_LABEL = {"noisy": "İşlemsiz", "spectral_subtraction": "Spektral çıkarma",
                "wiener_filter": "Wiener", "deepfilternet": "DeepFilterNet"}
METHOD_COLOR = {"noisy": "#8a8a85", "spectral_subtraction": "#2a78d6",
                "wiener_filter": "#eb6834", "deepfilternet": "#1baf7a"}
METHOD_MARKER = {"noisy": "o", "spectral_subtraction": "s", "wiener_filter": "^", "deepfilternet": "D"}


def load(results, testset_log):
    df = pd.read_csv(results)
    df["method"] = df["method"].replace({"wiener": "wiener_filter"})
    df["file"] = df["file"].astype(str).str.replace(r"\.wav$", "", regex=True)
    if testset_log and not {"noise_type", "snr"} <= set(df.columns):
        rows = []
        for line in Path(testset_log).read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                snr = float(parts[-1])
            except ValueError:
                continue  # başlık vb. satırları atla
            rows.append((parts[0].replace(".wav", ""), " ".join(parts[1:-1]), snr))
        meta = pd.DataFrame(rows, columns=["file", "noise_type", "snr"])
        df = df.merge(meta, on="file", how="left")
    missing = [m for m in METRICS if m not in df.columns]
    if missing:
        raise SystemExit(f"Sonuç dosyasında eksik sütun: {missing}")
    methods = [m for m in METHOD_ORDER if m in df["method"].unique()]
    methods += sorted(set(df["method"]) - set(methods))
    return df, methods


def fmt_mean_std(g):
    out = pd.DataFrame(index=g.mean().index)
    for m, name in METRICS.items():
        out[name] = [f"{a:.3f} ± {s:.3f}" for a, s in zip(g.mean()[m], g.std()[m].fillna(0))]
    return out


def style_axes(ax):
    ax.grid(axis="y", color="#e4e3dd", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#b8b7ae")
    ax.tick_params(colors="#55554f", labelsize=9)


def plot_vs_snr(df, methods, path):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, (m, name) in zip(axes, METRICS.items()):
        g = df.groupby(["method", "snr"])[m].mean().reset_index()
        for meth in methods:
            d = g[g["method"] == meth].sort_values("snr")
            ax.plot(d["snr"], d[m], color=METHOD_COLOR.get(meth, "#55554f"), linewidth=2,
                    marker=METHOD_MARKER.get(meth, "o"), markersize=7,
                    markeredgecolor="white", markeredgewidth=1.2, label=METHOD_LABEL.get(meth, meth))
        ax.set_title(name, fontsize=11, color="#2b2b28", loc="left")
        ax.set_xlabel("Giriş SNR (dB)", fontsize=9, color="#55554f")
        ax.set_xticks(sorted(df["snr"].dropna().unique()))
        style_axes(ax)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=len(methods), frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_by_noise(df, methods, path):
    noises = sorted(df["noise_type"].dropna().unique())
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    width = 0.8 / len(methods)
    for ax, (m, name) in zip(axes, METRICS.items()):
        g = df.groupby(["noise_type", "method"])[m].mean()
        for k, meth in enumerate(methods):
            vals = [g.get((n, meth), float("nan")) for n in noises]
            xs = [i + (k - (len(methods) - 1) / 2) * width for i in range(len(noises))]
            ax.bar(xs, vals, width=width * 0.9, color=METHOD_COLOR.get(meth, "#55554f"),
                   label=METHOD_LABEL.get(meth, meth))
        ax.set_xticks(range(len(noises)))
        ax.set_xticklabels(noises, fontsize=9)
        ax.set_title(name, fontsize=11, color="#2b2b28", loc="left")
        if m != "si_sdr":
            ax.set_ylim(bottom=0)
        style_axes(ax)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=len(methods), frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Yöntemlerin PESQ/STOI/SI-SDR karşılaştırması")
    ap.add_argument("--results", required=True)
    ap.add_argument("--testset_log", default=None)
    ap.add_argument("--out_dir", default="results/analysis")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df, methods = load(args.results, args.testset_log)
    label = lambda s: s.map(lambda x: METHOD_LABEL.get(x, x))

    by_method = fmt_mean_std(df.groupby("method")[list(METRICS)]).reindex(methods)
    by_method.index = label(by_method.index.to_series())
    by_method.to_csv(out / "summary_by_method.csv", encoding="utf-8")

    md = ["# Karşılaştırmalı Analiz Özeti", "", f"Kayıt sayısı: {df['file'].nunique()}, yöntemler: "
          + ", ".join(METHOD_LABEL.get(m, m) for m in methods), "", "## Yöntem başına ortalama ± std", "",
          by_method.to_markdown(), ""]

    if "noisy" in methods:
        base = df[df["method"] == "noisy"].set_index("file")[list(METRICS)]
        rows = []
        for meth in methods:
            if meth == "noisy":
                continue
            d = df[df["method"] == meth].set_index("file")[list(METRICS)]
            diff = (d - base.reindex(d.index)).mean()
            rows.append({"Yöntem": METHOD_LABEL.get(meth, meth),
                         **{f"Δ {n}": round(diff[m], 3) for m, n in METRICS.items()}})
        imp = pd.DataFrame(rows)
        imp.to_csv(out / "improvement_vs_noisy.csv", index=False, encoding="utf-8")
        md += ["## İşlemsiz kayda göre ortalama iyileşme", "", imp.to_markdown(index=False), ""]

    if "deepfilternet" in methods and len(methods) > 1:
        ref = df[df["method"] == "deepfilternet"].set_index("file")
        rows = []
        for meth in methods:
            if meth == "deepfilternet":
                continue
            other = df[df["method"] == meth].set_index("file")
            common = ref.index.intersection(other.index)
            for m, n in METRICS.items():
                a, b = ref.loc[common, m], other.loc[common, m]
                p = wilcoxon(a, b).pvalue if len(common) >= 6 and (a != b).any() else float("nan")
                rows.append({"Karşılaştırma": f"DeepFilterNet vs {METHOD_LABEL.get(meth, meth)}", "Ölçüt": n,
                             "Ortalama fark": round((a - b).mean(), 3), "n": len(common), "p (Wilcoxon)": p})
        wt = pd.DataFrame(rows)
        wt.to_csv(out / "wilcoxon_vs_deepfilternet.csv", index=False, encoding="utf-8")
        md += ["## Eşleştirilmiş Wilcoxon testi", "", wt.to_markdown(index=False, floatfmt=".4g"), ""]

    if {"noise_type", "snr"} <= set(df.columns) and df["snr"].notna().any():
        for col, fname in (("noise_type", "summary_by_noise.csv"), ("snr", "summary_by_snr.csv")):
            t = df.groupby([col, "method"])[list(METRICS)].mean().round(3).unstack("method")
            t.to_csv(out / fname, encoding="utf-8")
        plot_vs_snr(df, methods, out / "metrics_vs_snr.png")
        plot_by_noise(df, methods, out / "metrics_by_noise.png")
        snr_t = df.groupby(["snr", "method"])["pesq"].mean().round(3).unstack("method")[methods]
        snr_t.columns = [METHOD_LABEL.get(c, c) for c in snr_t.columns]
        md += ["## SNR seviyesine göre ortalama PESQ", "", snr_t.to_markdown(), "",
               "![SNR'ye göre ölçütler](metrics_vs_snr.png)", "", "![Gürültü türüne göre ölçütler](metrics_by_noise.png)", ""]
    else:
        md += ["(noise_type/snr bilgisi yok; gürültü türü ve SNR kırılımı atlandı.)", ""]

    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nÇıktılar: {out.resolve()}")


if __name__ == "__main__":
    main()
