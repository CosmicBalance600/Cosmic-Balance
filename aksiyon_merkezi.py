"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   SOLARIS-NETWORK :: Aksiyon Merkezi                        ║
║         Faz 3 – Otonom Kriz Protokolleri & Webhook Simülasyonu             ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Sürüm   : 3.0.0                                                          ║
║  Açıklama : Zeka Merkezi'nden gelen tehdit skorunu değerlendirir.          ║
║             Skor ≥ 7.0 olduğunda havacılık, enerji şebekesi ve            ║
║             uydu operatörlerine yönelik otonom kriz protokollerini          ║
║             tetikler. Tüm aksiyonlar SQLite'a loglanır.                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sqlite3
import uuid
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ── Ortam değişkenlerini yükle (.env) ──
_SCRIPT_DIZINI_ENV = Path(__file__).resolve().parent
load_dotenv(_SCRIPT_DIZINI_ENV / ".env")

# Discord Webhook URL'si (.env dosyasından okunur)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ═══════════════════════════════════════════════════════════════════════════════
#  SABİTLER (Constants)
# ═══════════════════════════════════════════════════════════════════════════════

# Kriz protokolü tetikleme eşik değeri
KRIZ_ESIK_SKORU = 7.0

# Veritabanı dosya yolu (proje kök dizininde solaris_hafiza.db)
_SCRIPT_DIZINI = Path(__file__).resolve().parent
VERITABANI_YOLU = _SCRIPT_DIZINI / "solaris_hafiza.db"

# Terminal çıktı renk kodları (ANSI)
R_KIRMIZI  = "\033[91m"
R_YESIL    = "\033[92m"
R_SARI     = "\033[93m"
R_MAVI     = "\033[94m"
R_MOR      = "\033[95m"
R_CYAN     = "\033[96m"
R_TURUNCU  = "\033[38;5;208m"
R_PARLAK   = "\033[1m"
R_DIM      = "\033[2m"
R_SIFIRLA  = "\033[0m"

# Sanal Webhook uç nokta simülasyonları
WEBHOOK_HAVACILIK = "https://api.icao.int/solaris/polar-route-divert"
WEBHOOK_ENERJI    = "https://api.energy-grid.gov/solaris/load-shed"
WEBHOOK_UYDU      = "https://api.satops.space/solaris/safe-mode"


# ═══════════════════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

