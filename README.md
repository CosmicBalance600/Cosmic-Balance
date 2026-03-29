# ☀️ Solaris V2 - Jeomanyetik Fırtına Erken Uyarı Sistemi

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Uzay kaynaklı jeomanyetik fırtınaları gerçek zamanlı izleyen ve otonom kriz protokolleri tetikleyen açık kaynak erken uyarı sistemi**

[Özellikler](#-özellikler) • [Kurulum](#-kurulum) • [Kullanım](#-kullanım) • [Mimari](#-sistem-mimarisi) • [Katkıda Bulunma](#-katkıda-bulunma)

</div>

---

## 📖 Hakkında

Solaris V2, NASA ve NOAA'nın uzay havası verilerini gerçek zamanlı analiz ederek jeomanyetik fırtınaları tespit eden ve kritik altyapıları korumak için otonom protokoller tetikleyen gelişmiş bir erken uyarı sistemidir.

Sistem, güneş patlamaları, güneş rüzgarı hızı, manyetik alan değişimleri ve radyasyon seviyelerini 5 farklı sensör üzerinden sürekli izler ve yapay zeka destekli analiz ile tehdit seviyesini değerlendirir.

### 🎯 Kullanım Alanları

- **Havacılık**: Kutup rotalarında uçan uçaklar için radyasyon uyarıları
- **Enerji Şebekeleri**: Jeomagnetik fırtınaların neden olduğu güç kesintilerine karşı koruma
- **Uydu Operasyonları**: Uzay araçları için güvenli mod protokolleri
- **Bilimsel Araştırma**: Uzay havası verilerinin analizi ve modellenmesi

---

## ✨ Özellikler

### 🔄 Gerçek Zamanlı Veri Toplama
- **5 Paralel Sensör**: Plazma, Manyetik Alan, Kp İndeksi, X-Ray, Proton Flux
- **Yedekli Sistem**: API hatalarında otomatik retry mekanizması
- **Graceful Degradation**: Bir sensör çökse bile sistem çalışmaya devam eder

### 🧠 Yapay Zeka Destekli Analiz
- **Claude AI Entegrasyonu**: Tehdit raporlarının otomatik özetlenmesi
- **Zaman Serisi Analizi**: SMA, ivmelenme ve trend tespiti
- **Tehdit Puanlama**: NASA SWPC G-Scale referanslı 1-10 arası skorlama
- **Fırtına Tahmini**: 72+ saat önceden risk değerlendirmesi

### 💾 Kalıcı Hafıza Sistemi
- **SQLite Veritabanı**: WAL modu ile thread-safe veri saklama
- **Tarihsel Analiz**: Geçmiş verilere dayalı trend analizi
- **Otomatik Arşivleme**: Tüm ölçümler ve analizler kaydedilir

### 🎨 İnteraktif Dashboard
- **3D Dünya Görselleştirmesi**: Three.js ile gerçek zamanlı animasyon
- **6 Farklı Grafik**: ChartJS ile detaylı veri görselleştirme
- **Canlı Güncelleme**: WebSocket benzeri polling ile anlık veri akışı
- **Responsive Tasarım**: Mobil ve masaüstü uyumlu

### 🚨 Otonom Kriz Yönetimi
- **Otomatik Tetikleme**: Tehdit skoru ≥ 7.0 olduğunda protokoller devreye girer
- **Webhook Bildirimleri**: Kritik sistemlere anlık uyarı gönderimi
- **Simülasyon Modu**: Test amaçlı kriz senaryoları

---

## 🚀 Kurulum

### Ön Koşullar

- Python 3.9 veya üzeri
- pip paket yöneticisi
- (Opsiyonel) Docker ve Docker Compose

### Hızlı Başlangıç

#### 1️⃣ Depoyu Klonlayın

```bash
git clone https://github.com/yourusername/solaris-v2.git
cd solaris-v2
```

#### 2️⃣ Ortam Değişkenlerini Ayarlayın

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

`.env` dosyasını düzenleyip API anahtarınızı ekleyin:

```env
API_KEY=your_wenox_api_key_here
```

> 💡 **Not**: Wenox API anahtarı için [claude.wenox.co](https://claude.wenox.co) adresinden ücretsiz hesap oluşturabilirsiniz.

#### 3️⃣ Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

#### 4️⃣ Sistemi Başlatın

**Terminal 1 - Veri Toplama ve Analiz Motoru:**
```bash
python solaris_baslat.py
```

**Terminal 2 - Web Dashboard:**
```bash
python web_sunucu.py
```

Dashboard'a tarayıcınızdan `http://localhost:5000` adresinden erişebilirsiniz.

---

## 🐳 Docker ile Kurulum (Önerilen)

Docker kullanarak tüm sistemi tek komutla başlatabilirsiniz:

```bash
# .env dosyanızı oluşturun
cp .env.example .env

# Konteynerleri başlatın
docker-compose up -d --build
```

Servisler:
- **solaris_daemon**: Veri toplama ve analiz motoru
- **solaris_web**: Web dashboard (http://localhost:5000)

Logları görüntülemek için:
```bash
docker-compose logs -f
```

Servisleri durdurmak için:
```bash
docker-compose down
```

---

## 📊 Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLARIS-NETWORK v2.0                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   FAZ 1: VERİ MERKEZİ (veri_merkezi.py) │
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │  5 Paralel Sensör (Asenkron Toplama)     │
        ├───────────────────────────────────────────┤
        │  • Plazma (Yoğunluk, Hız, Sıcaklık)      │
        │  • Manyetik Alan (Bt, Bz, Bx, By)        │
        │  • Kp İndeksi (Jeomanyetik Aktivite)     │
        │  • X-Ray Flux (Güneş Patlamaları)        │
        │  • Proton Flux (Radyasyon Seviyesi)      │
        └───────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   FAZ 2: ZEKA MERKEZİ (zeka_merkezi.py) │
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │  Analiz Modülleri                         │
        ├───────────────────────────────────────────┤
        │  • SQLite Kalıcı Hafıza (WAL Mode)       │
        │  • Zaman Serisi Analizi (SMA, Trend)     │
        │  • Tehdit Puanlama (1-10 Skala)          │
        │  • Fırtına Tahmini (72+ Saat)            │
        │  • Claude AI Rapor Üretimi               │
        └───────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │  FAZ 3: AKSİYON MERKEZİ (aksiyon_merkezi.py)│
        └─────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │  Kriz Protokol Denetimi                   │
        ├───────────────────────────────────────────┤
        │  • Tehdit Skoru ≥ 7.0 → Kriz Tetikleme   │
        │  • Webhook Bildirimleri                   │
        │  • Havacılık / Enerji / Uydu Uyarıları   │
        └───────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │   WEB DASHBOARD (web_sunucu.py)         │
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │  Flask REST API + Frontend                │
        ├───────────────────────────────────────────┤
        │  • /api/canli_veri (Anlık Telemetri)     │
        │  • /api/tarihsel (Grafik Verileri)       │
        │  • /api/uydu_verileri (Uydu Bilgileri)   │
        │  • 3D Dünya Görselleştirmesi (Three.js)  │
        │  • 6 ChartJS Grafiği                     │
        └───────────────────────────────────────────┘
```

---

## 🔧 Yapılandırma

Tüm sistem ayarları [`config.py`](Solaris_V2_Open/config.py) dosyasında merkezi olarak yönetilir:

### Önemli Parametreler

```python
# Döngü aralığı (saniye)
DONGU_ARALIGI_SANIYE = 15

# Kriz tetikleme eşiği
KRIZ_ESIK_SKORU = 7.0

# Tehdit skoru eşik değerleri
ESIK = {
    "hiz_firtina": 700.0,      # km/s
    "bz_tehlike": -5.0,        # nT
    "proton_yuksek": 10.0,     # pfu
}

# Flask sunucu
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
```

---

## 📡 API Endpoints

### `GET /api/canli_veri`
Anlık telemetri ve analiz verileri

**Yanıt:**
```json
{
  "tehdit_skoru": 1.5,
  "tehdit_seviyesi": "SAKİN",
  "ruzgar_hizi": 354.7,
  "plazma_yogunluk": 1.28,
  "bt_toplam": 7.26,
  "bz_yonu": -4.29,
  "kp_degeri": 3.67,
  "xray_flux": 1.00e-06,
  "proton_flux": 0.15
}
```

### `GET /api/tarihsel`
Son 50 ölçümün grafik verisi

### `GET /api/uydu_verileri`
DSCOVR, ACE, GOES-16, SDO uydu bilgileri

---

## 🗄️ Veritabanı Şeması

### `telemetri` Tablosu
Güneş rüzgarı ölçümleri
- `id`, `zaman`, `ruzgar_hizi`, `plazma_yogunluk`, `bt_toplam`, `bz_yonu`
- `kp_degeri`, `xray_flux`, `proton_flux`

### `analiz_sonuclari` Tablosu
Tehdit skorları ve AI raporları
- `id`, `zaman`, `tehdit_skoru`, `tehdit_seviyesi`
- `hiz_sma`, `trend_yonu`, `firtina_olasilik`
- `yapay_zeka_raporu`

### `aksiyon_loglari` Tablosu
Kriz protokol kayıtları
- `id`, `zaman`, `tehdit_skoru`, `protokol_tetiklendi`
- `bildirim_detaylari`

---

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen [CONTRIBUTING.md](CONTRIBUTING.md) dosyasını okuyun.

### Geliştirme Süreci

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

### Kod Standartları

- PEP 8 Python stil rehberine uyun
- Docstring'leri eksiksiz yazın
- Type hint'leri kullanın
- Unit testler ekleyin

---

## 📝 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır. Detaylar için LICENSE dosyasına bakın.

---

## 🙏 Teşekkürler

Bu proje aşağıdaki açık kaynak projeleri ve veri kaynaklarını kullanmaktadır:

- **Veri Kaynakları**
  - [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov/)
  - [NASA](https://www.nasa.gov/)
  - [GOES Satellite Data](https://www.goes.noaa.gov/)

- **Teknolojiler**
  - [Python](https://www.python.org/)
  - [Flask](https://flask.palletsprojects.com/)
  - [Three.js](https://threejs.org/)
  - [Chart.js](https://www.chartjs.org/)
  - [SQLite](https://www.sqlite.org/)

---

## 📞 İletişim

Proje Sahibi: Solaris Mühendislik Ekibi

Proje Linki: [https://github.com/yourusername/solaris-v2](https://github.com/yourusername/solaris-v2)

---

## 🔮 Gelecek Planları

- [ ] Machine Learning tabanlı fırtına tahmini
- [ ] Telegram/Discord bot entegrasyonu
- [ ] Mobil uygulama (React Native)
- [ ] Çoklu dil desteği
- [ ] Grafana dashboard entegrasyonu
- [ ] Prometheus metrics export
- [ ] Kubernetes deployment manifests

---

<div align="center">

**⭐ Projeyi beğendiyseniz yıldız vermeyi unutmayın!**

Made with ☀️ by Solaris Engineering Team

</div>
