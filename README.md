# Gürültülü Konuşma Kayıtlarının İyileştirilmesi

Bu proje, **Bilgisayar Mühendisliği Tasarımı** dersi kapsamında geliştirilmiş olup; gürültülü konuşma kayıtlarındaki arka plan gürültülerini geleneksel sinyal işleme algoritmaları ve derin öğrenme modelleri ile temizlemeyi, nesnel ölçütlerle (PESQ, STOI, SI-SDR) analiz etmeyi ve etkileşimli bir web arayüzü sunmayı amaçlar.

---

## 🚀 Hızlı Başlangıç (Arayüzü Çalıştırma)

Projeyi Gradio web arayüzü ile başlatmak için terminalde aşağıdaki komutu çalıştırınız:

```powershell
.\venv\Scripts\python app.py
```

Komutu çalıştırdıktan sonra terminalde verilen yerel adrese (varsayılan: `http://127.0.0.1:7860`) tarayıcınızdan erişebilirsiniz.

---

## 🎧 Arayüz Yetenekleri

1. **Ses Girişi:** Bilgisayardan ses dosyası (`.wav`, `.mp3` vb.) yükleme veya doğrudan **canlı mikrofon** ile konuşma kaydetme.
2. **Yöntem Seçimi:**
   * **Spektral Çıkarma (Spectral Subtraction):** `Alpha` katsayısı slider ile ayarlanabilir.
   * **Wiener Filtresi (Wiener Filter):** Güç spektrumu kestirimi tabanlı filtreleme.
   * **DeepFilterNet (Deep Learning):** İki aşamalı derin yapay sinir ağı tabanlı model.
   * **Tümünü Karşılaştır (A/B/C Testi):** Üç yöntemi de aynı anda çalıştırarak karşılaştırmalı dinleme ve analiz imkanı.
3. **Zaman ve Frekans Analizi:** Her yöntem için **Dalga Formu (Waveform)** ve dB ölçeğinde renklendirilmiş **Spektrogram (Spectrogram)** grafikleri.
4. **Metrik ve İstatistik Raporu:** Veri seti üzerinde yapılan nesnel test ölçütleri ve gürültü türlerine göre başarım grafikleri.

---

## 🏗️ Proje Mimarisi

```text
gurultulu-konusma-iyilestirme/
│
├── data/                      # Gürültülü ve temiz ses veri kümesi
├── docs/                      # Metrik analizleri ve grafikler
├── outputs/                   # İşlenen seslerin kaydedildiği klasörler
│
├── src/                       # Çekirdek İşleme ve Servis Katmanı
│   ├── preprocess.py          # Ses normalizasyonu (16 kHz mono)
│   ├── spectral_subtraction.py# Spektral Çıkarma algoritması
│   ├── wiener_filter.py       # Wiener Filtresi algoritması
│   ├── enhance_deepfilternet.py# DeepFilterNet modeli çıkarım motoru
│   ├── analysis.py            # PESQ, STOI, SI-SDR analiz modülü
│   ├── visualization.py       # Dalga formu ve spektrogram çizim modülü
│   └── pipeline.py            # Servis katmanı (Arayüz ve algoritmalar köprüsü)
│
├── app.py                     # Gradio Web Arayüzü (Sunum Katmanı)
├── requirements.txt           # Bağımlılıklar listesi
└── README.md                  # Proje dokümantasyonu
```
