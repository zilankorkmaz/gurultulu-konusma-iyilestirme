"""Ek gürültü test setinin metrik analizi.

data/extra_noise_set/dosya_listesi.csv (id, dosya, temiz, gurultu, snr_db) kullanılarak her
çıktı, `temiz` sütunundaki VoiceBank temiz kaydıyla eşleştirilir ve PESQ, STOI, SI-SDR
hesaplanır. Ardından yöntem, gürültü türü ve SNR kırılımlarında özet tablolar ve grafikler
üretilir.

Değerlendirilen yöntemler:
    outputs/extra_noise/spectral_subtraction
    outputs/extra_noise/wiener_filter
    outputs/extra_noise/deepfilternet
    (+ data/extra_noise_set/noisy varsa "noisy": işlem uygulanmamış kayıt, başlangıç noktası)

Kullanım (proje kökünden):
    python scripts/evaluate_extra_noise.py
    python scripts/evaluate_extra_noise.py --limit 20      # hızlı deneme
    python scripts/evaluate_extra_noise.py --from_csv      # ölçmeden, CSV'den tablo ve grafikleri yenile

Çıktılar:
    results/extra_noise_metrics.csv                 kayıt başına ölçümler
    results/extra_noise_analysis/summary.md         tüm özet tablolar
    results/extra_noise_analysis/*.csv              yöntem / gürültü / SNR / gürültü×SNR özetleri
    results/extra_noise_analysis/*.png              grafikler ve rapor için tablo görüntüleri (tablo1..4)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE / "src"))

from metrics import compute_metrics_from_files  # noqa: E402
import analysis  # noqa: E402  (renkler, etiketler ve SNR / gürültü grafikleri)

YONTEMLER = ["spectral_subtraction", "wiener_filter", "deepfilternet"]
METRIKLER = {"pesq": "PESQ", "stoi": "STOI", "si_sdr": "SI-SDR (dB)"}
GURULTU_SIRASI = ["classroom", "crowd", "people", "group_talking"]


def lfs_isaretci_mi(yol: Path) -> bool:
    """Git LFS ile indirilmemiş dosyalar 130 baytlık metin işaretçisi olarak kalır."""
    try:
        if yol.stat().st_size > 1024:
            return False
        return yol.read_bytes()[:40].startswith(b"version https://git-lfs")
    except OSError:
        return False


def ortalama_std(df, grup):
    g = df.groupby(grup)[list(METRIKLER)]
    ort, std = g.mean(), g.std().fillna(0)
    out = pd.DataFrame(index=ort.index)
    for m, ad in METRIKLER.items():
        out[ad] = [f"{a:.3f} ± {s:.3f}" for a, s in zip(ort[m], std[m])]
    return out


def olc(args):
    """Her kayıt ve yöntem için ölçütleri hesaplar, CSV'ye yazar ve DataFrame döndürür."""
    liste = pd.read_csv(args.list)
    eksik_sutun = {"id", "dosya", "temiz", "gurultu", "snr_db"} - set(liste.columns)
    if eksik_sutun:
        raise SystemExit(f"dosya_listesi.csv içinde eksik sütun: {sorted(eksik_sutun)}")
    if args.limit:
        liste = liste.head(args.limit)

    clean_dir, out_root, noisy_root = Path(args.clean_dir), Path(args.outputs_dir), Path(args.noisy_root)

    # Girdi kontrolleri: temiz referanslar ve LFS işaretçileri
    eksik_temiz = sorted({t for t in liste["temiz"] if not (clean_dir / t).exists()})
    if eksik_temiz:
        raise SystemExit(f"{len(eksik_temiz)} temiz referans bulunamadı ({clean_dir}), ör. {eksik_temiz[:3]}")

    def cikti_yolu(yontem, dosya):
        goreli = Path(dosya)
        if goreli.parts and goreli.parts[0] == "noisy":
            goreli = Path(*goreli.parts[1:])
        return out_root / yontem / goreli

    ornek = cikti_yolu(YONTEMLER[0], liste["dosya"].iloc[0])
    if lfs_isaretci_mi(ornek):
        raise SystemExit("Çıktı dosyaları Git LFS işaretçisi olarak duruyor (ses indirilmemiş).\n"
                         'Önce şunu çalıştırın: git lfs pull --include "outputs/extra_noise/**"')

    yontemler = list(YONTEMLER)
    noisy_var = (noisy_root / liste["dosya"].iloc[0]).exists()
    if noisy_var:
        yontemler = ["noisy"] + yontemler
    else:
        print("Not: data/extra_noise_set/noisy bulunamadı; işlemsiz (noisy) ölçüm atlanıyor.")

    toplam = len(liste) * len(yontemler)
    print(f"{len(liste)} kayıt × {len(yontemler)} yöntem = {toplam} ölçüm")
    rows, eksikler, t0 = [], [], time.perf_counter()
    for i, r in enumerate(liste.itertuples(index=False), 1):
        ref = clean_dir / r.temiz
        for y in yontemler:
            est = noisy_root / r.dosya if y == "noisy" else cikti_yolu(y, r.dosya)
            if not est.exists() or lfs_isaretci_mi(est):
                eksikler.append(f"{y}: {est}")
                continue
            m = compute_metrics_from_files(ref, est)
            rows.append({"id": r.id, "file": r.id, "method": y, "noise_type": r.gurultu,
                         "snr": float(r.snr_db), "temiz": r.temiz, **m})
        if i % 50 == 0 or i == len(liste):
            gecen = time.perf_counter() - t0
            print(f"  {i}/{len(liste)}  ({gecen:.0f} sn, kalan ~{gecen / i * (len(liste) - i):.0f} sn)")

    if eksikler:
        print(f"\nUYARI: {len(eksikler)} çıktı bulunamadı ya da indirilmemiş, ör.:")
        for e in eksikler[:5]:
            print("   ", e)

    df = pd.DataFrame(rows)
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"\nÖlçümler: {out_csv}  ({len(df)} satır)")
    return df


