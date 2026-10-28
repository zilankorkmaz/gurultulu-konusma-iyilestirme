# Gürültülü Konuşma Kayıtlarının İyileştirilmesi

Fırat Üniversitesi **Bilgisayar Mühendisliği Tasarımı** dersi projesi.

Tek kanallı gürültülü konuşma kayıtlarını iki klasik sinyal işleme yöntemi (**spektral çıkarma**, **Wiener filtresi**) ve önceden eğitilmiş bir derin öğrenme modeli (**DeepFilterNet3**) ile iyileştirip, yöntemleri **VoiceBank-DEMAND** test kümesinde **PESQ**, **STOI** ve **SI-SDR** ölçütleriyle karşılaştırıyoruz. Sonuçları dinlemek ve görselleştirmek için bir Gradio arayüzü de içerir.

**Ekip:** Zilan Korkmaz · Betül Kemaneci · Leyla Erdoğan

---

## 📊 Sonuçlar (VoiceBank-DEMAND test kümesi, 824 kayıt)

| Yöntem | PESQ | STOI | SI-SDR (dB) |
|---|---|---|---|
| İşlemsiz (gürültülü kayıt) | 1,97 | 0,921 | 8,45 |
| Spektral çıkarma (α = 1,0) | 2,33 | 0,920 | 13,09 |
| Wiener filtresi (gürültü çarpanı = 16) | 2,31 | 0,913 | 14,34 |
| **DeepFilterNet3** | **3,16** | **0,945** | **18,92** |

- DeepFilterNet tüm ölçütlerde ve tüm SNR seviyelerinde en iyi yöntem; farklar istatistiksel olarak anlamlı (eşleştirilmiş Wilcoxon testi, p < 0,001).
- Klasik yöntemler kaliteyi (PESQ, SI-SDR) artırıyor ancak anlaşılırlığı (STOI) artıramıyor.
- Klasik yöntemlerin ayarları parametre taramasıyla seçildi; en iyi ayarlar bile PESQ'yu varsayılana göre en fazla 0,07 artırıyor.
- DeepFilterNet CPU'da gerçek zamandan yaklaşık 7,5 kat hızlı çalışıyor (gerçek zaman oranı 0,134).

Ayrıntılı tablolar ve grafikler: [`results/analysis_tuned/summary.md`](results/analysis_tuned/summary.md) · parametre taraması: [`results/param_sweep/param_sweep.md`](results/param_sweep/param_sweep.md)

---

## ⚙️ Kurulum

> **Python 3.10 veya 3.11 gerekir.** DeepFilterNet'in bağımlı olduğu `torch==2.0.1`, Python 3.12 ve sonrası için yayınlanmadığından kurulum başarısız olur.

Windows (PowerShell), proje klasöründe:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- `py -3.11` bulunamazsa Python 3.11'i kurun: `winget install -e --id Python.Python.3.11`
- `Activate.ps1` "running scripts is disabled" hatası verirse bir kez şunu çalıştırın: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- macOS / Linux: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Kurulumu doğrulamak için:

```powershell
python -c "import torch, df, pesq, pystoi; print('tamam', torch.__version__)"
```

DeepFilterNet3 model ağırlıkları ilk çalıştırmada otomatik indirilir.

---

## 🎧 Veri Seti

**VoiceBank-DEMAND** (Valentini-Botinhao vd., 2016) test kümesini kullanıyoruz: 2 konuşmacı, 824 kayıt; her kaydın temiz ve gürültülü hali var; 5 gürültü türü (bus, cafe, living, office, psquare) ve 4 SNR seviyesi (2,5 / 7,5 / 12,5 / 17,5 dB).

