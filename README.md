
***

```markdown
# ☀️ SOLARIS V2
### Jeomanyetik Fırtına Otonom Erken Uyarı Sistemi

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/durum-aktif-success.svg)
![License](https://img.shields.io/badge/lisans-MIT-green.svg)

**Solaris V2 nedir?** Güneş'ten Dünya'ya doğru gelen tehlikeli uzay fırtınalarını (Güneş patlamaları vb.) uydulardan takip eden bir sistemdir. 
Tehlike anında bir insanın düğmeye basmasını beklemez; kendi kendine karar verir ve sistemi kırmızı alarma geçirir.

---

## 💡 En Çok Merak Edilenler (Hızlı Cevaplar)

* **Sistemi test etmek için şifre veya API Key girmeli miyim?** * **HAYIR.** Sistem, uzay verilerini NASA ve NOAA'nın halka açık kaynaklarından çeker.
  * Hiçbir ayar yapmadan, direkt başlatıp 3D dünyayı ve grafikleri canlı izleyebilirsiniz.

* **Peki `.env` dosyası ne işe yarıyor?** * Kriz anında yapay zekanın durum raporu yazmasını isterseniz gereklidir.
  * İsterseniz klasördeki `.env` dosyasının içine kendi `API_KEY` bilginizi girebilirsiniz. 
  * Girmezseniz sistem çökmez, sadece standart acil durum mesajları gösterir.

* **İnternetsiz çalışır mı?**
  * Hayır. NASA'dan anlık veri çektiği için aktif internet bağlantısı şarttır.

---

## 🚀 Sistemi Bilgisayarda Çalıştırma Rehberi

Sistemi denemek çok basittir. Lütfen adımları sırasıyla uygulayın.
*(Not: Bilgisayarınızda Python yüklü olmalıdır.)*

### ADIM 1: Dosyaları İndirin
1. Bu sayfanın sağ üstündeki yeşil **"<> Code"** butonuna tıklayın.
2. **"Download ZIP"** seçeneğine tıklayıp indirin.
3. İnen dosyayı masaüstünde bir klasöre çıkartın.

### ADIM 2: Gerekli Kurulumları Yapın
1. Çıkarttığınız proje klasörünün içine girin.
2. Klasörün en üstündeki **adres çubuğuna** tıklayın, içindekileri silip **`cmd`** yazın ve Enter'a basın.
3. Açılan siyah ekrana şu kodu yapıştırıp Enter'a basın:
   ```bash
   pip install -r requirements.txt
   ```
*(Yüklemenin bitmesini bekleyin).*

### ADIM 3: Motorları Çalıştırın
Sistemimiz çökme riskine karşı iki farklı motorla çalışır. İkisini de başlatmalıyız.

**1. Veri Motoru:** Açık olan siyah ekrana şu kodu yazıp Enter'a basın:
```bash
python solaris_baslat.py
```
*(Bu motor NASA'dan veri çekmeye başlar. Bu ekranı kapatmayın, aşağı indirin).*

**2. Web Sunucusu:** Klasörün adres çubuğuna tekrar **`cmd`** yazıp İKİNCİ bir siyah ekran açın. Şunu yazın:
```bash
python web_sunucu.py
```
*(Bu köprü görevini görür. Bunu da kapatmayın, aşağı indirin).*

### ADIM 4: Web Sitesini Açın
Motorlar arka planda çalışırken proje klasöründeki **`Arayuz_UI`** klasörüne girin. 
Oradaki **`index.html`** dosyasına çift tıklayarak tarayıcınızda açın.
*(Verilerin NASA'dan inip ekrana yansıması 5-10 saniye sürebilir).*

---

## 🚨 Büyük Test (Kırmızı Alarm Simülasyonu)

Her şey yeşil ve sakinken, sistemin kriz anında nasıl karar aldığını görmek ister misiniz?

1. Tarayıcıda arayüz açıkken, proje klasöründe **üçüncü bir komut ekranı (cmd)** açın.
2. Şu kodu yapıştırıp Enter'a basın:
   ```bash
   python kriz_tetikle.py
   ```
3. **Hemen tarayıcıya (web sitesine) geri dönün ve izleyin:**
   * Rüzgar hızı aniden 800+ km/s seviyesine fırlar.
   * Tehdit Skoru 9.8'e vurur.
   * Sistem insan müdahalesi olmadan **Kırmızı Alarm** (Massive Explosion) protokolüne geçer.

---
*Cosmic Balance Ekibi Tarafından TUA Astro Hackathon İçin Geliştirilmiştir.* 🚀
```