def _utc_simdi() -> str:
    """Şu anki UTC zamanını ISO 8601 formatında döndürür."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(seviye: str, mesaj: str):
    """
    Renk kodlu, zaman damgalı terminal log çıktısı üretir.
    Seviyeler: AKSİYON, KRİZ, BİLGİ, UYARI, HATA, VERİTABANI
    """
    renk = {
        "AKSİYON":    R_TURUNCU,
        "KRİZ":       R_KIRMIZI,
        "BİLGİ":      R_YESIL,
        "UYARI":      R_SARI,
        "HATA":       R_KIRMIZI,
        "VERİTABANI": R_MAVI,
    }.get(seviye, R_SIFIRLA)
    print(f"{R_CYAN}[{_utc_simdi()}]{R_SIFIRLA} {renk}{R_PARLAK}[{seviye}]{R_SIFIRLA} {mesaj}")


# ═══════════════════════════════════════════════════════════════════════════════
#  VERİTABANI KATMANI – Aksiyon Log Kaydı
# ═══════════════════════════════════════════════════════════════════════════════

class AksiyonHafizasi:
    """
    Kriz protokollerinin aksiyon loglarını SQLite veritabanına kaydeder.
    `solaris_hafiza.db` içinde `aksiyon_loglari` tablosu kullanılır.
    """

    def __init__(self, veritabani_yolu: str = None):
        """
        Veritabanı bağlantısını başlatır ve aksiyon_loglari tablosunu oluşturur.

        Parametreler:
            veritabani_yolu: SQLite dosya yolu (varsayılan: solaris_hafiza.db)
        """
        self.yol = str(veritabani_yolu or VERITABANI_YOLU)
        self._baglanti = None
        self._tablo_olustur()

    def _baglan(self) -> sqlite3.Connection:
        """Veritabanı bağlantısı oluşturur veya mevcut bağlantıyı döndürür."""
        if self._baglanti is None:
            self._baglanti = sqlite3.connect(self.yol, timeout=10)
            self._baglanti.row_factory = sqlite3.Row
            self._baglanti.execute("PRAGMA journal_mode=WAL")
            self._baglanti.execute("PRAGMA synchronous=NORMAL")
        return self._baglanti

    def _tablo_olustur(self):
        """
        'aksiyon_loglari' tablosunu oluşturur (yoksa).

        Sütunlar:
            id           : Otomatik artan birincil anahtar
            zaman        : Aksiyon tetiklenme zamanı (UTC, ISO 8601)
            aksiyon_turu : Protokol türü (HAVACILIK / ENERJİ / UYDU)
            detay        : Aksiyonun detay açıklaması
        """
        conn = self._baglan()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS aksiyon_loglari (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman        TEXT    NOT NULL,
                aksiyon_turu TEXT    NOT NULL,
                detay        TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_aksiyon_zaman ON aksiyon_loglari(zaman)
        """)
        conn.commit()
        _log("VERİTABANI", "Aksiyon log hafızası hazır.")

    def kaydet(self, aksiyon_turu: str, detay: str) -> bool:
        """
        Tetiklenen bir kriz aksiyonunu veritabanına kaydeder.

        Parametreler:
            aksiyon_turu: Protokol türü (HAVACILIK_UYARISI / ENERJİ_SEBEKESI / UYDU_OPERATORU)
            detay       : Aksiyonun detay açıklaması

        Dönüş:
            bool: Kayıt başarılı ise True, hata oluşursa False
        """
        try:
            conn = self._baglan()
            zaman = _utc_simdi()
            conn.execute(
                """INSERT INTO aksiyon_loglari (zaman, aksiyon_turu, detay)
                   VALUES (?, ?, ?)""",
                (zaman, aksiyon_turu, detay)
            )
            conn.commit()
            _log("VERİTABANI", f"Aksiyon logu kaydedildi: [{aksiyon_turu}]")
            return True
        except Exception as hata:
            _log("HATA", f"Aksiyon log kayıt hatası: {hata}")
            return False

    def kapat(self):
        """Veritabanı bağlantısını güvenli şekilde kapatır."""
        if self._baglanti:
            self._baglanti.close()
            self._baglanti = None


# ═══════════════════════════════════════════════════════════════════════════════
#  KRİZ PROTOKOLLERİ – Sanal Webhook Simülasyonları
# ═══════════════════════════════════════════════════════════════════════════════

def havacilik_uyarisi_gonder(skor: float, seviye_tr: str, hafiza: AksiyonHafizasi) -> dict:
    """
    Kutup bölgesindeki uçuşların rotalarının acil değiştirilmesi için
    ICAO (Uluslararası Sivil Havacılık Örgütü) API simülasyonu.

    Fiziksel gerekçe:
        Şiddetli güneş fırtınalarında kutup rotaları yüksek radyasyon
        dozuna maruz kalır. HF radyo iletişimi kesilir ve GPS doğruluğu
        düşer. Uçuşların daha düşük enlem rotalarına yönlendirilmesi gerekir.

    Parametreler:
        skor      : Güncel tehdit skoru
        seviye_tr : Tehdit seviyesi açıklaması (Türkçe)
        hafiza    : AksiyonHafizasi veritabanı nesnesi

    Dönüş:
        dict: Sanal webhook yanıt simülasyonu
    """
    islem_id = str(uuid.uuid4())[:8].upper()

    print()
    print(f"  {R_KIRMIZI}{R_PARLAK}┌──────────────────────────────────────────────────────────────┐{R_SIFIRLA}")
    print(f"  {R_KIRMIZI}{R_PARLAK}│  ✈  HAVACILIK ACIL UYARI PROTOKOLü – DEVREDE                │{R_SIFIRLA}")
    print(f"  {R_KIRMIZI}{R_PARLAK}└──────────────────────────────────────────────────────────────┘{R_SIFIRLA}")
    print()
    _log("KRİZ", f"[WEBHOOK] POST → {WEBHOOK_HAVACILIK}")
    _log("KRİZ", f"[İŞLEM-ID: {islem_id}] Kutup uçuş rotası değiştirme talebi gönderiliyor...")
    _log("KRİZ", f"  ├─ Tehdit Skoru    : {skor}/10.0 ({seviye_tr})")
    _log("KRİZ", f"  ├─ Etkilenen Bölge : Kuzey Kutbu (60°N – 90°N) & Güney Kutbu (60°S – 90°S)")
    _log("KRİZ", f"  ├─ Öneri           : Tüm transarktik uçuşlar alt enlem rotalarına yönlendirilsin")
    _log("KRİZ", f"  ├─ HF Radyo Durumu : KESİNTİ BEKLENİYOR – Uydu iletişimine geçilsin")
    _log("KRİZ", f"  └─ Simülasyon Yanıt: HTTP 200 OK – Rota değişikliği emri alındı ✓")

    detay = (
        f"İşlem-ID: {islem_id} | Tehdit: {skor}/10 ({seviye_tr}) | "
        f"Kutup rotaları (60°N-90°N, 60°S-90°S) için acil rota değişikliği emri | "
        f"Transarktik uçuşlar alt enlem rotalarına yönlendirildi | "
        f"Webhook: {WEBHOOK_HAVACILIK}"
    )
    hafiza.kaydet("HAVACILIK_UYARISI", detay)

    return {
        "protokol": "HAVACILIK_UYARISI",
        "islem_id": islem_id,
        "durum": "TETIKLENDI",
        "webhook": WEBHOOK_HAVACILIK,
        "simulasyon_yanit": "HTTP 200 OK",
    }


