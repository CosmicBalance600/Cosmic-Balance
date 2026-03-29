# 🚀 Solaris V2: Jeomanyetik Fırtınalar İçin Otonom Erken Uyarı Sistemi

Solaris V2, uzay kaynaklı jeomanyetik fırtınaları (güneş patlamaları, rüzgarları vb.) tespit edip otonom olarak uçuş rotalarını (kutuplar) ve enerji şebekelerini güvence altına almayı simüle eden, yüksek performanslı erken uyarı sistemidir.

NASA, NOAA ve GOES verilerini 5 farklı (yedekli) asenkron paralel hattan gerçek zamanlı toplayarak tehdit puanlaması yapar ve gerekirse otonom protokolleri tetikler.

## 🌟 Özellikler
- **Gerçek Zamanlı Veri Füzyonu:** 5 farklı kaynaktan (Plazma, Manyetizma, X-Ray, Proton ve Kp) veri toplanıp analiz edilir.
- **Yapay Zeka Destekli Analiz:** Wenox Claude (AI) yardımı ile fırtınalara ait özetleme raporu sunulur.
- **Thread-safe & Dirençli Sistem:** SQLite WAL modu ve kesintisiz retry mekanizmalarıyla hata (çökme) önlenir.
- **Dinamik 3D Dashboard:** Anlık verilerin işlendiği üç boyutlu dünya modülasyonu (Three.js/WebGL tabanlı) ve 6 farklı ChartJS grafiği.
- **Graceful Degradation:** API'lerin biri çökse dahi operasyonlarına kesinti yapmadan devam eder.

## 🛠 Kurulum ve Çalıştırma

### 1️⃣ Ön Koşullar
- Python 3.9 veya daha yüksek bir sürüm.
- İşletim sisteminize uygun *pip* paketi.

### 2️⃣ Ortam Değişkenlerini Ayarlama
Güvenliğiniz için API anahtarlarınızı `.env` isimli dosyada barındırmanız gerekmektedir:
```bash
# Şablonu kopyalayarak asıl env doyanızı oluşturun:
# (Windows)
copy .env.example .env
# (Linux/Mac)
cp .env.example .env
```
*(Dosya içerisindeki `WENOX_API_KEY` değişkenini kendi API anahtarınız ile güncelleyin.)*

### 3️⃣ Bağımlılıkları Yükleme
```bash
pip install -r requirements.txt
```

### 4️⃣ Sistemi Başlatma (Terminal 1 - Orkestratör)
Veri toplama, makine zekasına veriyi yedirme, fırtına dinleme için (daemon) motorunu başlatın:
```bash
python solaris_baslat.py
```

### 5️⃣ Web Arayüzünü Başlatma (Terminal 2 - Server)
Sisteminizdeki değişimleri dışarı çıkartıp görselleştiren web arka ucunu (Flask backend) devreyi alın:
```bash
python web_sunucu.py
```
Arayüze an itibariyle tarayıcınızdan `http://localhost:5000` yazılarak ulaşılabilir.

---
## 🐳 Docker ile Tek Tıkla Kurulum (Önerilen)
Bilgisayarınızda Docker yüklüyse, Python testlerine gerek duymadan direkt çalıştırabilirsiniz:
```bash
docker-compose up -d --build
```

---
## 📄 Katkı Sağlama / Lisans
Bu proje **MIT Lisansı** altında özgür (Open Source) yazılımdır. Verilen kural çerçevesi boyunca rahatlıkta değiştirebilir, ticari projelerinizde kaynak gösterebilirsiniz. Tüm detaylar `LICENSE` dosyasında bulunabilir.
