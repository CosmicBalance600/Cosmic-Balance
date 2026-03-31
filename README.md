

***

```markdown
# ☀️ Solaris V2 - Jeomanyetik Fırtına Otonom Erken Uyarı Sistemi

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Uzay kaynaklı jeomanyetik fırtınaları gerçek zamanlı izleyen ve insan müdahalesiz (otonom) kriz protokolleri tetikleyen erken uyarı ağı.**

</div>

---

## 💡 Akıldaki Sorular (Hızlı Yanıtlar)

* **Çalıştırmak için API Key (Şifre) Zorunlu mu?** * **HAYIR.** Sistem, güneş rüzgarı ve plazma verilerini NASA/NOAA'nın halka açık sunucularından çeker. Hiçbir şifre girmeden sistemi başlatıp grafikleri ve 3D dünyayı canlı izleyebilirsiniz.
* **Yapay Zeka Raporu Nasıl Çalışır?** * Kriz anında yapay zekanın (Claude) durum raporu yazmasını isterseniz, klasördeki `.env` dosyasının içine kendi `API_KEY` bilginizi girebilirsiniz. Girmezseniz sistem çökmez, standart askeri durum mesajları üretir.
* **Sistem İnternetsiz Çalışır mı?**
  * Verileri NASA'dan çektiği için aktif bir internet bağlantısı gerektirir.

---

## 🚀 Kurulum ve Çalıştırma Rehberi (Adım Adım)

Jüri üyelerinin ve geliştiricilerin sistemi kendi bilgisayarlarında test edebilmesi için en basit kurulum adımları aşağıdadır. Sistem **Python 3.10 veya üzeri** gerektirir.

### 1. Dosyaları Bilgisayarınıza İndirin
* Sayfanın sağ üst köşesindeki yeşil **"<> Code"** butonuna tıklayın.
* **"Download ZIP"** seçeneğini seçin ve inen dosyayı bir klasöre çıkartın.
* *(Geliştiriciler için alternatif: `git clone https://github.com/CosmicBalance600/Cosmic-Balance.git`)*

### 2. Gerekli Kütüphaneleri Kurun
1. Çıkarttığınız proje klasörünün içine girin.
2. Üstteki **dosya yolu (adres) çubuğuna** tıklayın, içindeki her şeyi silip **`cmd`** yazın ve Enter'a basın. (Siyah bir komut ekranı açılacaktır).
3. Açılan ekrana şu kodu yapıştırıp Enter'a basın:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Sistemi Başlatın (Motorları Ateşleme)
Sistemimiz, çökme riskine karşı iki ayrı asenkron motorla çalışır. Proje klasörünüzde iki farklı komut ekranı (cmd) açmanız gerekir.

**Terminal 1 (Veri Toplama Motoru):**
NASA'dan verileri çekmeye başlar. Bu ekranı açıp simge durumuna küçültün.
```bash
python solaris_baslat.py
```

**Terminal 2 (Web Sunucusu):**
Yeni bir `cmd` ekranı daha açın ve arayüz köprüsünü başlatın. Bunu da küçültün.
```bash
python web_sunucu.py
```

**Arayüze Giriş:**
Motorlar çalıştıktan sonra proje klasöründeki **`Arayuz_UI`** klasörüne girin ve **`index.html`** dosyasına çift tıklayarak tarayıcınızda açın. *(Verilerin NASA'dan inip ekrana yansıması 5-10 saniye sürebilir).*

---

## 🚨 Kriz Simülasyonu (Büyük Test)
Sistemin kriz anında (bir Güneş Patlaması Dünya'yı vurduğunda) otonom olarak nasıl karar aldığını görmek için şu testi uygulayın:

1. Tarayıcıda arayüz açık ve sakin durumdayken, proje klasöründe **üçüncü bir komut ekranı (cmd)** açın.
2. Şu komutu çalıştırın:
   ```bash
   python kriz_tetikle.py
   ```
3. **Hemen tarayıcıya geri dönün ve izleyin:** Rüzgar hızının aniden 800+ km/s seviyesine fırladığını, Tehdit Skorunun 9.8'e vurduğunu ve sistemin otonom olarak **Kırmızı Alarm** (Massive Explosion) protokolüne geçtiğini göreceksiniz.

---

## 📊 Sistem Mimarisi

```text
┌─────────────────────────────────────────────────────────────┐
│                    SOLARIS V2 - OTONOM AĞ                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   FAZ 1: VERİ MERKEZİ (veri_merkezi.py) │
        └─────────────────────────────────────────┘
        │ • NASA/NOAA'dan 5 Paralel Sensör Verisi │
        │ • 15 Saniyelik Asenkron Toplama Döngüsü │
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   FAZ 2: ZEKA MERKEZİ (zeka_merkezi.py) │
        └─────────────────────────────────────────┘
        │ • Thread-Safe SQLite WAL Hafıza Kaydı   │
        │ • Çok Faktörlü Tehdit Puanlama (1-10)   │
        │ • Yapay Zeka (LLM) Rapor Üretimi        │
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │  FAZ 3: AKSİYON MERKEZİ (aksiyon_merkezi.py)│
        └─────────────────────────────────────────────┘
        │ • Tehdit Skoru ≥ 7.0 → Kriz Tetikleme       │
        │ • Havacılık/Enerji Otonom Webhook Uyarıları │
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   WEB DASHBOARD (3D UI & Chart.js)      │
        └─────────────────────────────────────────┘
```

## ✨ Temel Özellikler

* **Graceful Degradation:** NASA uydularından biri kopsa bile sistem çökmez, kalan uydularla çalışmaya devam eder.
* **Akıllı Fallback:** SDO güneş lekesi (Sunspot) sayılarını, sabit vermek yerine Kp indeksine göre dinamik hesaplar.
* **Otonom Bypass:** Kriz anında operatör onayı beklemeden kritik altyapılara kapatma/tahliye komutu iletir.

---

## 🔑 İsteğe Bağlı Ortam Değişkenleri (.env)
Yapay Zeka (AI) raporlaması ve otonom Discord bildirimleri için proje ana dizinindeki `.env` dosyasını kendi bilgilerinizle düzenleyebilirsiniz:

```env
API_KEY=sizin_yapay_zeka_api_anahtariniz
DISCORD_WEBHOOK_URL=sizin_discord_kanal_linkiniz
```

## 📝 Lisans
Bu proje [MIT Lisansı](LICENSE) altında açık kaynak olarak lisanslanmıştır.

<div align="center">
<b>Cosmic Balance Ekibi Tarafından TUA Astro Hackathon İçin Geliştirilmiştir 🚀</b>
</div>
```
