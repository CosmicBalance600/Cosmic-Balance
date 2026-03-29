"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   SOLARIS-NETWORK :: Zeka Merkezi                          ║
║         Faz 2 – Otonom Analiz & Tehdit Puanlama Motoru                    ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Sürüm   : 2.0.0                                                          ║
║  Açıklama : Faz 1 Veri Motorundan gelen master_veri_paketini SQLite        ║
║             veritabanına kaydeder, zaman serisi analizi yapar ve            ║
║             NASA-seviyesinde otonom tehdit puanlaması üretir.               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import math
import time
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ── Faz 1 Veri Motoru bağlantısı ──
from veri_merkezi import calistir as veri_motoru_calistir

# ── Ortam değişkenlerini yükle (.env) ──
_SCRIPT_DIZINI_ENV = Path(__file__).resolve().parent
load_dotenv(_SCRIPT_DIZINI_ENV / ".env")

# ── Merkezi Konfigürasyon ──
from config import (
    VERITABANI_YOLU, ANALIZ_PENCERE_BOYUTU, SMA_PENCERE, ESIK,
    WENOX_API_URL, WENOX_MODEL, WENOX_MAKS_DENEME, WENOX_BEKLEME_SURESI,
    RENK_KIRMIZI, RENK_YESIL, RENK_SARI, RENK_MAVI, RENK_MOR,
    RENK_CYAN, RENK_BEYAZ, RENK_PARLAK, RENK_DIM, RENK_SIFIRLA,
)

# Wenox API Key (gizli, .env'den okunur)
WENOX_API_KEY = os.getenv("WENOX_API_KEY", "")

# Yerel renk kısaltmaları (mevcut kodla uyumluluk için)
R_KIRMIZI = RENK_KIRMIZI
R_YESIL   = RENK_YESIL
R_SARI    = RENK_SARI
R_MAVI    = RENK_MAVI
R_MOR     = RENK_MOR
R_CYAN    = RENK_CYAN
R_BEYAZ   = RENK_BEYAZ
R_PARLAK  = RENK_PARLAK
R_DIM     = RENK_DIM
R_SIFIRLA = RENK_SIFIRLA


# ═══════════════════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

