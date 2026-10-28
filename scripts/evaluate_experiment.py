"""Ek Gürültü Deneyinin Ölçülmesi ve Karşılaştırmalı Analizi (scripts/evaluate_experiment.py).

Betül'ün oluşturduğu VoiceBank test kümesindeki tüm çıktıları (noisy,
spectral_subtraction, wiener_filter, deepfilternet) src/metrics.py modülüyle
değerlendirir, results/metrics.csv dosyasını üretir ve src/analysis.py
aracılığıyla results/analysis/ klasöründeki tablo ve grafikleri oluşturur.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from metrics import evaluate_directory
import analysis

def main():
    clean_dir = ROOT_DIR / "data" / "voicebank" / "clean"
    vb_noisy_dir = ROOT_DIR / "data" / "voicebank" / "noisy"
    outputs_dir = ROOT_DIR / "outputs" / "voicebank"
    results_csv = ROOT_DIR / "results" / "metrics.csv"
    analysis_dir = ROOT_DIR / "results" / "analysis"
    testset_log = ROOT_DIR / "data" / "voicebank" / "log_testset.txt"

    # Eski metrics.csv dosyasını temizle
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    if results_csv.exists():
        results_csv.unlink()

    print("=" * 60)
    print("1. EK GÜRÜLTÜ DENEYİ METRİK ÖLÇÜMLERİ BAŞLATILIYOR (metrics.py)")
    print("=" * 60)

    # 1. İşlemsiz (noisy) temel ölçüm
    print("\n--> [noisy] Ham Gürültülü Kayıtlar Ölçülüyor...")
    evaluate_directory(
        clean_dir=clean_dir,
        enhanced_dir=vb_noisy_dir,
        method_name="noisy",
        output_csv=results_csv
    )

    # 2. Spektral Çıkarma
    print("\n--> [spectral_subtraction] Spektral Çıkarma Çıktıları Ölçülüyor...")
    evaluate_directory(
        clean_dir=clean_dir,
        enhanced_dir=outputs_dir / "spectral_subtraction",
        method_name="spectral_subtraction",
        output_csv=results_csv
    )

    # 3. Wiener Filtresi
    print("\n--> [wiener_filter] Wiener Filtresi Çıktıları Ölçülüyor...")
    evaluate_directory(
        clean_dir=clean_dir,
        enhanced_dir=outputs_dir / "wiener_filter",
        method_name="wiener_filter",
        output_csv=results_csv
    )

    # 4. DeepFilterNet
    print("\n--> [deepfilternet] DeepFilterNet Çıktıları Ölçülüyor...")
    evaluate_directory(
        clean_dir=clean_dir,
        enhanced_dir=outputs_dir / "deepfilternet",
        method_name="deepfilternet",
        output_csv=results_csv
    )

    print("\n" + "=" * 60)
    print(f"2. ÖLÇÜMLER TAMAMLANDI: {results_csv}")
    print("=" * 60)

    # 3. Karşılaştırmalı Analiz Üretimi (src/analysis.py)
    print("\n--> [analysis.py] Karşılaştırmalı Analiz ve Grafikler Üretiliyor...")
    analysis_dir.mkdir(parents=True, exist_ok=True)

    sys.argv = [
        "analysis.py",
        "--results", str(results_csv),
        "--testset_log", str(testset_log),
        "--out_dir", str(analysis_dir)
    ]
    analysis.main()

    print("\n" + "=" * 60)
    print(f"TÜM ANALİZ ÇIKTILARI BAŞARIYLA ÜRETİLDİ: {analysis_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
