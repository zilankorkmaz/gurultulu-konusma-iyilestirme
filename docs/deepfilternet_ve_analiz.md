# DeepFilterNet Entegrasyonu ve Karşılaştırmalı Analiz

Sorumlu: Zilan KORKMAZ (İP 4 ve İP 6)

## Kurulum

```bash
python -m venv .venv            # Python 3.10 veya 3.11
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Model (DeepFilterNet3) ilk çalıştırmada otomatik indirilir. İnternet sorunu olursa
https://github.com/Rikorose/DeepFilterNet/tree/main/models adresinden `DeepFilterNet3.zip`
indirilip açılır ve `--model_dir` ile gösterilir.

## 1. DeepFilterNet ile iyileştirme

```bash
python src/enhance_deepfilternet.py          # data/noisy -> outputs/deepfilternet (run_all.py ile aynı düzen)
```

- DeepFilterNet **48 kHz** ile çalışır. Girdi 48 kHz'e çevrilip modele verilir,
  çıktı 16 kHz olarak kaydedilir (PESQ geniş bant 16 kHz istediği için).
- Her dosyanın işlem süresi `outputs/deepfilternet/_timing.csv` dosyasına yazılır.
- Girdi olarak .wav, .mp3, .flac vb. kabul eder; alt klasörler de taranır.
- Deneme için `--limit 10` ile ilk 10 dosya işlenebilir.

## 2. Ortak sonuç tablosu (ekip için sözleşme)

Analiz betiği tek bir CSV okur. Her yöntemin ölçüt sonuçları bu biçimde olmalı:

| sütun   | açıklama |
|---------|----------|
| file    | dosya adı, uzantısız (`p232_001`) |
| method  | `noisy`, `spectral_subtraction`, `wiener_filter`, `deepfilternet` (outputs/ klasör adları) |
| pesq    | geniş bant PESQ |
| stoi    | STOI (0–1) |
| si_sdr  | SI-SDR (dB) |

`noisy` satırları, işlem uygulanmamış gürültülü kaydın temiz kayda göre ölçütleridir
(karşılaştırmanın başlangıç noktası). Gürültü türü ve SNR sütunlarını eklemeye gerek yok;
analiz betiği bunları VoiceBank-DEMAND `log_testset.txt` dosyasından ekler.

## 3. Karşılaştırmalı analiz

```bash
python src/analysis.py --results results/metrics.csv --testset_log data/log_testset.txt --out_dir results/analysis
```

Üretilenler: yöntem başına ortalama ± std, işlemsiz kayda göre iyileşme, DeepFilterNet ile
diğer yöntemler arasında eşleştirilmiş Wilcoxon testi, gürültü türü ve SNR kırılımları,
iki grafik (`metrics_vs_snr.png`, `metrics_by_noise.png`) ve rapora yapıştırılabilir `summary.md`.

## 4. Uçtan uca deneme

Gerçek veri gelmeden boru hattını denemek için:

```bash
python scripts/smoke_test.py --clean temiz.wav --noise gurultu1.wav --noise gurultu2.wav
```

Temiz bir kayda iki gürültüyü 2,5 / 7,5 / 12,5 / 17,5 dB SNR'de ekler, DeepFilterNet'i çalıştırır,
ölçütleri hesaplar ve analizi üretir. Bu betikteki ölçüt hesaplama geçicidir; ekibin
değerlendirme modülü hazır olunca onunla değiştirilecek.