def _utc_simdi() -> str:
    """Şu anki UTC zamanını ISO 8601 formatında döndürür."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(seviye: str, mesaj: str):
    """
    Renk kodlu, zaman damgalı terminal log çıktısı üretir.
    Seviyeler: ZEKA, BİLGİ, UYARI, HATA, ANALİZ, VERİTABANI
    """
    renk = {
        "ZEKA":      R_MOR,
        "BİLGİ":     R_YESIL,
        "UYARI":     R_SARI,
        "HATA":      R_KIRMIZI,
        "ANALİZ":    R_CYAN,
        "VERİTABANI": R_MAVI,
    }.get(seviye, R_SIFIRLA)
    print(f"{R_CYAN}[{_utc_simdi()}]{R_SIFIRLA} {renk}{R_PARLAK}[{seviye}]{R_SIFIRLA} {mesaj}")


# ═══════════════════════════════════════════════════════════════════════════════
#  VERİTABANI KATMANI – SQLite Kalıcı Hafıza
# ═══════════════════════════════════════════════════════════════════════════════

class SolarisHafiza:
    """
    Solaris-Network'ün kalıcı hafıza birimi.
    SQLite veritabanı üzerinden telemetri verilerini depolar ve sorgular.

    Thread-safe tasarım: Kalıcı bağlantı tutmaz. Her işlemde
    `with sqlite3.connect() as conn:` ile anlık bağlantı açar,
    işlemi tamamlar ve otomatik kapatır. Bu sayede Flask web sunucusu
    ve Daemon orkestratörü eş zamanlı çalışabilir.
    """

    def __init__(self, veritabani_yolu: str = None):
        """
        Veritabanı yolunu kaydeder ve gerekli tabloları oluşturur.

        Parametreler:
            veritabani_yolu: SQLite dosya yolu (varsayılan: solaris_hafiza.db)
        """
        self.yol = str(veritabani_yolu or VERITABANI_YOLU)
        self._tablo_olustur()

    def _yeni_baglanti(self) -> sqlite3.Connection:
        """
        Yeni bir SQLite bağlantısı oluşturur ve WAL modunu aktif eder.
        Her çağrıda bağımsız bir bağlantı döner (thread-safe).
        Bu bağlantı `with` bloğu içinde kullanılmalıdır.
        """
        conn = sqlite3.connect(self.yol, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _tablo_olustur(self):
        """
        'telemetri' ve 'analiz_sonuclari' tablolarını oluşturur (yoksa).
        telemetri: Güneş rüzgarı, manyetik alan, Kp, X-Ray ve Proton ölçümlerini depolar.
        analiz_sonuclari: Tehdit skoru ve AI analiz raporlarını depolar.

        Mevcut veritabanları için ALTER TABLE ile kp_indeksi, xray_sinifi ve
        proton_akisi sütunları otomatik olarak eklenir (geriye uyumlu migrasyon).
        """
        with self._yeni_baglanti() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetri (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    zaman            TEXT    NOT NULL,
                    ruzgar_hizi      REAL,
                    plazma_yogunlugu REAL,
                    bt_gucu          REAL,
                    bz_yonu          REAL,
                    kp_indeksi       REAL,
                    xray_sinifi      TEXT,
                    proton_akisi     REAL
                )
            """)

            # ── Geriye Uyumlu Migrasyon ──
            for sutun_adi, sutun_tipi in [
                ("kp_indeksi", "REAL"),
                ("xray_sinifi", "TEXT"),
                ("proton_akisi", "REAL"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE telemetri ADD COLUMN {sutun_adi} {sutun_tipi}")
                    _log("VERİTABANI", f"Migrasyon: telemetri tablosuna '{sutun_adi}' sütunu eklendi.")
                except sqlite3.OperationalError:
                    pass

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetri_zaman ON telemetri(zaman)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analiz_sonuclari (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    zaman            TEXT    NOT NULL,
                    tehdit_skoru     REAL,
                    tehdit_seviyesi  TEXT,
                    tehdit_seviyesi_tr TEXT,
                    fiziksel_aciklama TEXT,
                    renk_kodu        TEXT,
                    ai_analiz        TEXT,
                    rapor_json       TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analiz_zaman ON analiz_sonuclari(zaman)
            """)
            conn.commit()
        _log("VERİTABANI", f"Hafıza birimi hazır: {self.yol}")

    def kaydet(self, master_paket: dict) -> bool:
        """
        Faz 1'den gelen master_veri_paketini veritabanına güvenli şekilde kaydeder.
        Plazma, manyetik alan, Kp İndeksi, X-Ray ve Proton Flux verilerinin
        tamamını tek bir telemetri kaydında birleştirir.
        """
        try:
            gunes = master_paket.get("gunes_ruzgari", {})
            plazma = gunes.get("plazma", {})
            manyetik = gunes.get("manyetik_alan", {})

            kp_verisi = master_paket.get("jeomanyetik_durum", {})
            kp_degeri = kp_verisi.get("kp_degeri")

            xray_verisi = master_paket.get("gunes_patlamasi", {})
            xray_sinifi = xray_verisi.get("flare_sinifi")
            if xray_sinifi == "N/A":
                xray_sinifi = None

            radyasyon = master_paket.get("radyasyon_durumu", {})
            proton_akisi = radyasyon.get("proton_flux_pfu")

            zaman = plazma.get("zaman_damgasi") or _utc_simdi()

            with self._yeni_baglanti() as conn:
                conn.execute(
                    """INSERT INTO telemetri
                       (zaman, ruzgar_hizi, plazma_yogunlugu, bt_gucu, bz_yonu,
                        kp_indeksi, xray_sinifi, proton_akisi)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        zaman,
                        plazma.get("hiz_km_s"),
                        plazma.get("yogunluk_p_cc"),
                        manyetik.get("bt_nT"),
                        manyetik.get("bz_gsm_nT"),
                        kp_degeri,
                        xray_sinifi,
                        proton_akisi,
                    )
                )
                conn.commit()

            _log("VERİTABANI", f"Telemetri kaydı başarıyla yazıldı – "
                               f"Kp: {kp_degeri}, X-Ray: {xray_sinifi}, "
                               f"Proton: {proton_akisi} pfu (zaman: {zaman})")
            return True

        except Exception as hata:
            _log("HATA", f"Veritabanı yazma hatası: {hata}")
            return False

    def son_kayitlari_getir(self, adet: int = ANALIZ_PENCERE_BOYUTU) -> list[dict]:
        """
        Veritabanından son N adet telemetri kaydını zaman sırasına göre getirir.
        Bu kayıtlar zaman serisi analizi için kullanılır.
        """
        try:
            with self._yeni_baglanti() as conn:
                cursor = conn.execute(
                    """SELECT zaman, ruzgar_hizi, plazma_yogunlugu, bt_gucu, bz_yonu, proton_akisi
                       FROM telemetri
                       ORDER BY id DESC
                       LIMIT ?""",
                    (adet,)
                )
                satirlar = [dict(satir) for satir in cursor.fetchall()]
                satirlar.reverse()

            _log("VERİTABANI", f"Analiz için {len(satirlar)} kayıt hafızadan yüklendi.")
            return satirlar

        except Exception as hata:
            _log("HATA", f"Veritabanı okuma hatası: {hata}")
            return []

    def toplam_kayit_sayisi(self) -> int:
        """Veritabanındaki toplam telemetri kaydı sayısını döndürür."""
        try:
            with self._yeni_baglanti() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM telemetri")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def analiz_kaydet(self, rapor: dict) -> bool:
        """
        Analiz raporunu analiz_sonuclari tablosuna kaydeder.
        Dashboard API bu tablodan veri çeker.
        """
        try:
            tehdit = rapor.get("tehdit_degerlendirmesi", {})
            with self._yeni_baglanti() as conn:
                conn.execute(
                    """INSERT INTO analiz_sonuclari
                       (zaman, tehdit_skoru, tehdit_seviyesi, tehdit_seviyesi_tr,
                        fiziksel_aciklama, renk_kodu, ai_analiz, rapor_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        _utc_simdi(),
                        tehdit.get("tehdit_skoru"),
                        tehdit.get("tehdit_seviyesi"),
                        tehdit.get("tehdit_seviyesi_tr"),
                        tehdit.get("fiziksel_aciklama"),
                        tehdit.get("renk_kodu"),
                        rapor.get("yapay_zeka_analizi"),
                        json.dumps(rapor, ensure_ascii=False),
                    )
                )
                conn.commit()
            _log("VERİTABANI", "Analiz raporu veritabanına kaydedildi.")
            return True
        except Exception as hata:
            _log("HATA", f"Analiz raporu kayıt hatası: {hata}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
#  MATEMATİKSEL ANALİZ MOTORU – Zaman Serisi & Trend Hesaplama
# ═══════════════════════════════════════════════════════════════════════════════

class AnalizMotoru:
    """
    NASA SWPC standartlarında zaman serisi analiz motoru.
    SMA (Basit Hareketli Ortalama), ivmelenme hesaplama ve
    ağırlıklı ortalama algoritmaları ile güneş rüzgarı trendlerini belirler.
    """

    @staticmethod
    def _gecerli_degerler(kayitlar: list[dict], alan: str) -> list[float]:
        """
        Kayıt listesinden belirtilen alanın None olmayan değerlerini çıkarır.

        Parametreler:
            kayitlar : Telemetri kayıt listesi
            alan     : Değeri çekilecek sözlük anahtarı

        Dönüş:
            list[float]: Geçerli (None olmayan) değerler listesi
        """
        return [k[alan] for k in kayitlar if k.get(alan) is not None]

    @staticmethod
    def sma_hesapla(degerler: list[float], pencere: int = SMA_PENCERE) -> float | None:
        """
        Basit Hareketli Ortalama (Simple Moving Average) hesaplar.

        SMA, son N değerin aritmetik ortalamasıdır ve kısa vadeli
        dalgalanmaları düzleyerek ana trendi ortaya çıkarır.

        Formül: SMA = (x₁ + x₂ + ... + xₙ) / n

        Parametreler:
            degerler : Sayısal değerler listesi
            pencere  : Ortalama pencere boyutu (varsayılan: 10)

        Dönüş:
            float: SMA değeri veya yetersiz veri için None
        """
        if not degerler or len(degerler) < 2:
            return None

        # Pencere boyutunu mevcut veri miktarına göre ayarla
        efektif_pencere = min(pencere, len(degerler))
        son_pencere = degerler[-efektif_pencere:]

        return round(sum(son_pencere) / len(son_pencere), 2)

    @staticmethod
    def ivmelenme_hesapla(degerler: list[float]) -> dict | None:
        """
        Güneş rüzgarı hızının İvmelenmesini (Rate of Change) hesaplar.

        İvmelenme, hız değişim oranını (Δv / Δt) temsil eder:
          - Pozitif ivme = Hız artıyor → Fırtına yaklaşıyor olabilir
          - Negatif ivme = Hız azalıyor → Fırtına yavaşlıyor
          - Sıfıra yakın = Stabil durum

        Hesaplama:
          - Anlık ivme: Son iki değer arasındaki fark
          - Ortalama ivme: Tüm ardışık farkların ortalaması
          - Trend yönü: Genel hareket yönü

        Dönüş:
            dict: İvme metrikleri veya yetersiz veri için None
        """
        if not degerler or len(degerler) < 3:
            return None

        # Ardışık farkları hesapla (birinci türev)
        farklar = [degerler[i] - degerler[i - 1] for i in range(1, len(degerler))]

        # Anlık ivme (son iki ölçüm arasındaki fark)
        anlik_ivme = round(farklar[-1], 2)

        # Son 5 değerin ortalama ivmesi
        son_farklar = farklar[-min(5, len(farklar)):]
        ortalama_ivme = round(sum(son_farklar) / len(son_farklar), 2)

        # Trend yönünü belirle (pozitif farklar / toplam fark oranı)
        pozitif_sayisi = sum(1 for f in son_farklar if f > 0)
        negatif_sayisi = sum(1 for f in son_farklar if f < 0)

        if pozitif_sayisi > negatif_sayisi:
            trend_yonu = "YUKARI ▲"
            trend_kodu = "YUKSELIYOR"
        elif negatif_sayisi > pozitif_sayisi:
            trend_yonu = "ASAGI ▼"
            trend_kodu = "DUSUYOR"
        else:
            trend_yonu = "YATAY ◆"
            trend_kodu = "STABIL"

        # Maksimum sıçramayı bul (volatilite göstergesi)
        maks_sicrama = round(max(abs(f) for f in farklar), 2) if farklar else 0.0

        return {
            "anlik_ivme_km_s": anlik_ivme,
            "ortalama_ivme_km_s": ortalama_ivme,
            "trend_yonu": trend_yonu,
            "trend_kodu": trend_kodu,
            "maks_sicrama_km_s": maks_sicrama,
            "olcum_sayisi": len(degerler),
        }

    @staticmethod
    def agirlikli_ortalama_bz(degerler: list[float]) -> dict | None:
        """
        Bz (Manyetik Yön) değerinin Üstel Ağırlıklı Ortalamasını hesaplar.

        Bz Fiziksel Anlamı:
          - Bz < 0 (güneye dönük): Dünya'nın manyetosferi ile anti-paralel,
            manyetik yeniden bağlanma (reconnection) gerçekleşir → Kalkan delinir!
          - Bz > 0 (kuzeye dönük): Paralel yönde, kalkan güçlenir → Güvenli.

        Ağırlıklandırma (Exponential Weighting):
          Daha yeni ölçümler daha fazla ağırlık taşır (w = e^(i/N)).
          Bu, hızla değişen koşullarda daha hassas bir gösterge sağlar.

        Dönüş:
            dict: Bz analiz sonuçları veya yetersiz veri için None
        """
        if not degerler or len(degerler) < 2:
            return None

        n = len(degerler)

        # Üstel ağırlıklar: yeni veriler daha fazla ağırlık taşır
        agirliklar = [math.exp(i / n) for i in range(n)]
        toplam_agirlik = sum(agirliklar)

        # Ağırlıklı ortalama
        agirlikli_toplam = sum(d * w for d, w in zip(degerler, agirliklar))
        agirlikli_ort = round(agirlikli_toplam / toplam_agirlik, 3)

        # Son değerin durumu
        son_bz = degerler[-1]

        # Güneye dönüklük süresi (streak) – ardışık negatif değerleri say
        guneye_donuk_sure = 0
        for v in reversed(degerler):
            if v < 0:
                guneye_donuk_sure += 1
            else:
                break

        # Bz durum yorumu
        if agirlikli_ort < ESIK["bz_kritik"]:
            durum = "KRİTİK_GÜNEYWARD"
            yorum = "Manyetosfer ciddi şekilde tehdit altında! Kalkan delinme riski çok yüksek."
        elif agirlikli_ort < ESIK["bz_tehlike"]:
            durum = "TEHLİKELİ_GÜNEYWARD"
            yorum = "Manyetik yeniden bağlanma aktif. Jeomagnetik aktivite artıyor."
        elif agirlikli_ort < 0:
            durum = "HAFİF_GÜNEYWARD"
            yorum = "Bz hafif güneyde. Düşük seviyeli manyetik sızıntı mümkün."
        else:
            durum = "KUZEYWARD_GÜVENLİ"
            yorum = "Bz kuzeye dönük, manyetosfer kalkanı güçlü. Tehdit düşük."

        return {
            "agirlikli_ortalama_nT": agirlikli_ort,
            "son_deger_nT": round(son_bz, 2),
            "durum": durum,
            "fiziksel_yorum": yorum,
            "guneye_donuk_ardisik_olcum": guneye_donuk_sure,
            "toplam_olcum": n,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  OTONOM TEHDİT PUANLAMA ALGORİTMASI
# ═══════════════════════════════════════════════════════════════════════════════

class TehditDegerlendirici:
    """
    Çok faktörlü, dinamik tehdit puanlama sistemi.
    NASA SWPC G-Scale (G1-G5) ve Kp indeksi referanslarından
    esinlenerek oluşturulmuş otonom karar algoritması.

    Puanlama bileşenleri:
      1. Hız Bileşeni      (0-3 puan)   : Güneş rüzgarı hızı etkisi
      2. Bz Bileşeni       (0-3 puan)   : Manyetik yön etkisi
      3. Bt Bileşeni       (0-1.5 puan) : Toplam manyetik alan gücü
      4. Yoğunluk Bileşeni (0-1 puan)   : Plazma yoğunluğu etkisi
      5. Radyasyon Bileşeni (0-2 puan)   : Proton akısı (≥10 MeV) etkisi
      6. İvme Çarpanı       (×1.0-×2.0) : Hızlanma durumunda eksponansiyel artış
      7. Bz-İvme Sinerjisi  (×1.0-×1.5) : Hız artışı + güneye Bz = tehlike katlanır
    """

    @staticmethod
    def puanla(
        anlik_hiz: float | None,
        anlik_bz: float | None,
        anlik_bt: float | None,
        anlik_yogunluk: float | None,
        sma_hiz: float | None,
        ivme_verisi: dict | None,
        bz_analiz: dict | None,
        anlik_proton: float | None = None,
    ) -> dict:
        """
        Tüm metrikleri değerlendirerek 1-10 arası tehdit skoru üretir.

        Dönüş:
            dict: Detaylı tehdit değerlendirme raporu
        """
        bilesenler = {}
        toplam_puan = 0.0

        # ── 1. HIZ BİLEŞENİ (0-3 puan) ──
        hiz = anlik_hiz or (sma_hiz or 0.0)
        if hiz >= ESIK["hiz_siddetli"]:
            hiz_puani = 3.0
        elif hiz >= ESIK["hiz_firtina"]:
            hiz_puani = 2.0 + ((hiz - ESIK["hiz_firtina"]) / (ESIK["hiz_siddetli"] - ESIK["hiz_firtina"]))
        elif hiz >= ESIK["hiz_yukseldi"]:
            hiz_puani = 1.0 + ((hiz - ESIK["hiz_yukseldi"]) / (ESIK["hiz_firtina"] - ESIK["hiz_yukseldi"]))
        elif hiz >= ESIK["hiz_sakin"]:
            hiz_puani = (hiz - ESIK["hiz_sakin"]) / (ESIK["hiz_yukseldi"] - ESIK["hiz_sakin"])
        else:
            hiz_puani = 0.0
        bilesenler["hiz_puani"] = round(hiz_puani, 2)
        toplam_puan += hiz_puani

        # ── 2. Bz BİLEŞENİ (0-3 puan) ──
        bz = anlik_bz if anlik_bz is not None else 0.0
        bz_ort = bz_analiz.get("agirlikli_ortalama_nT", 0.0) if bz_analiz else 0.0
        efektif_bz = min(bz, bz_ort)  # En kötü senaryoyu al

        if efektif_bz <= ESIK["bz_kritik"]:
            bz_puani = 3.0
        elif efektif_bz <= ESIK["bz_tehlike"]:
            bz_puani = 1.5 + 1.5 * ((ESIK["bz_tehlike"] - efektif_bz) / (ESIK["bz_tehlike"] - ESIK["bz_kritik"]))
        elif efektif_bz < 0:
            bz_puani = 1.5 * (abs(efektif_bz) / abs(ESIK["bz_tehlike"]))
        else:
            bz_puani = 0.0
        bilesenler["bz_puani"] = round(bz_puani, 2)
        toplam_puan += bz_puani

        # ── 3. Bt BİLEŞENİ (0-1.5 puan) ──
        bt = anlik_bt if anlik_bt is not None else 0.0
        if bt >= ESIK["bt_firtina"]:
            bt_puani = 1.5
        elif bt >= ESIK["bt_yuksek"]:
            bt_puani = 0.5 + ((bt - ESIK["bt_yuksek"]) / (ESIK["bt_firtina"] - ESIK["bt_yuksek"]))
        else:
            bt_puani = 0.5 * (bt / ESIK["bt_yuksek"]) if ESIK["bt_yuksek"] > 0 else 0.0
        bilesenler["bt_puani"] = round(bt_puani, 2)
        toplam_puan += bt_puani

        # ── 4. YOĞUNLUK BİLEŞENİ (0-1 puan) ──
        yog = anlik_yogunluk if anlik_yogunluk is not None else 0.0
        if yog >= ESIK["yogunluk_kritik"]:
            yog_puani = 1.0
        elif yog >= ESIK["yogunluk_yuksek"]:
            yog_puani = 0.5 + 0.5 * ((yog - ESIK["yogunluk_yuksek"]) / (ESIK["yogunluk_kritik"] - ESIK["yogunluk_yuksek"]))
        else:
            yog_puani = 0.5 * (yog / ESIK["yogunluk_yuksek"]) if ESIK["yogunluk_yuksek"] > 0 else 0.0
        bilesenler["yogunluk_puani"] = round(yog_puani, 2)
        toplam_puan += yog_puani

        # ── 5. RADYASYON BİLEŞENİ (0-2 puan) ──
        # Yüksek proton akısı (≥10 MeV) radyasyon fırtınası göstergesi
        proton = anlik_proton if anlik_proton is not None else 0.0
        if proton >= ESIK["proton_siddetli"]:
            radyasyon_puani = 2.0
        elif proton >= ESIK["proton_kritik"]:
            radyasyon_puani = 1.5 + 0.5 * ((proton - ESIK["proton_kritik"]) / (ESIK["proton_siddetli"] - ESIK["proton_kritik"]))
        elif proton >= ESIK["proton_yuksek"]:
            radyasyon_puani = 0.5 + 1.0 * ((proton - ESIK["proton_yuksek"]) / (ESIK["proton_kritik"] - ESIK["proton_yuksek"]))
        else:
            radyasyon_puani = 0.5 * (proton / ESIK["proton_yuksek"]) if ESIK["proton_yuksek"] > 0 else 0.0
        bilesenler["radyasyon_puani"] = round(radyasyon_puani, 2)
        toplam_puan += radyasyon_puani

        # ── 6. İVME ÇARPANI (×1.0 – ×2.0) ──
        # Eğer hız ivmelenerek artıyorsa tehdit puanını eksponansiyel olarak yükselt
        ivme_carpani = 1.0
        if ivme_verisi and ivme_verisi.get("trend_kodu") == "YUKSELIYOR":
            ort_ivme = abs(ivme_verisi.get("ortalama_ivme_km_s", 0))
            if ort_ivme > ESIK["ivme_uyari"]:
                # Eksponansiyel çarpan: 1.0 → 2.0 arasında hareket eder
                ivme_carpani = min(2.0, 1.0 + (ort_ivme / (ESIK["ivme_uyari"] * 4)))
        bilesenler["ivme_carpani"] = round(ivme_carpani, 2)

        # ── 7. Bz-İVME SİNERJİSİ (×1.0 – ×1.5) ──
        # Hız artıyor VE Bz güneye dönükse → sinerjik tehdit katlanması
        sinerji_carpani = 1.0
        bz_guneyde = efektif_bz < ESIK["bz_tehlike"]
        hiz_artiyor = ivme_verisi and ivme_verisi.get("trend_kodu") == "YUKSELIYOR"

        if bz_guneyde and hiz_artiyor:
            # Sinerjik çarpan: güneye dönüklük derinliğine göre 1.0 → 1.5
            bz_derinlik = abs(efektif_bz) / abs(ESIK["bz_kritik"])
            sinerji_carpani = min(1.5, 1.0 + (bz_derinlik * 0.5))
        bilesenler["sinerji_carpani"] = round(sinerji_carpani, 2)

        # ── TOPLAM SKOR HESAPLAMA ──
        ham_skor = toplam_puan * ivme_carpani * sinerji_carpani

        # 1-10 arasında normalize et (maks ham skor: 10.5 × 2.0 × 1.5 = 31.5 → 10)
        maks_teorik = 10.5 * 2.0 * 1.5
        normalize_skor = min(10.0, max(1.0, 1.0 + 9.0 * (ham_skor / maks_teorik)))
        final_skor = round(normalize_skor, 1)

        # ── TEHDİT SEVİYESİ SINIFLANDIRMASI ──
        if final_skor >= 9.0:
            seviye = "EXTREME"
            seviye_tr = "AŞIRI TEHLİKE"
            aciklama = "G5-Seviye şiddetli jeomagnetik fırtına riski! Uydu ve iletişim sistemleri çökebilir."
            renk_kodu = "KIRMIZI_YANIP_SONEN"
        elif final_skor >= 7.0:
            seviye = "SEVERE"
            seviye_tr = "CİDDİ TEHLİKE"
            aciklama = "G3/G4-Seviye fırtına olasılığı. GPS sapmaları, radyo kesintileri beklenir."
            renk_kodu = "KIRMIZI"
        elif final_skor >= 5.0:
            seviye = "MODERATE"
            seviye_tr = "ORTA SEVİYE"
            aciklama = "G1/G2-Seviye fırtına mümkün. Kutup bölgelerinde aurora aktivitesi artabilir."
            renk_kodu = "TURUNCU"
        elif final_skor >= 3.0:
            seviye = "MINOR"
            seviye_tr = "DÜŞÜK RİSK"
            aciklama = "Hafif uzay havası aktivitesi. Yüksek enlemlerde zayıf aurora olası."
            renk_kodu = "SARI"
        else:
            seviye = "QUIET"
            seviye_tr = "SAKİN"
            aciklama = "Sakin güneş rüzgarı koşulları. Jeomagnetik aktivite minimal."
            renk_kodu = "YESIL"

        return {
            "tehdit_skoru": final_skor,
            "tehdit_seviyesi": seviye,
            "tehdit_seviyesi_tr": seviye_tr,
            "fiziksel_aciklama": aciklama,
            "renk_kodu": renk_kodu,
            "bilesenler": bilesenler,
            "ham_skor": round(ham_skor, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  FIRTINA TAHMİN MOTORU – Ağırlıklı Olasılık Algoritması
# ═══════════════════════════════════════════════════════════════════════════════

def firtina_ihtimali_hesapla(master_paket: dict, hafiza: 'SolarisHafiza') -> dict:
    """
    Hafızadaki son 10 ölçüme ve anlık Kp/X-Ray verilerine bakarak
    ağırlıklı bir fırtına olasılık tahmini üretir.

    Algoritma Bileşenleri (her biri 0-25 puan, toplam 0-100):
      1. Rüzgar İvmesi    : Hız artış trendi (pozitif ivme = tehlike)
      2. Bz Kararlılığı   : İstikrarlı güneye dönük Bz (kalkan zayıflığı)
      3. Kp İndeksi       : Jeomagnetik fırtına aktivitesi
      4. X-Ray Sınıfı     : Güneş patlaması şiddeti (M/X = roketleme)

    Ek Bonus:
      - X-Ray M veya X sınıfı ise +20 puan eklenir ("roketleme" etkisi)

    Parametreler:
        master_paket : Faz 1 veri motorundan dönen master veri paketi
        hafiza       : SolarisHafiza veritabanı bağlantısı

    Dönüş:
        dict: Fırtına tahmin raporu
            - olasilik_yuzdesi : 0-100 arası olasılık
            - zaman_ufku       : Tahmini etki zamanı
            - risk_seviyesi    : DÜŞÜK / ORTA / YÜKSEK / KRİTİK
            - faktorler        : Her bileşenin detaylı puanları
    """
    try:
        _log("ANALİZ", "Fırtına tahmin motoru başlatılıyor (son 10 ölçüm)...")

        # ── Son 10 ölçümü hafızadan çek ──
        son_kayitlar = hafiza.son_kayitlari_getir(10)

        # Kp ve X-Ray verilerini master paketten al
        kp_verisi = master_paket.get("jeomanyetik_durum", {})
        xray_verisi = master_paket.get("gunes_patlamasi", {})

        faktorler = {}
        toplam_puan = 0.0

        # ── FAKTÖR 1: Rüzgar İvmesi (0-25 puan) ──
        hiz_degerleri = [k["ruzgar_hizi"] for k in son_kayitlar if k.get("ruzgar_hizi") is not None]
        ivme_puani = 0.0

        if len(hiz_degerleri) >= 3:
            # Son 5 ardışık farkın ortalamasını hesapla
            farklar = [hiz_degerleri[i] - hiz_degerleri[i - 1] for i in range(1, len(hiz_degerleri))]
            son_farklar = farklar[-min(5, len(farklar)):]
            ortalama_ivme = sum(son_farklar) / len(son_farklar)

            if ortalama_ivme > 0:
                # Pozitif ivme → puan artır (maks 25)
                ivme_puani = min(25.0, (ortalama_ivme / ESIK["ivme_uyari"]) * 25.0)
            faktorler["ruzgar_ivmesi"] = {
                "puan": round(ivme_puani, 1),
                "ortalama_ivme_km_s": round(ortalama_ivme, 2),
                "yorum": "Pozitif – Hız artıyor" if ortalama_ivme > 0 else "Negatif/Stabil",
            }
        else:
            faktorler["ruzgar_ivmesi"] = {"puan": 0, "yorum": "Yetersiz veri"}

        toplam_puan += ivme_puani

        # ── FAKTÖR 2: Bz İstikrarlı Negatif (0-25 puan) ──
        bz_degerleri = [k["bz_yonu"] for k in son_kayitlar if k.get("bz_yonu") is not None]
        bz_puani = 0.0

        if len(bz_degerleri) >= 2:
            # Ardışık negatif sayısını hesapla (streak)
            guneye_streak = 0
            for v in reversed(bz_degerleri):
                if v < 0:
                    guneye_streak += 1
                else:
                    break

            # Ağırlıklı ortalama (üstel)
            n = len(bz_degerleri)
            agirliklar = [math.exp(i / n) for i in range(n)]
            bz_ort = sum(d * w for d, w in zip(bz_degerleri, agirliklar)) / sum(agirliklar)

            # Puanlama: istikrarlı negatif → yüksek puan
            if bz_ort < ESIK["bz_kritik"] and guneye_streak >= 5:
                bz_puani = 25.0
            elif bz_ort < ESIK["bz_tehlike"] and guneye_streak >= 3:
                bz_puani = 18.0
            elif bz_ort < 0 and guneye_streak >= 2:
                bz_puani = 10.0 * (abs(bz_ort) / abs(ESIK["bz_tehlike"]))
            elif bz_ort < 0:
                bz_puani = 5.0

            bz_puani = min(25.0, bz_puani)
            faktorler["bz_kararliligi"] = {
                "puan": round(bz_puani, 1),
                "agirlikli_ortalama_nT": round(bz_ort, 2),
                "guneye_streak": guneye_streak,
                "yorum": "Kritik güneyward" if bz_puani >= 20 else (
                    "Tehlikeli güneyward" if bz_puani >= 15 else (
                        "Hafif güneyward" if bz_puani > 0 else "Kuzeyward – Güvenli"
                    )
                ),
            }
        else:
            faktorler["bz_kararliligi"] = {"puan": 0, "yorum": "Yetersiz veri"}

        toplam_puan += bz_puani

        # ── FAKTÖR 3: Kp İndeksi (0-25 puan) ──
        kp_puani = 0.0
        kp_degeri = kp_verisi.get("kp_degeri")

        if kp_degeri is not None:
            if kp_degeri >= 8:
                kp_puani = 25.0
            elif kp_degeri >= 7:
                kp_puani = 20.0
            elif kp_degeri >= 6:
                kp_puani = 15.0
            elif kp_degeri >= 5:
                kp_puani = 10.0
            elif kp_degeri >= 4:
                kp_puani = 5.0
            else:
                kp_puani = max(0.0, kp_degeri * 1.0)

            faktorler["kp_indeksi"] = {
                "puan": round(kp_puani, 1),
                "kp_degeri": kp_degeri,
                "firtina_sinifi": kp_verisi.get("firtina_sinifi", "N/A"),
            }
        else:
            faktorler["kp_indeksi"] = {"puan": 0, "yorum": "Veri alınamadı"}

        toplam_puan += kp_puani

        # ── FAKTÖR 4: X-Ray Sınıfı (0-25 puan + roketleme bonusu) ──
        xray_puani = 0.0
        flare_sinifi = xray_verisi.get("flare_sinifi", "N/A")
        roketleme = False

        if flare_sinifi == "X-Class":
            xray_puani = 25.0
            roketleme = True
        elif flare_sinifi == "M-Class":
            xray_puani = 20.0
            roketleme = True
        elif flare_sinifi == "C-Class":
            xray_puani = 10.0
        elif flare_sinifi == "B-Class":
            xray_puani = 3.0
        else:
            xray_puani = 0.0

        faktorler["xray_flare"] = {
            "puan": round(xray_puani, 1),
            "flare_sinifi": flare_sinifi,
            "roketleme_aktif": roketleme,
        }

        toplam_puan += xray_puani

        # ── ROKETLEME BONUSU: M/X sınıfı ise +20 puan ──
        bonus = 0.0
        if roketleme:
            bonus = 20.0
            _log("ANALİZ", f"🚀 ROKETLEME AKTİF! X-Ray {flare_sinifi} tespit – +{bonus}% bonus eklendi.")

        toplam_puan += bonus

        # ── Sonuç: 0-100 arası normalize et ──
        # Maks teorik: 25*4 + 20 = 120 → 100'e normalize
        olasilik = min(100, max(0, round(toplam_puan * (100.0 / 120.0))))

        # ── Zaman Ufku ve Risk Seviyesi ──
        if olasilik >= 80:
            zaman_ufku = "6-12 Saat"
            risk_seviyesi = "KRİTİK"
        elif olasilik >= 60:
            zaman_ufku = "12-24 Saat"
            risk_seviyesi = "YÜKSEK"
        elif olasilik >= 40:
            zaman_ufku = "24-48 Saat"
            risk_seviyesi = "ORTA"
        elif olasilik >= 20:
            zaman_ufku = "48-72 Saat"
            risk_seviyesi = "DÜŞÜK"
        else:
            zaman_ufku = "72+ Saat"
            risk_seviyesi = "MİNİMAL"

        tahmin = {
            "olasilik_yuzdesi": olasilik,
            "zaman_ufku": zaman_ufku,
            "risk_seviyesi": risk_seviyesi,
            "faktorler": faktorler,
            "roketleme_bonusu": bonus,
            "ham_puan": round(toplam_puan, 1),
            "analiz_veri_sayisi": len(son_kayitlar),
        }

        _log("ANALİZ", f"Fırtına Tahmini: %{olasilik} olasılık – {risk_seviyesi} ({zaman_ufku})")
        return tahmin

    except Exception as hata:
        _log("HATA", f"Fırtına tahmin motoru hatası: {hata}")
        return {
            "olasilik_yuzdesi": None,
            "zaman_ufku": "N/A",
            "risk_seviyesi": "BİLİNMİYOR",
            "faktorler": {},
            "hata": str(hata),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  YAPAY ZEKA RAPORU – Wenox API (Claude Sonnet) Entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════

def yapay_zeka_raporu_al(veri: dict, skor: float) -> str | None:
    """
    Wenox API (Claude Sonnet) üzerinden yapay zeka destekli
    acil durum analiz raporu üretir.

    Mevcut telemetri verileri ve hesaplanan matematiksel tehdit
    skoru, Claude modeline gönderilerek profesyonel bir durum
    tespiti (2-3 cümle) alınır.

    Parametreler:
        veri : Anlık ölçümler ve trend analizi içeren veri sözlüğü
        skor : TehditDegerlendirici tarafından hesaplanan tehdit skoru

    Dönüş:
        str  : Yapay zeka tarafından üretilen analiz metni
        None : API hatası durumunda None döner (sistem durmaz)
    """
    if not WENOX_API_KEY:
        _log("UYARI", "WENOX_API_KEY bulunamadı! .env dosyasını kontrol edin. AI raporu atlanıyor.")
        return None

    _log("ZEKA", f"Wenox AI (Claude Sonnet) analiz raporu isteniyor... "
                 f"[API Key: {WENOX_API_KEY[:8]}{'*' * (len(WENOX_API_KEY) - 8)}]")

    # ── Prompt için veri özetini hazırla ──
    anlik = veri.get("anlik_olcumler", {})
    trend = veri.get("trend_analizi", {})
    tehdit_bilgi = veri.get("tehdit_degerlendirmesi", {})

    kullanici_mesaji = (
        f"Güncel Uzay Havası Telemetri Verileri:\n"
        f"- Güneş Rüzgarı Hızı: {anlik.get('ruzgar_hizi_km_s', 'N/A')} km/s\n"
        f"- Plazma Yoğunluğu: {anlik.get('plazma_yogunlugu_p_cc', 'N/A')} p/cm³\n"
        f"- Bt (Toplam Manyetik Alan): {anlik.get('bt_toplam_nT', 'N/A')} nT\n"
        f"- Bz (Manyetik Yön): {anlik.get('bz_yonu_nT', 'N/A')} nT\n"
        f"- Hız SMA Trendi: {trend.get('hiz_sma', 'N/A')} km/s\n"
        f"- Hesaplanan Tehdit Skoru: {skor}/10.0\n"
        f"- Tehdit Seviyesi: {tehdit_bilgi.get('tehdit_seviyesi_tr', 'N/A')} ({tehdit_bilgi.get('tehdit_seviyesi', 'N/A')})\n"
        f"\nBu verilere dayanarak profesyonel bir acil durum tespiti yaz."
    )

    headers = {
        "x-api-key": WENOX_API_KEY,
        "Authorization": f"Bearer {WENOX_API_KEY}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": WENOX_MODEL,
        "max_tokens": 300,
        "system": (
            "Sen Solaris-Network uzay havası otonom analiz yapay zekasısın. "
            "Gelen telemetri verilerine bakarak en fazla 2-3 cümlelik, "
            "acil durum formatında profesyonel bir durum tespiti yaz. "
            "Yanıtın kısa, net ve operasyonel olsun."
        ),
        "messages": [
            {"role": "user", "content": kullanici_mesaji}
        ],
    }

    # ── Retry mekanizması ──
    for deneme in range(1, WENOX_MAKS_DENEME + 1):
        try:
            _log("ZEKA", f"Wenox API isteği gönderiliyor... (Deneme {deneme}/{WENOX_MAKS_DENEME})")

            yanit = requests.post(
                WENOX_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            yanit.raise_for_status()

            yanit_json = yanit.json()

            # Claude API yanıt formatından metin çıkar
            content_bloks = yanit_json.get("content", [])
            if content_bloks and isinstance(content_bloks, list):
                ai_metin = content_bloks[0].get("text", "").strip()
            else:
                ai_metin = str(yanit_json.get("content", "")).strip()

            if ai_metin:
                _log("ZEKA", "Wenox AI raporu başarıyla alındı. ✓")
                return ai_metin
            else:
                _log("UYARI", "Wenox API boş yanıt döndürdü.")
                return None

        except requests.exceptions.HTTPError as http_hatasi:
            _log("UYARI", f"Wenox API HTTP Hatası: {http_hatasi.response.status_code} – "
                          f"Deneme {deneme}/{WENOX_MAKS_DENEME}")

        except requests.exceptions.ConnectionError:
            _log("UYARI", f"Wenox API bağlantı hatası – Deneme {deneme}/{WENOX_MAKS_DENEME}")

        except requests.exceptions.Timeout:
            _log("UYARI", f"Wenox API zaman aşımı (30s) – Deneme {deneme}/{WENOX_MAKS_DENEME}")

        except Exception as genel_hata:
            _log("UYARI", f"Wenox API beklenmeyen hata: {genel_hata} – Deneme {deneme}/{WENOX_MAKS_DENEME}")

        if deneme < WENOX_MAKS_DENEME:
            time.sleep(WENOX_BEKLEME_SURESI)

    _log("HATA", "AI Raporu Alınamadı – Tüm denemeler başarısız. Sistem çalışmaya devam ediyor.")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALİZ RAPORU OLUŞTURUCU
# ═══════════════════════════════════════════════════════════════════════════════

def analiz_raporu_olustur(
    master_paket: dict,
    sma_hiz: float | None,
    ivme_verisi: dict | None,
    bz_analiz: dict | None,
    tehdit: dict,
    hafiza_kayit_sayisi: int,
    gelecek_tahmini: dict | None = None,
) -> dict:
    """
    Tüm analiz sonuçlarını birleştirerek kapsamlı bir analiz raporu oluşturur.

    Bu rapor, sistemin karar verme birimleri tarafından tüketilecek
    standartlaştırılmış bir çıktıdır.

    Dönüş:
        dict: Zengin analiz raporu sözlüğü
    """
    gunes = master_paket.get("gunes_ruzgari", {})
    plazma = gunes.get("plazma", {})
    manyetik = gunes.get("manyetik_alan", {})

    rapor = {
        "rapor_bilgisi": {
            "motor": "Solaris-Network Zeka Merkezi",
            "surum": "2.1.0",
            "olusturma_zamani_utc": _utc_simdi(),
            "hafiza_kayit_sayisi": hafiza_kayit_sayisi,
        },
        "anlik_olcumler": {
            "ruzgar_hizi_km_s": plazma.get("hiz_km_s"),
            "plazma_yogunlugu_p_cc": plazma.get("yogunluk_p_cc"),
            "bt_toplam_nT": manyetik.get("bt_nT"),
            "bz_yonu_nT": manyetik.get("bz_gsm_nT"),
            "plazma_zamani": plazma.get("zaman_damgasi"),
            "manyetik_zamani": manyetik.get("zaman_damgasi"),
        },
        "trend_analizi": {
            "hiz_sma": sma_hiz,
            "hiz_ivmelenmesi": ivme_verisi,
            "bz_agirlikli_analiz": bz_analiz,
        },
        "tehdit_degerlendirmesi": tehdit,
        "gelecek_tahmini": gelecek_tahmini if gelecek_tahmini else {
            "olasilik_yuzdesi": None,
            "zaman_ufku": "N/A",
            "risk_seviyesi": "BİLİNMİYOR",
            "faktorler": {},
        },
    }

    return rapor


# ═══════════════════════════════════════════════════════════════════════════════
#  TERMİNAL RAPOR GÖRÜNTÜLEYICI – Fütüristik Çıktı
# ═══════════════════════════════════════════════════════════════════════════════

def raporu_yazdir(rapor: dict):
    """
    Analiz raporunu terminal ekranında fütüristik ve detaylı formatta görüntüler.
    ANSI renk kodları, box-drawing karakterleri ve sembolik göstergelerle
    profesyonel bir kontrol paneli (dashboard) deneyimi sunar.
    """
    # ── Tehdit bilgileri ──
    tehdit = rapor["tehdit_degerlendirmesi"]
    skor = tehdit["tehdit_skoru"]
    seviye = tehdit["tehdit_seviyesi"]
    seviye_tr = tehdit["tehdit_seviyesi_tr"]

    # Skora göre renk seçimi
    skor_renk = {
        "KIRMIZI_YANIP_SONEN": f"{R_KIRMIZI}{R_PARLAK}",
        "KIRMIZI": R_KIRMIZI,
        "TURUNCU": R_SARI,
        "SARI": R_SARI,
        "YESIL": R_YESIL,
    }.get(tehdit["renk_kodu"], R_SIFIRLA)

    # ── Skor barı oluştur (10 bloklu görsel gösterge) ──
    dolu_blok = "█"
    bos_blok = "░"
    dolu_sayisi = int(round(skor))
    skor_bari = dolu_blok * dolu_sayisi + bos_blok * (10 - dolu_sayisi)

    # ══════════════════════════ BAŞLIK ══════════════════════════
    print()
    print(f"{R_MOR}{R_PARLAK}")
    print("    ╔════════════════════════════════════════════════════════════════╗")
    print("    ║            ◈  SOLARIS-NETWORK  ::  Zeka Merkezi              ║")
    print("    ║              SİSTEM ANALİZ RAPORU  v2.0.0                    ║")
    print("    ╚════════════════════════════════════════════════════════════════╝")
    print(f"{R_SIFIRLA}")

    zaman = rapor["rapor_bilgisi"]["olusturma_zamani_utc"]
    kayit = rapor["rapor_bilgisi"]["hafiza_kayit_sayisi"]
    print(f"  {R_DIM}Rapor Zamanı : {zaman}  │  Hafıza Derinliği : {kayit} kayıt{R_SIFIRLA}")

    # ══════════════════════════ TEHDİT SKORU ══════════════════════════
    print()
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  ⚡ TEHDİT DEĞERLENDİRMESİ{R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 66}{R_SIFIRLA}")
    print()
    print(f"      Tehdit Skoru   : {skor_renk}{R_PARLAK}{skor} / 10.0{R_SIFIRLA}")
    print(f"      Skor Barı      : {skor_renk}{skor_bari}{R_SIFIRLA}")
    print(f"      Tehdit Seviyesi: {skor_renk}{R_PARLAK}{seviye_tr} ({seviye}){R_SIFIRLA}")
    print()
    print(f"      {R_DIM}» {tehdit['fiziksel_aciklama']}{R_SIFIRLA}")
    print()

    # Bileşen detayları
    bil = tehdit.get("bilesenler", {})
    print(f"      {R_PARLAK}Bileşen Detayları:{R_SIFIRLA}")
    print(f"        Hız Puanı      : {bil.get('hiz_puani', 'N/A')} / 3.0")
    print(f"        Bz Puanı       : {bil.get('bz_puani', 'N/A')} / 3.0")
    print(f"        Bt Puanı       : {bil.get('bt_puani', 'N/A')} / 1.5")
    print(f"        Yoğunluk Puanı : {bil.get('yogunluk_puani', 'N/A')} / 1.0")
    print(f"        İvme Çarpanı   : ×{bil.get('ivme_carpani', 'N/A')}")
    print(f"        Sinerji Çarpanı: ×{bil.get('sinerji_carpani', 'N/A')}")

    # ══════════════════════════ ANLIK ÖLÇÜMLER ══════════════════════════
    anlik = rapor["anlik_olcumler"]
    print()
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  ☀ ANLIK GÜNEŞ RÜZGARI ÖLÇÜMLERİ{R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 66}{R_SIFIRLA}")
    print()

    hiz = anlik.get("ruzgar_hizi_km_s")
    yog = anlik.get("plazma_yogunlugu_p_cc")
    bt  = anlik.get("bt_toplam_nT")
    bz  = anlik.get("bz_yonu_nT")

    # Hız durum sembolü
    hiz_sembol = "🟢" if (hiz or 0) < ESIK["hiz_sakin"] else ("🟡" if (hiz or 0) < ESIK["hiz_firtina"] else "🔴")
    bz_sembol  = "🟢" if (bz or 0) >= 0 else ("🟡" if (bz or 0) > ESIK["bz_tehlike"] else "🔴")

    print(f"      {hiz_sembol} Rüzgar Hızı    : {R_PARLAK}{hiz if hiz is not None else 'N/A':>10} km/s{R_SIFIRLA}")
    print(f"      {'🔵'} Plazma Yoğunluk : {R_PARLAK}{yog if yog is not None else 'N/A':>10} p/cm³{R_SIFIRLA}")
    print(f"      {'🟣'} Bt (Toplam Güç) : {R_PARLAK}{bt if bt is not None else 'N/A':>10} nT{R_SIFIRLA}")
    print(f"      {bz_sembol} Bz (Manyetik)   : {R_PARLAK}{bz if bz is not None else 'N/A':>10} nT{R_SIFIRLA}")

    # ══════════════════════════ TREND ANALİZİ ══════════════════════════
    trend = rapor["trend_analizi"]
    print()
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  📊 ZAMAN SERİSİ & TREND ANALİZİ{R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 66}{R_SIFIRLA}")
    print()

    # SMA
    sma = trend.get("hiz_sma")
    print(f"      Hız SMA ({SMA_PENCERE}-ölçüm) : {R_CYAN}{R_PARLAK}{sma if sma is not None else 'Yetersiz veri'} km/s{R_SIFIRLA}")

    # İvmelenme
    ivme = trend.get("hiz_ivmelenmesi")
    if ivme:
        trend_yonu = ivme.get("trend_yonu", "N/A")
        anlik_ivme = ivme.get("anlik_ivme_km_s", "N/A")
        ort_ivme = ivme.get("ortalama_ivme_km_s", "N/A")
        maks = ivme.get("maks_sicrama_km_s", "N/A")
        olcum = ivme.get("olcum_sayisi", "N/A")
        print(f"      Trend Yönü       : {R_PARLAK}{trend_yonu}{R_SIFIRLA}")
        print(f"      Anlık İvme       : {anlik_ivme} km/s/ölçüm")
        print(f"      Ortalama İvme    : {ort_ivme} km/s/ölçüm")
        print(f"      Maks. Sıçrama    : {maks} km/s")
        print(f"      Ölçüm Derinliği  : {olcum} kayıt")
    else:
        print(f"      {R_DIM}İvme analizi için yetersiz veri (min. 3 kayıt gerekli){R_SIFIRLA}")

    # Bz ağırlıklı analiz
    print()
    bz_a = trend.get("bz_agirlikli_analiz")
    if bz_a:
        print(f"      {R_PARLAK}Bz Manyetik Yön Analizi:{R_SIFIRLA}")
        print(f"        Ağırlıklı Ort.   : {bz_a.get('agirlikli_ortalama_nT', 'N/A')} nT")
        print(f"        Son Değer        : {bz_a.get('son_deger_nT', 'N/A')} nT")
        print(f"        Durum            : {R_PARLAK}{bz_a.get('durum', 'N/A')}{R_SIFIRLA}")
        print(f"        Güneye Streak    : {bz_a.get('guneye_donuk_ardisik_olcum', 0)} ölçüm")
        print(f"        {R_DIM}» {bz_a.get('fiziksel_yorum', '')}{R_SIFIRLA}")
    else:
        print(f"      {R_DIM}Bz analizi için yetersiz veri{R_SIFIRLA}")

    # ══════════════════════════ AI ANALİZİ ══════════════════════════
    ai_rapor = rapor.get("yapay_zeka_analizi", None)
    print()
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  🤖 AI ANALİZİ (Wenox Claude Sonnet){R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 66}{R_SIFIRLA}")
    print()
    if ai_rapor:
        # AI metnini satır satır renkli yazdır
        for satir in ai_rapor.split('\n'):
            if satir.strip():
                print(f"      {R_MOR}{R_PARLAK}▸{R_SIFIRLA} {R_BEYAZ}{satir.strip()}{R_SIFIRLA}")
    else:
        print(f"      {R_DIM}AI raporu alınamadı veya devre dışı. Sistem matematiksel{R_SIFIRLA}")
        print(f"      {R_DIM}analiz ile çalışmaya devam ediyor.{R_SIFIRLA}")
    print()

    # ══════════════════════════ FIRTINA TAHMİNİ ══════════════════════════
    tahmin = rapor.get("gelecek_tahmini", {})
    olasilik = tahmin.get("olasilik_yuzdesi")
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  🌩  FIRTINA TAHMİN MOTORU{R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 66}{R_SIFIRLA}")
    print()
    if olasilik is not None:
        risk = tahmin.get('risk_seviyesi', 'N/A')
        zaman_u = tahmin.get('zaman_ufku', 'N/A')
        # Risk seviyesine göre renk
        risk_renk = R_KIRMIZI if risk in ('KRİTİK', 'YÜKSEK') else (R_SARI if risk == 'ORTA' else R_YESIL)
        # Olasılık barı (20 blok)
        dolu = int(round(olasilik / 5))
        bar = '█' * dolu + '░' * (20 - dolu)
        print(f"      Fırtına Olasılığı : {risk_renk}{R_PARLAK}%{olasilik}{R_SIFIRLA}")
        print(f"      Olasılık Barı     : {risk_renk}{bar}{R_SIFIRLA}")
        print(f"      Risk Seviyesi     : {risk_renk}{R_PARLAK}{risk}{R_SIFIRLA}")
        print(f"      Zaman Ufku        : {R_PARLAK}{zaman_u}{R_SIFIRLA}")
        print()
        # Faktör detayları
        fak = tahmin.get('faktorler', {})
        if fak:
            print(f"      {R_PARLAK}Faktör Puanları:{R_SIFIRLA}")
            for anahtar, deger in fak.items():
                if isinstance(deger, dict):
                    puan = deger.get('puan', 'N/A')
                    print(f"        {anahtar:<20}: {puan}/25")
            roket = tahmin.get('roketleme_bonusu', 0)
            if roket > 0:
                print(f"        {'🚀 Roketleme':<20}: +{roket}")
    else:
        print(f"      {R_DIM}Tahmin verisi hesaplanamadı.{R_SIFIRLA}")
    print()

    # ══════════════════════════ JSON ÇIKTISI ══════════════════════════
    print()
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  📋 TAM ANALİZ RAPORU (JSON){R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 66}{R_SIFIRLA}")
    print()
    print(f"{R_YESIL}{json.dumps(rapor, indent=4, ensure_ascii=False)}{R_SIFIRLA}")
    print()
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print(f"  {R_DIM}  Solaris-Network Zeka Merkezi – Faz 2 Analiz Tamamlandı ✓{R_SIFIRLA}")
    print(f"  {R_PARLAK}{'═' * 66}{R_SIFIRLA}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANA ÇALIŞTIRMA ORKESTRATÖRü (Main Pipeline)
# ═══════════════════════════════════════════════════════════════════════════════

def calistir() -> dict:
    """
    Solaris-Network Zeka Merkezinin ana orkestrasyon fonksiyonu.
    Veri toplama → Kayıt → Analiz → Puanlama → Raporlama
    boru hattını (pipeline) uçtan uca yönetir.

    Çalışma sırası:
        1. Faz 1 Veri Motorunu çalıştır → master_veri_paketi al
        2. Veriyi SQLite veritabanına kaydet
        3. Son N kaydı veritabanından çek
        4. Zaman serisi analizini yap (SMA, ivme, Bz ağırlıklı ort.)
        5. Tehdit puanlamasını hesapla
        6. Analiz raporunu oluştur ve ekrana yazdır

    Dönüş:
        dict: Kapsamlı analiz raporu
    """
    # ── Başlangıç Banneri ──
    print()
    print(f"{R_MOR}{R_PARLAK}")
    print("    ╔════════════════════════════════════════════════════════════════╗")
    print("    ║         ◈  SOLARIS-NETWORK  ::  Zeka Merkezi v2.0.0         ║")
    print("    ║         Otonom Analiz & Tehdit Puanlama Motoru               ║")
    print("    ╚════════════════════════════════════════════════════════════════╝")
    print(f"{R_SIFIRLA}")

    _log("ZEKA", "Zeka Merkezi başlatılıyor...")

    # ── ADIM 1: Faz 1 Veri Motorunu çalıştır ──
    _log("ZEKA", "Faz 1 Veri Motoru çağrılıyor...")
    master_paket = veri_motoru_calistir()

    if not master_paket:
        _log("HATA", "Veri motoru boş paket döndürdü! Analiz yapılamıyor.")
        return {}

    # ── ADIM 2: Veriyi SQLite'a kaydet ──
    _log("ZEKA", "Kalıcı hafıza modülü başlatılıyor...")
    hafiza = SolarisHafiza()

    hafiza.kaydet(master_paket)

    # ── ADIM 3: Tarihsel verileri çek ──
    _log("ANALİZ", f"Son {ANALIZ_PENCERE_BOYUTU} kayıt hafızadan çekiliyor...")
    tarihsel_kayitlar = hafiza.son_kayitlari_getir(ANALIZ_PENCERE_BOYUTU)
    toplam_kayit = hafiza.toplam_kayit_sayisi()
    _log("ANALİZ", f"Toplam hafıza derinliği: {toplam_kayit} kayıt")

    # ── ADIM 4: Zaman Serisi Analizi ──
    _log("ANALİZ", "Matematiksel analiz başlatılıyor...")
    analiz = AnalizMotoru()

    # Geçerli hız ve Bz değerlerini çıkar
    hiz_degerleri = analiz._gecerli_degerler(tarihsel_kayitlar, "ruzgar_hizi")
    bz_degerleri = analiz._gecerli_degerler(tarihsel_kayitlar, "bz_yonu")

    # SMA hesapla
    sma_hiz = analiz.sma_hesapla(hiz_degerleri)
    _log("ANALİZ", f"Hız SMA({SMA_PENCERE}): {sma_hiz} km/s")

    # İvmelenme hesapla
    ivme_verisi = analiz.ivmelenme_hesapla(hiz_degerleri)
    if ivme_verisi:
        _log("ANALİZ", f"Hız Trendi: {ivme_verisi['trend_yonu']} (anlık ivme: {ivme_verisi['anlik_ivme_km_s']} km/s)")

    # Bz ağırlıklı ortalama
    bz_analiz = analiz.agirlikli_ortalama_bz(bz_degerleri)
    if bz_analiz:
        _log("ANALİZ", f"Bz Durumu: {bz_analiz['durum']} (ağ.ort: {bz_analiz['agirlikli_ortalama_nT']} nT)")

    # ── ADIM 5: Tehdit Puanlaması ──
    _log("ZEKA", "Otonom tehdit puanlama algoritması çalıştırılıyor...")

    gunes = master_paket.get("gunes_ruzgari", {})
    plazma = gunes.get("plazma", {})
    manyetik = gunes.get("manyetik_alan", {})

    # Radyasyon (Proton Flux) verisini tehdit skoruna dahil et
    radyasyon = master_paket.get("radyasyon_durumu", {})
    proton_akisi = radyasyon.get("proton_flux_pfu")

    tehdit = TehditDegerlendirici.puanla(
        anlik_hiz=plazma.get("hiz_km_s"),
        anlik_bz=manyetik.get("bz_gsm_nT"),
        anlik_bt=manyetik.get("bt_nT"),
        anlik_yogunluk=plazma.get("yogunluk_p_cc"),
        sma_hiz=sma_hiz,
        ivme_verisi=ivme_verisi,
        bz_analiz=bz_analiz,
        anlik_proton=proton_akisi,
    )

    _log("ZEKA", f"Tehdit Skoru: {tehdit['tehdit_skoru']}/10 – {tehdit['tehdit_seviyesi_tr']}")

    # ── ADIM 5.5: Fırtına Tahmin Motoru ──
    _log("ZEKA", "Fırtına tahmin motoru çalıştırılıyor...")
    gelecek_tahmini = firtina_ihtimali_hesapla(master_paket, hafiza)

    # ── ADIM 6: Analiz Raporu Oluştur ──
    _log("ZEKA", "Analiz raporu derleniyor...")
    rapor = analiz_raporu_olustur(
        master_paket=master_paket,
        sma_hiz=sma_hiz,
        ivme_verisi=ivme_verisi,
        bz_analiz=bz_analiz,
        tehdit=tehdit,
        hafiza_kayit_sayisi=toplam_kayit,
        gelecek_tahmini=gelecek_tahmini,
    )

    # ── ADIM 7: Yapay Zeka Raporu (Wenox AI) ──
    _log("ZEKA", "Yapay zeka analiz modülü çağrılıyor...")
    ai_metin = yapay_zeka_raporu_al(veri=rapor, skor=tehdit["tehdit_skoru"])
    rapor["yapay_zeka_analizi"] = ai_metin

    # ── ADIM 8: Raporu Yazdır ──
    raporu_yazdir(rapor)

    # ── ADIM 9: Analiz Raporunu Veritabanına Kaydet (Dashboard için) ──
    _log("ZEKA", "Analiz raporu veritabanına kaydediliyor (Dashboard API)...")
    hafiza.analiz_kaydet(rapor)

    _log("ZEKA", "Zeka Merkezi döngüsü tamamlandı. ✓")
    return rapor


# ═══════════════════════════════════════════════════════════════════════════════
#  MODÜL GİRİŞ NOKTASI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    calistir()
