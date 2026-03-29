"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   SOLARIS-NETWORK :: Merkezi Konfigürasyon                  ║
║            Tüm Modüller İçin Tek Nokta Yapılandırma Dosyası                ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Sürüm   : 1.0.0                                                          ║
║  Açıklama : Sistem genelindeki tüm sabitleri (API URL'leri, eşik           ║
║             değerleri, timeout süreleri, döngü aralıkları, dosya            ║
║             yolları ve ANSI renk kodları) merkezi olarak barındırır.        ║
║             Diğer tüm modüller bu dosyadan import ederek kullanır.         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
#  PROJE KÖK DİZİNİ
# ═══════════════════════════════════════════════════════════════════════════════

PROJE_DIZINI = Path(__file__).resolve().parent

# ═══════════════════════════════════════════════════════════════════════════════
#  VERİTABANI YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

VERITABANI_YOLU = PROJE_DIZINI / "solaris_hafiza.db"

# ═══════════════════════════════════════════════════════════════════════════════
#  NOAA / SWPC API UÇ NOKTALARI
# ═══════════════════════════════════════════════════════════════════════════════

# Güneş Rüzgarı – Plazma & Manyetik Alan
PLAZMA_API_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json"
MANYETIK_API_URL = "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json"

# Jeomanyetik Aktivite – Kp İndeksi
KP_INDEKSI_API_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"

# Güneş Patlaması – X-Ray Flux
XRAY_FLARE_API_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"

# Radyasyon – Proton Flux (≥10 MeV integral protons)
PROTON_FLUX_API_URL = "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json"

# ═══════════════════════════════════════════════════════════════════════════════
#  WENOX AI API YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

WENOX_API_URL = "https://claude.wenox.co/v1/messages"
WENOX_MODEL = "claude-sonnet-4-6"
WENOX_MAKS_DENEME = 2
WENOX_BEKLEME_SURESI = 3

# ═══════════════════════════════════════════════════════════════════════════════
#  HTTP İSTEK YAPILANDIRMASI (Retry & Timeout)
# ═══════════════════════════════════════════════════════════════════════════════

MAKS_DENEME_SAYISI = 3          # Başarısız isteklerde maksimum tekrar deneme sayısı
BEKLEME_SURESI_SANIYE = 3       # Her başarısız denemeden sonra bekleme süresi
ISTEK_ZAMAN_ASIMI = 6           # HTTP isteği zaman aşımı (saniye) – Plazma/Manyetik - Bug #13 düzeltildi
KP_XRAY_ZAMAN_ASIMI = 5         # HTTP isteği zaman aşımı (saniye) – Kp/X-Ray/Proton - Bug #13 düzeltildi

# ═══════════════════════════════════════════════════════════════════════════════
#  ANALİZ MOTORU YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

ANALIZ_PENCERE_BOYUTU = 50      # Son N adet kayıt üzerinden analiz yapılır
SMA_PENCERE = 10                # SMA (Simple Moving Average) pencere boyutu

# ═══════════════════════════════════════════════════════════════════════════════
#  TEHDİT SKORU EŞİK DEĞERLERİ – NASA SWPC G-Scale Referanslarından
# ═══════════════════════════════════════════════════════════════════════════════

ESIK = {
    "hiz_sakin":        400.0,   # km/s – Normal güneş rüzgarı hızı üst sınırı
    "hiz_yukseldi":     500.0,   # km/s – Yükselmiş güneş rüzgarı
    "hiz_firtina":      700.0,   # km/s – Jeomagnetik fırtına eşiği
    "hiz_siddetli":     900.0,   # km/s – Şiddetli fırtına
    "yogunluk_yuksek":  20.0,    # p/cm³ – Yüksek plazma yoğunluğu
    "yogunluk_kritik":  50.0,    # p/cm³ – Kritik plazma yoğunluğu
    "bt_yuksek":        10.0,    # nT – Yüksek manyetik alan şiddeti
    "bt_firtina":       20.0,    # nT – Fırtına seviyesi alan şiddeti
    "bz_tehlike":       -5.0,    # nT – Güneye dönük Bz tehlike eşiği
    "bz_kritik":        -10.0,   # nT – Kritik güneye dönük Bz
    "ivme_uyari":       15.0,    # km/s/dk – Hız ivmelenmesi uyarı eşiği
    "proton_yuksek":    10.0,    # pfu – Yüksek proton akısı (S1 eşiği)
    "proton_kritik":    100.0,   # pfu – Kritik proton akısı (S2 eşiği)
    "proton_siddetli":  1000.0,  # pfu – Şiddetli proton fırtınası (S3 eşiği)
}

# ═══════════════════════════════════════════════════════════════════════════════
#  KRİZ PROTOKOLLERİ YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

KRIZ_ESIK_SKORU = 7.0           # Tehdit skoru ≥ bu değer → kriz protokolü tetiklenir

# Sanal Webhook uç nokta simülasyonları
WEBHOOK_HAVACILIK = "https://api.icao.int/solaris/polar-route-divert"
WEBHOOK_ENERJI = "https://api.energy-grid.gov/solaris/load-shed"
WEBHOOK_UYDU = "https://api.satops.space/solaris/safe-mode"

# ═══════════════════════════════════════════════════════════════════════════════
#  DAEMON ORKESTRATÖR YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

DONGU_ARALIGI_SANIYE = 15       # Döngü tekrar aralığı (NOAA Rate-Limit koruması)

# ═══════════════════════════════════════════════════════════════════════════════
#  FLASK WEB SUNUCU YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

# Rate Limiting
RATE_LIMIT_API = "5 per second"  # /api/* endpoint'leri için istek limiti

# ═══════════════════════════════════════════════════════════════════════════════
#  TERMİNAL ANSI RENK KODLARI (Tüm Modüller Tarafından Paylaşılır)
# ═══════════════════════════════════════════════════════════════════════════════

RENK_KIRMIZI = "\033[91m"
RENK_YESIL   = "\033[92m"
RENK_SARI    = "\033[93m"
RENK_MAVI    = "\033[94m"
RENK_MOR     = "\033[95m"
RENK_CYAN    = "\033[96m"
RENK_BEYAZ   = "\033[97m"
RENK_TURUNCU = "\033[38;5;208m"
RENK_PARLAK  = "\033[1m"
RENK_DIM     = "\033[2m"
RENK_SIFIRLA = "\033[0m"