def enerji_sebekesi_uyarisi(skor: float, seviye_tr: str, hafiza: AksiyonHafizasi) -> dict:
    """
    Elektrik şebekesi yük azaltma (load shedding) protokolü.
    Trafo merkezlerine acil sinyal gönderir.

    Fiziksel gerekçe:
        Jeomagnetik fırtınalar, Dünya yüzeyinde Jeomagnetik İndüklenmiş
        Akımlar (GIC) oluşturur. Bu akımlar yüksek gerilim trafo
        sargılarını aşırı ısıtarak kalıcı hasara yol açabilir.
        Yükün azaltılması trafoları korur.

    Parametreler:
        skor      : Güncel tehdit skoru
        seviye_tr : Tehdit seviyesi açıklaması (Türkçe)
        hafiza    : AksiyonHafizasi veritabanı nesnesi

    Dönüş:
        dict: Sanal webhook yanıt simülasyonu
    """
    islem_id = str(uuid.uuid4())[:8].upper()

    print()
    print(f"  {R_SARI}{R_PARLAK}┌──────────────────────────────────────────────────────────────┐{R_SIFIRLA}")
    print(f"  {R_SARI}{R_PARLAK}│  ⚡ ENERJİ ŞEBEKESİ ACİL KORUMA PROTOKOLü – DEVREDE         │{R_SIFIRLA}")
    print(f"  {R_SARI}{R_PARLAK}└──────────────────────────────────────────────────────────────┘{R_SIFIRLA}")
    print()
    _log("KRİZ", f"[WEBHOOK] POST → {WEBHOOK_ENERJI}")
    _log("KRİZ", f"[İŞLEM-ID: {islem_id}] Şebeke yük azaltma talebi gönderiliyor...")
    _log("KRİZ", f"  ├─ Tehdit Skoru    : {skor}/10.0 ({seviye_tr})")
    _log("KRİZ", f"  ├─ GIC Risk Bölgesi: Yüksek enlem şebeke hatları (>55° enlem)")
    _log("KRİZ", f"  ├─ Önlem           : Trafo yükü %60'a düşürülsün, yedek devreler aktif edilsin")
    _log("KRİZ", f"  ├─ VAR Kompanzasyon: Reaktif güç kompanzatörleri tam kapasiteye alınsın")
    _log("KRİZ", f"  └─ Simülasyon Yanıt: HTTP 200 OK – Yük azaltma emri alındı ✓")

    detay = (
        f"İşlem-ID: {islem_id} | Tehdit: {skor}/10 ({seviye_tr}) | "
        f"GIC risk bölgesi: >55° enlem şebeke hatları | "
        f"Trafo yükü %60'a düşürüldü, yedek devreler aktif | "
        f"VAR kompanzatörleri tam kapasite | "
        f"Webhook: {WEBHOOK_ENERJI}"
    )
    hafiza.kaydet("ENERJİ_SEBEKESI", detay)

    return {
        "protokol": "ENERJİ_SEBEKESI",
        "islem_id": islem_id,
        "durum": "TETIKLENDI",
        "webhook": WEBHOOK_ENERJI,
        "simulasyon_yanit": "HTTP 200 OK",
    }


