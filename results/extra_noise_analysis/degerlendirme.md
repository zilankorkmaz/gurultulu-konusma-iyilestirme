# Ek Gürültü Deneyi – Teknik Değerlendirme

Ek gürültü setinde (800 kayıt; classroom, crowd, people ve group_talking gürültüleri; 2,5–17,5 dB SNR) DeepFilterNet üç ölçütte de en başarılı yöntemdir. Ortalama değerleri PESQ 2,23, STOI 0,877 ve SI-SDR 13,7 dB'dir. Spektral çıkarma 1,67 / 0,828 / 11,4 dB, Wiener filtresi 1,64 / 0,838 / 11,2 dB değerlerinde kalmıştır. Farklar eşleştirilmiş Wilcoxon testine göre istatistiksel olarak anlamlıdır (p < 0,001).

DeepFilterNet, dört gürültü türü ile dört SNR seviyesinin oluşturduğu 16 durumun tamamında PESQ'da en iyi sonucu vermiştir. Klasik yöntemlere göre üstünlüğü 0,37 ile 0,72 PESQ arasındadır; en büyük fark classroom gürültüsünde görülmüştür (Tablo 4). Üstünlüğü en çok düşük SNR'de belirginleşir: 2,5 dB'de SI-SDR'de klasik yöntemlerin yaklaşık 5,4 dB önündedir. 17,5 dB'de ise fark kapanır ve SI-SDR'de Wiener filtresi (18,5 dB) ile spektral çıkarma (17,9 dB) DeepFilterNet'i (17,2 dB) geçer (Tablo 3). Bu sonuç, temiz kayda yakın durumlarda modelin sinyali gereğinden fazla değiştirdiğini düşündürmektedir.

Gürültü türleri arasında en zor olanlar konuşma benzeri gürültülerdir: group_talking ve classroom'da üç yöntem de en düşük PESQ ve STOI değerlerini almıştır. En kolay gürültü crowd olmuştur (Tablo 2). İki klasik yöntem birbirine çok yakındır. Spektral çıkarma PESQ ve SI-SDR'de, Wiener filtresi ise her SNR seviyesinde ve her gürültü türünde STOI'de (anlaşılırlıkta) hafifçe öndedir.

VoiceBank-DEMAND sonuçlarıyla karşılaştırıldığında, DeepFilterNet'in PESQ değeri 3,16'dan 2,23'e düşmüştür. Bu da ek setteki konuşma benzeri gürültülerin tüm yöntemler için daha zorlayıcı olduğunu göstermektedir.

**Not:** Ek setin işlenmemiş (gürültülü) kayıtları repoda bulunmadığından, yöntemlerin gürültülü kayda göre sağladığı iyileşme bu analizde ölçülmemiştir.

Tablolar ve grafikler: [`summary.md`](summary.md) · üretmek için: `python scripts/evaluate_extra_noise.py`