def main():
    ap = argparse.ArgumentParser(description="Ek gürültü test setinin metrik analizi")
    ap.add_argument("--list", default=str(PROJE / "data" / "extra_noise_set" / "dosya_listesi.csv"))
    ap.add_argument("--clean_dir", default=str(PROJE / "data" / "voicebank" / "clean_testset_wav"))
    ap.add_argument("--outputs_dir", default=str(PROJE / "outputs" / "extra_noise"))
    ap.add_argument("--noisy_root", default=str(PROJE / "data" / "extra_noise_set"),
                    help="dosya sütunundaki 'noisy/...' yollarının kökü (yoksa işlemsiz ölçüm atlanır)")
    ap.add_argument("--out_csv", default=str(PROJE / "results" / "extra_noise_metrics.csv"))
    ap.add_argument("--out_dir", default=str(PROJE / "results" / "extra_noise_analysis"))
    ap.add_argument("--limit", type=int, default=None, help="Sadece ilk N kaydı değerlendir (deneme için)")
    ap.add_argument("--from_csv", action="store_true",
                    help="Ölçümü atla; var olan --out_csv dosyasından tablo ve grafikleri yeniden üret")
    args = ap.parse_args()

    if args.from_csv:
        df = pd.read_csv(args.out_csv)
        print(f"Ölçümler {args.out_csv} dosyasından okundu ({len(df)} satır)")
    else:
        df = olc(args)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sira = [m for m in analysis.METHOD_ORDER if m in df["method"].unique()]
    etiket = lambda m: analysis.METHOD_LABEL.get(m, m)
    gurultuler = [g for g in GURULTU_SIRASI if g in df["noise_type"].unique()]
    gurultuler += sorted(set(df["noise_type"]) - set(gurultuler))

    # 1) Yöntem bazında
    t_yontem = ortalama_std(df, "method").reindex(sira)
    t_yontem.index = [etiket(m) for m in t_yontem.index]
    t_yontem.to_csv(out / "summary_by_method.csv", encoding="utf-8")

    # 2) Gürültü türü ve 3) SNR bazında (her ölçüt için yöntem sütunları)
    def kirilim(col, sira_idx):
        parcalar = []
        for m, ad in METRIKLER.items():
            t = df.pivot_table(index=col, columns="method", values=m, aggfunc="mean")[sira].reindex(sira_idx)
            t.columns = [f"{ad} | {etiket(c)}" for c in t.columns]
            parcalar.append(t.round(3))
        return pd.concat(parcalar, axis=1)

    t_gurultu = kirilim("noise_type", gurultuler)
    t_gurultu.to_csv(out / "summary_by_noise.csv", encoding="utf-8")
    t_snr = kirilim("snr", sorted(df["snr"].unique()))
    t_snr.to_csv(out / "summary_by_snr.csv", encoding="utf-8")

    # 4) Gürültü × SNR: her hücrede en iyi yöntem (PESQ)
    pv = df[df["method"] != "noisy"].pivot_table(index=["noise_type", "snr"], columns="method",
                                                 values="pesq", aggfunc="mean")
    en_iyi = pv.idxmax(axis=1).map(etiket).unstack("snr").reindex(gurultuler)
    en_iyi.to_csv(out / "best_method_by_noise_snr.csv", encoding="utf-8")
    pv_dfn = pv.copy()
    klasik_max = pv_dfn[[c for c in pv_dfn.columns if c != "deepfilternet"]].max(axis=1)
    fark = (pv_dfn["deepfilternet"] - klasik_max).round(3).unstack("snr").reindex(gurultuler) \
        if "deepfilternet" in pv_dfn else None
    if fark is not None:
        fark.to_csv(out / "dfn_minus_best_classical_pesq.csv", encoding="utf-8")

    # 5) Eşleştirilmiş Wilcoxon: DeepFilterNet vs diğerleri
    from scipy.stats import wilcoxon
    wt = []
    if "deepfilternet" in sira:
        ref_df = df[df["method"] == "deepfilternet"].set_index("id")
        for y in sira:
            if y == "deepfilternet":
                continue
            o = df[df["method"] == y].set_index("id")
            ortak = ref_df.index.intersection(o.index)
            for m, ad in METRIKLER.items():
                a, b = ref_df.loc[ortak, m], o.loc[ortak, m]
                p = wilcoxon(a, b).pvalue if len(ortak) >= 6 and (a != b).any() else float("nan")
                wt.append({"Karşılaştırma": f"DeepFilterNet vs {etiket(y)}", "Ölçüt": ad,
                           "Ortalama fark": round((a - b).mean(), 3), "n": len(ortak), "p (Wilcoxon)": p})
    t_wil = pd.DataFrame(wt)
    t_wil.to_csv(out / "wilcoxon_vs_deepfilternet.csv", index=False, encoding="utf-8")

    # Grafikler
    grafik_yontem(df, sira, out / "method_means.png")
    tablo_gorselleri(df, sira, gurultuler, out)
    analysis.plot_vs_snr(df, sira, out / "metrics_vs_snr.png")
    df_g = df.copy()
    df_g["noise_type"] = pd.Categorical(df_g["noise_type"], categories=gurultuler, ordered=True)
    analysis.plot_by_noise(df_g, sira, out / "metrics_by_noise.png")

    def md_kirilim(baslik, col, sira_idx):
        satirlar = [f"## {baslik} (ortalama)", ""]
        for m, ad in METRIKLER.items():
            t = df.pivot_table(index=col, columns="method", values=m, aggfunc="mean")[sira].reindex(sira_idx)
            t.columns = [etiket(c) for c in t.columns]
            t.index.name = "Gürültü" if col == "noise_type" else "SNR (dB)"
            satirlar += [f"**{ad}**", "", t.round(3).to_markdown(), ""]
        return satirlar

    md = [f"# Ek Gürültü Deneyi – Metrik Analizi", "",
          f"{df['id'].nunique()} kayıt · gürültüler: {', '.join(gurultuler)} · "
          f"SNR: {', '.join(f'{s:g}' for s in sorted(df['snr'].unique()))} dB · "
          f"yöntemler: {', '.join(etiket(m) for m in sira)}", "",
          "## Yöntem bazında (ortalama ± std)", "", t_yontem.to_markdown(), "",
          *md_kirilim("Gürültü türü bazında", "noise_type", gurultuler),
          *md_kirilim("SNR bazında", "snr", sorted(df["snr"].unique())),
          "## Her gürültü × SNR hücresinde PESQ'ya göre en iyi yöntem", "", en_iyi.to_markdown(), ""]
    if fark is not None:
        md += ["## DeepFilterNet – en iyi klasik yöntem (PESQ farkı)", "", fark.to_markdown(), ""]
    if len(t_wil):
        md += ["## Eşleştirilmiş Wilcoxon testi", "", t_wil.to_markdown(index=False, floatfmt=".4g"), ""]
    md += ["## Tablo görüntüleri", "", "![Tablo 1](tablo1_yontem.png)", "", "![Tablo 2](tablo2_gurultu.png)", "",
           "![Tablo 3](tablo3_snr.png)", "", "![Tablo 4](tablo4_dfn_fark.png)", "",
           "## Grafikler", "", "![Yöntem ortalamaları](method_means.png)", "", "![SNR'ye göre](metrics_vs_snr.png)", "",
           "![Gürültü türüne göre](metrics_by_noise.png)", ""]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(md))
    print(f"\nÇıktılar: {out}")