def uydu_operator_uyarisi(skor: float, seviye_tr: str, hafiza: AksiyonHafizasi) -> dict:
    """
    Uyduların güvenli moda (safe mode) geçirilmesi için
    uydu operatör merkezlerine acil sinyal gönderir.

    Fiziksel gerekçe:
        Şiddetli güneş parçacık olayları (SEP) uydu elektroniğinde
        Single Event Upsets (SEU) ve latch-up arızalarına neden olur.
        Güneş panelleri bozulabilir, yörünge sürüklenmesi artar.
        Safe mode, kritik olmayan sistemleri kapatarak uyduyu korur.

    Parametreler:
        skor      : Güncel tehdit skoru
        seviye_tr : Tehdit seviyesi açıklaması (Türkçe)
        hafiza    : AksiyonHafizasi veritabanı nesnesi

    Dönüş:
        dict: Sanal webhook yanıt simülasyonu
    """
    islem_id = str(uuid.uuid4())[:8].upper()

    print()
    print(f"  {R_MOR}{R_PARLAK}┌──────────────────────────────────────────────────────────────┐{R_SIFIRLA}")
    print(f"  {R_MOR}{R_PARLAK}│  🛰  UYDU OPERATÖR ACİL UYARI PROTOKOLü – DEVREDE            │{R_SIFIRLA}")
    print(f"  {R_MOR}{R_PARLAK}└──────────────────────────────────────────────────────────────┘{R_SIFIRLA}")
    print()
    _log("KRİZ", f"[WEBHOOK] POST → {WEBHOOK_UYDU}")
    _log("KRİZ", f"[İŞLEM-ID: {islem_id}] Uydu güvenli mod geçiş talebi gönderiliyor...")
    _log("KRİZ", f"  ├─ Tehdit Skoru    : {skor}/10.0 ({seviye_tr})")
    _log("KRİZ", f"  ├─ Etkilenen Yörünge: LEO (Alçak Dünya Yörüngesi) & GEO (Jeostatik Yörünge)")
    _log("KRİZ", f"  ├─ SEP Risk Seviyesi: YÜKSEK – Enerjik parçacık akısı eşik üstünde")
    _log("KRİZ", f"  ├─ Komut            : Kritik olmayan alt sistemler kapatılsın, güneş panelleri")
    _log("KRİZ", f"  │                     minimum açıya getirilsin, yedek bellek aktif edilsin")
    _log("KRİZ", f"  └─ Simülasyon Yanıt : HTTP 200 OK – Safe-mode geçiş emri alındı ✓")

    detay = (
        f"İşlem-ID: {islem_id} | Tehdit: {skor}/10 ({seviye_tr}) | "
        f"LEO & GEO yörünge uyduları safe-mode geçişi | "
        f"Kritik olmayan alt sistemler kapatıldı | "
        f"Güneş panelleri minimum açıya getirildi | "
        f"Webhook: {WEBHOOK_UYDU}"
    )
    hafiza.kaydet("UYDU_OPERATORU", detay)

    return {
        "protokol": "UYDU_OPERATORU",
        "islem_id": islem_id,
        "durum": "TETIKLENDI",
        "webhook": WEBHOOK_UYDU,
        "simulasyon_yanit": "HTTP 200 OK",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DISCORD WEBHOOK – Gerçek Dış Dünya Bildirimi
# ═══════════════════════════════════════════════════════════════════════════════

def discord_kriz_bildir(analiz_raporu: dict):
    """
    Kriz durumunda Discord kanalına şık bir Embed mesajı gönderir.
    Sadece DISCORD_WEBHOOK_URL .env'de tanımlıysa ve tehdit skoru
    kriz eşiğinin üzerindeyse çalışır.

    Embed içeriği:
        - Tehdit Skoru ve Seviyesi
        - Güneş Rüzgarı Hızı
        - Kp İndeksi (varsa)
        - Yapay Zeka Acil Durum Raporu (varsa)

    Try-except ile korunmuştur: internet/Discord çökerse sistem durmaz.
    """
    if not DISCORD_WEBHOOK_URL:
        _log("UYARI", "DISCORD_WEBHOOK_URL tanımlı değil (.env). Discord bildirimi atlanıyor.")
        return

    tehdit = analiz_raporu.get("tehdit_degerlendirmesi", {})
    skor = tehdit.get("tehdit_skoru", 0.0)
    seviye_tr = tehdit.get("tehdit_seviyesi_tr", "N/A")
    seviye = tehdit.get("tehdit_seviyesi", "N/A")
    fiziksel = tehdit.get("fiziksel_aciklama", "")

    # Anlık ölçümler
    anlik = analiz_raporu.get("anlik_olcumler", {})
    hiz = anlik.get("ruzgar_hizi_km_s", "N/A")
    bt = anlik.get("bt_toplam_nT", "N/A")
    bz = anlik.get("bz_yonu_nT", "N/A")

    # Kp İndeksi (master_paket'ten geliyorsa)
    kp_bilgi = "N/A"
    # Rapor içinde kp verisi olabilir
    trend = analiz_raporu.get("trend_analizi", {})
    kp_deger = trend.get("kp_degeri")
    if kp_deger is not None:
        kp_bilgi = str(kp_deger)

    # Yapay Zeka Raporu
    ai_rapor = analiz_raporu.get("yapay_zeka_analizi", None)
    ai_metin = ai_rapor if ai_rapor else "AI raporu mevcut değil."
    # Discord embed field max 1024 karakter
    if len(ai_metin) > 1000:
        ai_metin = ai_metin[:997] + "..."

    # ── Discord Embed Payload ──
    embed = {
        "title": "⚠️ SOLARIS-NETWORK :: KRİZ ALARMI",
        "description": (
            f"**Tehdit Seviyesi:** {seviye_tr} ({seviye})\n"
            f"**Açıklama:** {fiziksel}"
        ),
        "color": 0xFF0000,  # Kırmızı
        "fields": [
            {
                "name": "🔴 Tehdit Skoru",
                "value": f"**{skor}/10.0**",
                "inline": True,
            },
            {
                "name": "🌊 Rüzgar Hızı",
                "value": f"{hiz} km/s",
                "inline": True,
            },
            {
                "name": "🧲 Bt / Bz",
                "value": f"Bt: {bt} nT | Bz: {bz} nT",
                "inline": True,
            },
            {
                "name": "📡 Kp İndeksi",
                "value": f"{kp_bilgi}",
                "inline": True,
            },
            {
                "name": "🤖 Yapay Zeka Raporu",
                "value": ai_metin,
                "inline": False,
            },
        ],
        "footer": {
            "text": f"Solaris-Network Otonom Erken Uyarı Sistemi | {_utc_simdi()}",
        },
    }

    payload = {
        "username": "Solaris-Network",
        "embeds": [embed],
    }

    try:
        _log("KRİZ", "Discord webhook'a kriz embed mesajı gönderiliyor...")
        yanit = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )

        if yanit.status_code in (200, 204):
            _log("KRİZ", f"✓ Discord bildirim başarıyla gönderildi (HTTP {yanit.status_code})")
        else:
            _log("UYARI", f"Discord webhook yanıtı beklenmeyen: HTTP {yanit.status_code} – {yanit.text[:200]}")

    except requests.exceptions.Timeout:
        _log("UYARI", "Discord webhook zaman aşımı (10s). Bildirim gönderilemedi, sistem devam ediyor.")
    except requests.exceptions.ConnectionError:
        _log("UYARI", "Discord webhook bağlantı hatası. Bildirim gönderilemedi, sistem devam ediyor.")
    except Exception as hata:
        _log("HATA", f"Discord webhook beklenmeyen hata: {hata}. Sistem devam ediyor.")


