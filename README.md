***

# ☀️ SOLARIS V2
### Jeomanyetik Fırtına Otonom Erken Uyarı Sistemi

Solaris V2, uzaydan gelen tehlikeli güneş fırtınalarını uydulardan takip eden bir erken uyarı sistemidir. Tehlike anında bir insanın düğmeye basmasını beklemez; tamamen otonom çalışır ve sistemi kendi kendine kırmızı alarma geçirir.

---

## 💡 En Çok Merak Edilenler

* Şifre veya API Key girmeli miyim?
Hayır. Sistem uzay verilerini NASA'nın halka açık kaynaklarından çeker. Hiçbir ayar yapmadan başlatabilirsiniz.

* .env dosyası ne işe yarıyor?
Kriz anında yapay zekanın durum raporu yazmasını isterseniz gereklidir. İsterseniz klasördeki .env dosyasının içine kendi API anahtarınızı girebilirsiniz. Girmezseniz sistem çökmez, sadece standart acil durum mesajları gösterir.

* İnternetsiz çalışır mı?
Hayır. Sistem anlık olarak uydulardan veri çektiği için aktif internet bağlantısı şarttır.

---

## 🚀 Sistemi Bilgisayarda Çalıştırma Rehberi

Sistemi test etmek çok basittir. Lütfen adımları sırasıyla uygulayın. (Not: Bilgisayarınızda Python yüklü olmalıdır.)

### ADIM 1: Dosyaları İndirin
1. Bu sayfanın sağ üstündeki yeşil "Code" butonuna tıklayın.
2. "Download ZIP" seçeneğine tıklayıp indirin.
3. İnen dosyayı masaüstünde bir klasöre çıkartın.

### ADIM 2: Gerekli Kurulumları Yapın
1. Çıkarttığınız proje klasörünün içine girin.
2. Klasörün en üstündeki adres çubuğuna tıklayın, içindeki yazıları silin.
3. Oraya sadece cmd yazın ve Enter tuşuna basın. Siyah bir komut ekranı açılacaktır.
4. Açılan siyah ekrana aşağıdaki kodu tam olarak kopyalayıp yapıştırın ve Enter'a basın:

pip install -r requirements.txt

(Yüklemenin bitmesini bekleyin.)

### ADIM 3: Motorları Çalıştırın
Sistemimiz iki farklı motorla çalışır. İkisini de başlatmalıyız.

1. Veri Motoru: Açık olan siyah ekrana aşağıdaki kodu kopyalayıp yapıştırın ve Enter'a basın:

python solaris_baslat.py

(Bu motor NASA'dan veri çekmeye başlar. Bu ekranı kapatmayın, aşağı indirin.)

2. Web Sunucusu: Klasörün adres çubuğuna tekrar cmd yazıp İKİNCİ bir siyah ekran daha açın. Aşağıdaki kodu kopyalayıp yapıştırın ve Enter'a basın:

python web_sunucu.py

(Bu ekran köprü görevini görür. Bunu da kapatmayın, aşağı indirin.)

### ADIM 4: Web Sitesini Açın
Motorlar arka planda çalışırken, proje klasöründeki Arayuz_UI klasörüne girin. Oradaki index.html dosyasına çift tıklayarak tarayıcınızda açın. 
(Verilerin inip ekrana yansıması 5-10 saniye sürebilir.)

---

## 🚨 Büyük Test (Kırmızı Alarm Simülasyonu)

Her şey yeşil ve sakinken, sistemin devasa bir kriz anında nasıl karar aldığını görmek ister misiniz?

1. Tarayıcıda arayüz (web sitesi) açıkken, proje klasöründe üçüncü bir komut ekranı (cmd) daha açın.
2. Aşağıdaki kodu kopyalayıp yapıştırın ve Enter'a basın:

python kriz_tetikle.py

3. Hemen web sitesine geri dönün ve izleyin:
- Rüzgar hızı aniden 800+ km/s seviyesine fırlar.
- Tehdit Skoru 9.8'e vurur.
- Sistem insan müdahalesi olmadan otonom bir şekilde Kırmızı Alarm (Massive Explosion) protokolüne geçer.

---
Cosmic Balance Ekibi Tarafından TUA Astro Hackathon İçin Geliştirilmiştir.