def grafik_yontem(df, sira, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, (m, ad) in zip(axes, METRIKLER.items()):
        g = df.groupby("method")[m]
        ort, std = g.mean().reindex(sira), g.std().reindex(sira)
        xs = range(len(sira))
        ax.bar(xs, ort, width=0.6, yerr=std, capsize=3, error_kw={"elinewidth": 1, "ecolor": "#55554f"},
               color=[analysis.METHOD_COLOR.get(s, "#55554f") for s in sira])
        for x, v in zip(xs, ort):
            ax.text(x, v * 0.04, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color="white",
                    fontweight="bold")
        ax.set_xticks(list(xs))
        ax.set_xticklabels([analysis.METHOD_LABEL.get(s, s) for s in sira], fontsize=8)
        ax.set_title(ad, loc="left", fontsize=11, color="#2b2b28")
        if m != "si_sdr":
            ax.set_ylim(bottom=0)
        analysis.style_axes(ax)
    fig.suptitle("Ek gürültü seti – yöntem ortalamaları (hata çubuğu: std)", fontsize=10, color="#55554f", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=200)
    plt.close(fig)

# ---------------------------------------------------------------------------
# Rapor için tablo görüntüleri (ondalık virgüllü, her satırda/ölçütte en iyi değer vurgulu)
KISA = {"noisy": "İşlemsiz", "spectral_subtraction": "Spektral", "wiener_filter": "Wiener", "deepfilternet": "DFN"}
BASAMAK = {"pesq": 2, "stoi": 3, "si_sdr": 2}
T_INK, T_MUTED, T_RULE, T_HEAD, T_BEST = "#2b2b28", "#6b6b66", "#d9d9d4", "#f3f3f0", "#e3f4ec"


def _tr(v, d):
    return f"{v:.{d}f}".replace(".", ",")


def _tablo_ciz(baslik, ust, alt, satirlar, kalin, path, ilk_gen, hucre_gen, alt_not=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ncol = len(alt)
    gen = [ilk_gen] + [hucre_gen] * (ncol - 1)
    W, rh, nh = sum(gen), 0.42, (2 if ust else 1)
    H = rh * (nh + len(satirlar)) + 0.75 + (0.35 if alt_not else 0)
    fig = plt.figure(figsize=(W + 0.3, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(-0.15, W + 0.15)
    ax.set_ylim(H, 0)
    ax.text(0, 0.38, baslik, fontsize=12, fontweight="bold", color=T_INK, va="center")
    y, xs = 0.7, [sum(gen[:j]) for j in range(ncol + 1)]
    xm = lambda j: xs[j] + 0.1 if j == 0 else (xs[j] + xs[j + 1]) / 2
    ha = lambda j: "left" if j == 0 else "center"
    ax.add_patch(plt.Rectangle((0, y), W, rh * nh, color=T_HEAD, lw=0))
    if ust:
        j = 1
        for metin, n in ust:
            ax.text((xs[j] + xs[j + n]) / 2, y + rh / 2, metin, ha="center", va="center",
                    fontsize=10, fontweight="bold", color=T_INK)
            ax.plot([xs[j] + 0.08, xs[j + n] - 0.08], [y + rh - 0.04] * 2, color=T_RULE, lw=1)
            j += n
        y += rh
    for j, a in enumerate(alt):
        ax.text(xm(j), y + rh / 2, a, ha=ha(j), va="center", fontsize=9, fontweight="bold",
                color=T_MUTED if ust and j else T_INK)
    y += rh
    ax.plot([0, W], [y, y], color=T_INK, lw=1.2)
    for i, r in enumerate(satirlar):
        for j, v in enumerate(r):
            if (i, j) in kalin:
                ax.add_patch(plt.Rectangle((xs[j] + 0.04, y + 0.05), gen[j] - 0.08, rh - 0.1, color=T_BEST, lw=0))
            ax.text(xm(j), y + rh / 2, v, ha=ha(j), va="center", fontsize=9.5, color=T_INK,
                    fontweight="bold" if (i, j) in kalin else "normal")
        y += rh
        son = i == len(satirlar) - 1
        ax.plot([0, W], [y, y], color=T_INK if son else T_RULE, lw=1.2 if son else 0.8)
    if alt_not:
        ax.text(0, y + 0.25, alt_not, fontsize=8.5, color=T_MUTED, va="center")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def tablo_gorselleri(df, sira, gurultuler, out):
    etiket = lambda m: analysis.METHOD_LABEL.get(m, m)
    n_kayit = df["id"].nunique()

    # Tablo 1: yöntem bazında ortalama ± std
    g = df.groupby("method")
    satirlar = [[etiket(m)] + [f"{_tr(g[c].mean()[m], BASAMAK[c])} ± {_tr(g[c].std()[m], BASAMAK[c])}"
                               for c in METRIKLER] for m in sira]
    kalin = {(sira.index(g[c].mean().reindex(sira).idxmax()), j) for j, c in enumerate(METRIKLER, 1)}
    _tablo_ciz("Tablo 1. Yöntem bazında ortalama başarım (ortalama ± std)", None,
               ["Yöntem"] + list(METRIKLER.values()), satirlar, kalin, out / "tablo1_yontem.png", 2.0, 1.75,
               f"Yeşil ve kalın: her ölçütte en iyi yöntem. {n_kayit} kayıt, VoiceBank temiz referanslarıyla.")

    # Tablo 2 ve 3: gürültü türü ve SNR bazında
    def kirilim(col, degerler, ad, ilk, baslik, path):
        satirlar, kalin = [], set()
        for i, k in enumerate(degerler):
            s = df[df[col] == k].groupby("method")
            r = [ad(k)]
            for b, c in enumerate(METRIKLER):
                ort = s[c].mean().reindex(sira)
                r += [_tr(v, BASAMAK[c]) for v in ort]
                kalin.add((i, 1 + len(sira) * b + list(ort.index).index(ort.idxmax())))
            satirlar.append(r)
        _tablo_ciz(baslik, [(a, len(sira)) for a in METRIKLER.values()], [ilk] + [KISA.get(m, m) for m in sira] * 3,
                   satirlar, kalin, path, 1.55, 0.88,
                   "DFN: DeepFilterNet, Spektral: spektral çıkarma. Yeşil ve kalın: o satırda ilgili ölçütteki en iyi yöntem.")

    kirilim("noise_type", gurultuler, str, "Gürültü", "Tablo 2. Gürültü türü bazında ortalama başarım",
            out / "tablo2_gurultu.png")
    kirilim("snr", sorted(df["snr"].unique()), lambda v: _tr(v, 1) + " dB", "SNR",
            "Tablo 3. SNR seviyesi bazında ortalama başarım", out / "tablo3_snr.png")

    # Tablo 4: DeepFilterNet'in en iyi klasik yönteme göre PESQ farkı
    klasik = [m for m in ("spectral_subtraction", "wiener_filter") if m in sira]
    if "deepfilternet" in sira and klasik:
        pv = df.pivot_table(index=["noise_type", "snr"], columns="method", values="pesq", aggfunc="mean")
        fark = (pv["deepfilternet"] - pv[klasik].max(axis=1)).unstack("snr").reindex(gurultuler)
        satirlar = [[k] + [("+" if v >= 0 else "−") + _tr(abs(v), 2) for v in fark.loc[k]] for k in gurultuler]
        hepsi = (fark > 0).all().all()
        _tablo_ciz("Tablo 4. DeepFilterNet'in en iyi klasik yönteme göre PESQ farkı", None,
                   ["Gürültü"] + [_tr(v, 1) + " dB" for v in fark.columns], satirlar, set(),
                   out / "tablo4_dfn_fark.png", 1.8, 1.1,
                   f"{fark.size} durumun tamamında DeepFilterNet PESQ'da en iyi yöntemdir." if hepsi else
                   "Pozitif değer: DeepFilterNet daha iyi.")


if __name__ == "__main__":
    main()