# ═══════════════════════════════════════════════════════════════════════════════
#  KRİZ ORKESTRASYON FONKSİYONU
# ═══════════════════════════════════════════════════════════════════════════════

def kriz_protokollerini_denetle(analiz_raporu: dict) -> dict:
    """
    Zeka Merkezi'nden gelen analiz raporunu değerlendirir ve tehdit skoru
    eşik değerinin üzerindeyse tüm kriz protokollerini sırayla tetikler.

    Bu fonksiyon, Aksiyon Merkezi'nin tek dış arayüzüdür (public API).
    Orkestratör (solaris_baslat.py) bu fonksiyonu çağırır.

    Çalışma mantığı:
        - Tehdit skoru ≥ 7.0 → 3 kriz protokolü tetiklenir + DB'ye loglanır
        - Tehdit skoru < 7.0  → Durum normal logu basılır, aksiyon yok

    Parametreler:
        analiz_raporu: zeka_merkezi.calistir() fonksiyonundan dönen rapor sözlüğü

    Dönüş:
        dict: Kriz denetim özeti
            - kriz_tetiklendi : bool
            - tehdit_skoru    : float
            - tetiklenen_protokoller : list[dict]
    """
    # ── Başlangıç Banneri ──
    print()
    print(f"{R_TURUNCU}{R_PARLAK}")
    print("    ╔════════════════════════════════════════════════════════════════╗")
    print("    ║        🔥 SOLARIS-NETWORK  ::  Aksiyon Merkezi v3.0.0        ║")
    print("    ║           Otonom Kriz Protokol Denetim Birimi                 ║")
    print("    ╚════════════════════════════════════════════════════════════════╝")
    print(f"{R_SIFIRLA}")

    _log("AKSİYON", "Aksiyon Merkezi kriz denetimi başlatılıyor...")

    # ── Tehdit skorunu rapordan çıkar ──
    tehdit = analiz_raporu.get("tehdit_degerlendirmesi", {})
    skor = tehdit.get("tehdit_skoru", 0.0)
    seviye = tehdit.get("tehdit_seviyesi", "UNKNOWN")
    seviye_tr = tehdit.get("tehdit_seviyesi_tr", "BİLİNMİYOR")

    _log("AKSİYON", f"Tehdit Skoru Alındı: {skor}/10.0 – {seviye_tr} ({seviye})")
    _log("AKSİYON", f"Kriz Eşik Değeri  : {KRIZ_ESIK_SKORU}/10.0")

    # ── Skor barı ──
    dolu = "█" * int(round(skor))
    bos = "░" * (10 - int(round(skor)))

    if skor >= 9.0:
        bar_renk = f"{R_KIRMIZI}{R_PARLAK}"
    elif skor >= KRIZ_ESIK_SKORU:
        bar_renk = R_KIRMIZI
    elif skor >= 5.0:
        bar_renk = R_SARI
    else:
        bar_renk = R_YESIL

    print()
    print(f"      Skor : {bar_renk}{dolu}{R_DIM}{bos}{R_SIFIRLA}  {bar_renk}{R_PARLAK}{skor}/10.0{R_SIFIRLA}")
    print()

    sonuc = {
        "kriz_tetiklendi": False,
        "tehdit_skoru": skor,
        "tehdit_seviyesi": seviye,
        "tetiklenen_protokoller": [],
    }

    # ── TEHDİT SKORU DEĞERLENDİRMESİ ──
    if skor >= KRIZ_ESIK_SKORU:
        # ════════════════════ KRİZ MODU AKTİF ════════════════════
        print(f"  {R_KIRMIZI}{R_PARLAK}{'━' * 62}{R_SIFIRLA}")
        print(f"  {R_KIRMIZI}{R_PARLAK}  ⚠  UYARI: KRİZ EŞİĞİ AŞILDI – OTONOM PROTOKOLLER DEVREDE  ⚠{R_SIFIRLA}")
        print(f"  {R_KIRMIZI}{R_PARLAK}{'━' * 62}{R_SIFIRLA}")
        print()

        _log("KRİZ", f"Tehdit skoru {skor} ≥ {KRIZ_ESIK_SKORU} → 3 kriz protokolü tetikleniyor!")

        # Veritabanı bağlantısını aç
        hafiza = AksiyonHafizasi()

        try:
            # ── PROTOKOL 1: Havacılık Uyarısı ──
            _log("KRİZ", "━━━ Protokol 1/3: Havacılık Acil Uyarı ━━━")
            sonuc_havacilik = havacilik_uyarisi_gonder(skor, seviye_tr, hafiza)
            sonuc["tetiklenen_protokoller"].append(sonuc_havacilik)

            # ── PROTOKOL 2: Enerji Şebekesi Uyarısı ──
            _log("KRİZ", "━━━ Protokol 2/3: Enerji Şebekesi Koruma ━━━")
            sonuc_enerji = enerji_sebekesi_uyarisi(skor, seviye_tr, hafiza)
            sonuc["tetiklenen_protokoller"].append(sonuc_enerji)

            # ── PROTOKOL 3: Uydu Operatör Uyarısı ──
            _log("KRİZ", "━━━ Protokol 3/3: Uydu Operatör Güvenlik ━━━")
            sonuc_uydu = uydu_operator_uyarisi(skor, seviye_tr, hafiza)
            sonuc["tetiklenen_protokoller"].append(sonuc_uydu)

        finally:
            hafiza.kapat()

        sonuc["kriz_tetiklendi"] = True

        # ── Kriz Özet Raporu ──
        print()
        print(f"  {R_KIRMIZI}{R_PARLAK}{'═' * 62}{R_SIFIRLA}")
        print(f"  {R_KIRMIZI}{R_PARLAK}  KRİZ PROTOKOL ÖZETİ{R_SIFIRLA}")
        print(f"  {R_KIRMIZI}{R_PARLAK}{'─' * 62}{R_SIFIRLA}")
        print(f"    {R_PARLAK}Tetiklenen Protokol Sayısı : {len(sonuc['tetiklenen_protokoller'])}/3{R_SIFIRLA}")
        for p in sonuc["tetiklenen_protokoller"]:
            durum_icon = "✅" if p["durum"] == "TETIKLENDI" else "❌"
            print(f"    {durum_icon} {p['protokol']:<22} │ İşlem: {p['islem_id']} │ {p['simulasyon_yanit']}")
        print(f"  {R_KIRMIZI}{R_PARLAK}{'═' * 62}{R_SIFIRLA}")
        print()

        _log("KRİZ", "Tüm kriz protokolleri başarıyla tetiklendi ve loglandı. ✓")

        # ── PROTOKOL 4 (Gerçek): Discord Webhook Bildirimi ──
        discord_kriz_bildir(analiz_raporu)

    else:
        # ════════════════════ NORMAL DURUM ════════════════════
        print(f"  {R_YESIL}{R_PARLAK}{'─' * 62}{R_SIFIRLA}")
        print(f"  {R_YESIL}{R_PARLAK}  ✓ DURUM NORMAL – Kriz protokolü tetiklenmedi{R_SIFIRLA}")
        print(f"  {R_YESIL}{R_PARLAK}{'─' * 62}{R_SIFIRLA}")
        print()
        _log("AKSİYON", f"Tehdit skoru {skor} < {KRIZ_ESIK_SKORU} → Kriz eşiği altında.")
        _log("AKSİYON", "Tüm sistemler nominal parametrelerde çalışıyor. Bir sonraki tarama bekleniyor.")

    _log("AKSİYON", "Aksiyon Merkezi denetim döngüsü tamamlandı. ✓")
    return sonuc


# ═══════════════════════════════════════════════════════════════════════════════
#  MODÜL GİRİŞ NOKTASI (Doğrudan test için)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test amaçlı sahte analiz raporu (yüksek tehdit skoru ile)
    test_raporu = {
        "tehdit_degerlendirmesi": {
            "tehdit_skoru": 8.5,
            "tehdit_seviyesi": "SEVERE",
            "tehdit_seviyesi_tr": "CİDDİ TEHLİKE",
        }
    }
    print(f"\n{R_SARI}{R_PARLAK}[TEST MODU] Sahte yüksek tehdit raporu ile kriz testi başlatılıyor...{R_SIFIRLA}\n")
    kriz_protokollerini_denetle(test_raporu)