Veri seti repoda **yoktur**. [Edinburgh DataShare](https://datashare.ed.ac.uk/handle/10283/2791) sayfasından şu üç dosyayı indirin:

- `clean_testset_wav.zip`
- `noisy_testset_wav.zip`
- `logfiles.zip`

ve `data/voicebank/` altına açın:

```powershell
mkdir data\voicebank
Expand-Archive "$HOME\Downloads\clean_testset_wav.zip" -DestinationPath data\voicebank
Expand-Archive "$HOME\Downloads\noisy_testset_wav.zip" -DestinationPath data\voicebank
Expand-Archive "$HOME\Downloads\logfiles.zip" -DestinationPath data\voicebank
```

Beklenen yapı (her iki klasörde 824 `.wav` olmalı):

```text
data/voicebank/
├── clean_testset_wav/   p232_001.wav ...
├── noisy_testset_wav/   p232_001.wav ...
└── log_testset.txt      (kayıt adı, gürültü türü, SNR)
```

---

## 🧪 Deneyleri Çalıştırma

Tüm komutlar proje kökünden, sanal ortam etkinken çalıştırılır. Çıktılar `outputs/` (ses dosyaları, repoya eklenmez) ve `results/` (tablolar ve grafikler) klasörlerine yazılır.

**1. Klasik yöntemler** (spektral çıkarma ve Wiener):
```powershell
python src\run_voicebank.py
```

**2. DeepFilterNet:**
```powershell
python src\enhance_deepfilternet.py --input_dir data\voicebank\noisy_testset_wav --output_dir outputs\voicebank\deepfilternet
```

**3. Ölçütler** (her yöntem için PESQ, STOI, SI-SDR → `results/metrics.csv`). Betik var olan dosyaya ekleme yaptığı için önce eskisini silin:
```powershell
Remove-Item results\metrics.csv -ErrorAction SilentlyContinue
$C = "data\voicebank\clean_testset_wav"
python src\metrics.py --clean $C --enhanced data\voicebank\noisy_testset_wav --method noisy
python src\metrics.py --clean $C --enhanced outputs\voicebank\spectral_subtraction --method spectral_subtraction
python src\metrics.py --clean $C --enhanced outputs\voicebank\wiener_filter --method wiener_filter
python src\metrics.py --clean $C --enhanced outputs\voicebank\deepfilternet --method deepfilternet
```

**4. Karşılaştırmalı analiz** (ortalamalar, iyileşme, Wilcoxon testi, SNR ve gürültü türü kırılımı, grafikler):
```powershell
python src\analysis.py --results results\metrics.csv --testset_log data\voicebank\log_testset.txt --out_dir results\analysis
```

**5. Klasik yöntemler için parametre taraması** (200 kayıtlık alt kümede; ses dosyası kaydetmez):
```powershell
python scripts\param_sweep.py
```
Seçilen ayarlarla 824 kaydın tamamını ölçüp analizi yenilemek için:
```powershell
python scripts\param_sweep.py --final --ss_alpha 1.0 --wf_factor 16
python src\analysis.py --results results\metrics_tuned.csv --testset_log data\voicebank\log_testset.txt --out_dir results\analysis_tuned
```

**6. Ek gürültü deneyi** (gerçek ortam gürültülerinin VoiceBank temiz kayıtlarına eklenmesi). Gürültü dosyalarını `data/extra_noise/` klasörüne koyduktan sonra:
```powershell
python src\make_extra_noise_set.py
python src\run_extra.py
python src\enhance_deepfilternet.py --input_dir data\extra_noise_set\noisy --output_dir outputs\extra_noise\deepfilternet
```

---

## 🖥️ Arayüz

```powershell
python app.py
```

Tarayıcıda `http://127.0.0.1:7860` adresini açın.

1. **Ses girişi:** dosya yükleme (`.wav`, `.mp3` vb.) veya canlı mikrofon kaydı.
2. **Yöntem seçimi:** spektral çıkarma (α ayarlanabilir), Wiener filtresi, DeepFilterNet ya da üçünü birden karşılaştırma.
3. **Görselleştirme:** her yöntem için dalga formu ve spektrogram.
4. **Ölçütler:** temiz referans kayıt da yüklenirse PESQ, STOI ve SI-SDR tablosu.

---

## 🏗️ Proje Yapısı

```text
gurultulu-konusma-iyilestirme/
├── app.py                         # Gradio arayüzü
├── ui/                            # Arayüz bileşenleri
├── assets/style.css               # Arayüz stilleri
├── src/
│   ├── preprocess.py              # Ses okuma/yazma (16 kHz mono), SNR'de karıştırma
│   ├── spectral_subtraction.py    # Spektral çıkarma
│   ├── wiener_filter.py           # Wiener filtresi
│   ├── enhance_deepfilternet.py   # DeepFilterNet3 ile toplu iyileştirme
│   ├── run_voicebank.py           # Klasik yöntemleri VoiceBank test kümesinde çalıştırma
│   ├── metrics.py                 # PESQ, STOI, SI-SDR hesaplama
│   ├── analysis.py                # Karşılaştırmalı analiz, istatistik testi, grafikler
│   ├── make_extra_noise_set.py    # Ek gürültü test setinin oluşturulması
│   ├── run_extra.py               # Klasik yöntemleri ek gürültü setinde çalıştırma
│   ├── pipeline.py                # Arayüz ile yöntemler arasındaki servis katmanı
│   └── visualization.py           # Dalga formu ve spektrogram çizimi
├── scripts/
│   ├── param_sweep.py             # Klasik yöntemler için parametre taraması
│   └── smoke_test.py              # Sentetik veriyle uçtan uca deneme
├── results/                       # Sonuç tabloları ve grafikler
├── docs/                          # Ek dokümantasyon
├── data/                          # Veri seti (repoda yok)
├── outputs/                       # İyileştirilmiş ses dosyaları (repoya eklenmez)
└── requirements.txt
```

---

## 📝 Notlar

- **Örnekleme frekansı:** DeepFilterNet 48 kHz ile çalışır; girdi 48 kHz'e çevrilip modele verilir, çıktı 16 kHz'e indirilir. Tüm ölçütler 16 kHz'de hesaplanır (geniş bant PESQ 16 kHz gerektirir).
- **Parametre seçimi:** klasik yöntemlerin ayarları test kümesinin 200 kayıtlık bir alt kümesinde seçilmiş ve tüm kümede raporlanmıştır; ayrı bir doğrulama kümesi kullanılmamıştır.
- **Ses dosyalarını repoya eklemeyin.** `data/` ve `outputs/` klasörleri `.gitignore` içindedir; veri seti ve çıktılar yukarıdaki adımlarla yeniden üretilebilir (ek gürültü seti sabit rastgelelik tohumuyla üretildiği için herkeste aynıdır).

---

## Kaynaklar

- Valentini-Botinhao, C., Wang, X., Takaki, S., & Yamagishi, J. (2016). Investigating RNN-based speech enhancement methods for noise-robust text-to-speech. *9th ISCA Speech Synthesis Workshop*.
- Schröter, H., Escalante-B., A. N., Rosenkranz, T., & Maier, A. (2022). DeepFilterNet: A low complexity speech enhancement framework for full-band audio based on deep filtering. *ICASSP 2022*.
- Boll, S. F. (1979). Suppression of acoustic noise in speech using spectral subtraction. *IEEE Trans. ASSP*, 27(2).
- Rix, A. W. vd. (2001). Perceptual evaluation of speech quality (PESQ). *ICASSP 2001*.
- Taal, C. H. vd. (2011). An algorithm for intelligibility prediction of time-frequency weighted noisy speech. *IEEE TASLP*, 19(7).
- Le Roux, J. vd. (2019). SDR – half-baked or well done? *ICASSP 2019*.
