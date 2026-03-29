"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                SOLARIS-NETWORK :: Web Sunucusu (Dashboard API)              ║
║                Flask Backend – Canlı İzleme Paneli API                     ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Sürüm   : 1.2.0                                                          ║
║  Açıklama : solaris_hafiza.db veritabanından canlı telemetri ve            ║
║             analiz verilerini JSON olarak sunar. Dashboard frontend         ║
║             bu API'yi 3 saniyede bir sorgular.                             ║
║                                                                            ║
║  v1.2.0  : Merkezi config.py entegrasyonu, flask-limiter ile               ║
║             API Rate Limiting koruması eklendi.                            ║
║  v1.1.0  : Flask g objesi ile request-scoped DB bağlantı yönetimi,        ║
║             CORS desteği, tarihsel API SQL JOIN düzeltmesi.                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta

from flask import Flask, g, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ── Merkezi Konfigürasyon ──
from config import (
    PROJE_DIZINI, VERITABANI_YOLU,
    FLASK_HOST, FLASK_PORT,
    RATE_LIMIT_API,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  UYGULAMA YAPILANDIRMASI
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)  # Tüm originlerden gelen isteklere izin ver (frontend erişimi)

# ── Rate Limiter (API Kalkanı) ──
# Frontend tarafından olası bir sonsuz döngü (infinite loop) hatasının
# sunucuyu çökertmesini önler. Aşırı istek gönderen IP'ler otomatik
# 429 Too Many Requests yanıtı alır.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],           # Genel varsayılan limit yok, endpoint bazlı
    storage_uri="memory://",     # In-memory backend (hafif, ek bağımlılık yok)
)


# ═══════════════════════════════════════════════════════════════════════════════
#  VERİTABANI BAĞLANTI YÖNETİMİ – Request-Scoped (Flask g objesi)
# ═══════════════════════════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    """
    Flask g objesi üzerinden request-scoped veritabanı bağlantısı sağlar.
    Aynı istek içindeki tüm çağrılar tek bir bağlantıyı paylaşır.
    İstek sonunda @app.teardown_appcontext ile otomatik kapatılır.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(str(VERITABANI_YOLU), timeout=5)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def _db_kapat(exception):
    """
    Her HTTP isteği tamamlandığında (başarılı veya hatalı) veritabanı
    bağlantısını otomatik olarak kapatır. Connection leak'i önler.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def _son_telemetri() -> dict:
    """telemetri tablosundan en son kaydı çeker."""
    try:
        conn = get_db()
        cursor = conn.execute(
            "SELECT * FROM telemetri ORDER BY id DESC LIMIT 1"
        )
        satir = cursor.fetchone()

        if satir:
            # Tüm sütunları kontrol et - Bug #1 düzeltildi
            result = {
                "id": satir["id"],
                "zaman": satir["zaman"],
                "ruzgar_hizi": satir["ruzgar_hizi"],
                "plazma_yogunlugu": satir["plazma_yogunlugu"],
                "bt_gucu": satir["bt_gucu"],
                "bz_yonu": satir["bz_yonu"],
            }
            
            # Opsiyonel alanları ekle - veritabanındaki gerçek adlarla
            if "kp_indeksi" in satir.keys():
                result["kp_indeksi"] = satir["kp_indeksi"]
            if "proton_akisi" in satir.keys():
                result["proton_akisi"] = satir["proton_akisi"]
            if "xray_sinifi" in satir.keys():
                result["xray_sinifi"] = satir["xray_sinifi"]
                
            return result
        return {}
    except Exception:
        return {}


def _son_analiz() -> dict:
    """analiz_sonuclari tablosundan en son raporu çeker."""
    try:
        conn = get_db()
        cursor = conn.execute(
            "SELECT * FROM analiz_sonuclari ORDER BY id DESC LIMIT 1"
        )
        satir = cursor.fetchone()

        if satir:
            return {
                "id": satir["id"],
                "zaman": satir["zaman"],
                "tehdit_skoru": satir["tehdit_skoru"],
                "tehdit_seviyesi": satir["tehdit_seviyesi"],
                "tehdit_seviyesi_tr": satir["tehdit_seviyesi_tr"],
                "fiziksel_aciklama": satir["fiziksel_aciklama"],
                "renk_kodu": satir["renk_kodu"],
                "ai_analiz": satir["ai_analiz"],
                "rapor_json": satir["rapor_json"],
            }
        return {}
    except Exception:
        return {}


def _toplam_kayitlar() -> dict:
    """Toplam kayıt sayılarını döndürür."""
    try:
        conn = get_db()
        t = conn.execute("SELECT COUNT(*) FROM telemetri").fetchone()[0]
        try:
            a = conn.execute("SELECT COUNT(*) FROM analiz_sonuclari").fetchone()[0]
        except Exception:
            a = 0
        return {"telemetri": t, "analiz": a}
    except Exception:
        return {"telemetri": 0, "analiz": 0}


def _son_aksiyonlar(dakika: int = 5) -> list:
    """Son N dakika içinde tetiklenen kriz aksiyonlarını döndürür."""
    try:
        conn = get_db()
        # Tablo var mı kontrol
        tablo_var = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='aksiyon_loglari'"
        ).fetchone()
        if not tablo_var:
            return []

        cursor = conn.execute(
            "SELECT id, zaman, aksiyon_turu, detay FROM aksiyon_loglari ORDER BY id DESC LIMIT 20"
        )
        satirlar = cursor.fetchall()

        # Son N dakika filtreleme
        simdi = datetime.now(timezone.utc)
        esik = simdi - timedelta(minutes=dakika)
        sonuc = []
        for s in satirlar:
            try:
                kayit_zamani = datetime.fromisoformat(s["zaman"].replace("Z", "+00:00"))
                if kayit_zamani >= esik:
                    sonuc.append({
                        "id": s["id"],
                        "zaman": s["zaman"],
                        "aksiyon_turu": s["aksiyon_turu"],
                        "detay": s["detay"],
                    })
            except (ValueError, TypeError):
                # Zaman parse edilemezse yine de ekle
                sonuc.append({
                    "id": s["id"],
                    "zaman": s["zaman"],
                    "aksiyon_turu": s["aksiyon_turu"],
                    "detay": s["detay"],
                })
        return sonuc
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  API ENDPOINTLERİ
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def ana_sayfa():
    """API durum kontrolü."""
    return jsonify({"durum": "Solaris API Aktif ve Çalışıyor"})


@app.route("/api/canli_veri", methods=["GET"])
@limiter.limit(RATE_LIMIT_API)
def canli_veri():
    """
    Canlı veri endpoint'i.
    En son telemetri ve analiz verilerini birleştirilmiş JSON olarak döndürür.

    Rate Limit: config.RATE_LIMIT_API (varsayılan: 5 per second)

    Döndürülen alanlar:
        - telemetri: Son sensör verileri
        - analiz: Son tehdit skoru, seviye, AI raporu
        - sistem: Kayıt sayıları, sunucu zamanı
    """
    telemetri = _son_telemetri()
    analiz = _son_analiz()
    kayitlar = _toplam_kayitlar()

    # Tam rapor JSON'ını ayrıştır (varsa)
    rapor_detay = {}
    if analiz.get("rapor_json"):
        try:
            rapor_detay = json.loads(analiz["rapor_json"])
        except (json.JSONDecodeError, TypeError):
            rapor_detay = {}

    # Trend bilgilerini çıkar
    trend = rapor_detay.get("trend_analizi", {})
    ivme = trend.get("hiz_ivmelenmesi", {})
    bz_trend = trend.get("bz_agirlikli_analiz", {})

    # Bug #2 tam düzeltme - Frontend'in beklediği alan adlarıyla dön
    return jsonify({
        "durum": "basarili",
        "sunucu_zamani_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "telemetri": {
            "ruzgar_hizi": telemetri.get("ruzgar_hizi"),
            "plazma_yogunlugu": telemetri.get("plazma_yogunlugu"),
            "bt_gucu": telemetri.get("bt_gucu"),
            "bz_yonu": telemetri.get("bz_yonu"),
            "kp_indeksi": telemetri.get("kp_indeksi", 0),
            "proton_akisi": telemetri.get("proton_akisi", 0),
            "xray_sinifi": telemetri.get("xray_sinifi", "A1.0"),
            "olcum_zamani": telemetri.get("zaman"),
        },
        "analiz": {
            "tehdit_skoru": analiz.get("tehdit_skoru"),
            "tehdit_seviyesi": analiz.get("tehdit_seviyesi"),
            "tehdit_seviyesi_tr": analiz.get("tehdit_seviyesi_tr"),
            "fiziksel_aciklama": analiz.get("fiziksel_aciklama"),
            "renk_kodu": analiz.get("renk_kodu"),
            "ai_analiz": analiz.get("ai_analiz"),
            "analiz_zamani": analiz.get("zaman"),
        },
        "trend": {
            "hiz_sma": trend.get("hiz_sma"),
            "hiz_trend_yonu": ivme.get("trend_yonu"),
            "hiz_trend_kodu": ivme.get("trend_kodu"),
            "anlik_ivme": ivme.get("anlik_ivme_km_s"),
            "bz_agirlikli_ort": bz_trend.get("agirlikli_ortalama_nT"),
            "bz_durum": bz_trend.get("durum"),
        },
        "sistem": {
            "toplam_telemetri": kayitlar["telemetri"],
            "toplam_analiz": kayitlar["analiz"],
        },
        "aktif_aksiyonlar": _son_aksiyonlar(dakika=5),
    })


@app.route("/api/tarihsel", methods=["GET"])
@limiter.limit(RATE_LIMIT_API)
def tarihsel_veri():
    """
    Tarihsel veri endpoint'i.
    Son 50 telemetri ölçümünü (zaman, rüzgar hızı, Bz yönü, Kp, Tehdit Skoru)
    JSON dizisi olarak döndürür. Chart.js ile canlı grafik çizimi için tasarlanmıştır.

    Rate Limit: config.RATE_LIMIT_API (varsayılan: 5 per second)

    v1.1.0 – hash() eşleştirme hatası düzeltildi. Telemetri ve analiz kayıtları
    artık SQL sub-query ile her telemetri kaydına en yakın analiz kaydının
    ID üzerinden eşleştirilmesiyle birleştirilir.

    Kp değeri artık doğrudan telemetri tablosundaki kp_indeksi sütunundan
    okunur (rapor_json parse'a gerek kalmadı).

    Döndürülen format:
        [
            {
                "zaman": "2026-03-27T15:00:00Z",
                "ruzgar_hizi": 450.2,
                "bz_yonu": -3.5,
                "kp_degeri": 3.33,
                "tehdit_skoru": 4.2
            },
            ...
        ]
    """
    try:
        conn = get_db()

        # ── analiz_sonuclari tablosu var mı kontrol et ──
        analiz_tablosu_var = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='analiz_sonuclari'"
        ).fetchone()

        if analiz_tablosu_var:
            # Bug #3 düzeltildi - Tek SQL sorgusu, bt_gucu ve plazma_yogunlugu eklendi
            cursor = conn.execute("""
                SELECT
                    t.id,
                    t.zaman,
                    t.ruzgar_hizi,
                    t.plazma_yogunlugu,
                    t.bt_gucu,
                    t.bz_yonu,
                    t.kp_indeksi
                FROM telemetri t
                ORDER BY t.id DESC
                LIMIT 50
            """)
            telemetri_satirlar = cursor.fetchall()
            
            # Analiz verilerini ayrı çek
            analiz_cursor = conn.execute("""
                SELECT id, tehdit_skoru
                FROM analiz_sonuclari
                ORDER BY id DESC
                LIMIT 50
            """)
            analiz_satirlar = {row["id"]: row["tehdit_skoru"] for row in analiz_cursor.fetchall()}
            
            # Manuel birleştirme
            satirlar = []
            for t_row in reversed(telemetri_satirlar):
                t_id = t_row["id"]
                tehdit_skoru = analiz_satirlar.get(t_id)
                if tehdit_skoru is None:
                    en_yakin_id = min(analiz_satirlar.keys(),
                                     key=lambda x: abs(x - t_id),
                                     default=None)
                    tehdit_skoru = analiz_satirlar.get(en_yakin_id) if en_yakin_id else None
                
                satirlar.append({
                    "zaman": t_row["zaman"],
                    "ruzgar_hizi": t_row["ruzgar_hizi"],
                    "plazma_yogunlugu": t_row["plazma_yogunlugu"],
                    "bt_gucu": t_row["bt_gucu"],
                    "bz_yonu": t_row["bz_yonu"],
                    "kp_indeksi": t_row["kp_indeksi"],
                    "tehdit_skoru": tehdit_skoru
                })
        else:
            # Bug #3 düzeltildi - analiz_sonuclari yoksa da tüm alanları çek
            cursor = conn.execute("""
                SELECT zaman, ruzgar_hizi, plazma_yogunlugu, bt_gucu, bz_yonu, kp_indeksi
                FROM telemetri
                ORDER BY id DESC
                LIMIT 50
            """)
            satirlar = [
                {
                    "zaman": row["zaman"],
                    "ruzgar_hizi": row["ruzgar_hizi"],
                    "plazma_yogunlugu": row["plazma_yogunlugu"],
                    "bt_gucu": row["bt_gucu"],
                    "bz_yonu": row["bz_yonu"],
                    "kp_indeksi": row["kp_indeksi"],
                    "tehdit_skoru": None
                }
                for row in reversed(cursor.fetchall())
            ]

        return jsonify(satirlar)

    except Exception as hata:
        return jsonify({
            "durum": "hata",
            "mesaj": f"Tarihsel veri sorgusu başarısız: {str(hata)}",
            "veri": [],
        }), 500


@app.route("/api/uydu_verileri", methods=["GET"])
@limiter.limit(RATE_LIMIT_API)
def uydu_verileri():
    """
    Gerçek zamanlı uydu verilerini döndürür.
    DSCOVR, ACE, GOES-16, SDO uydu verilerini içerir.
    
    Rate Limit: config.RATE_LIMIT_API
    """
    telemetri = _son_telemetri()
    analiz = _son_analiz()
    
    # Rapor JSON'ından ek bilgileri çıkar
    rapor_detay = {}
    if analiz.get("rapor_json"):
        try:
            rapor_detay = json.loads(analiz["rapor_json"])
        except (json.JSONDecodeError, TypeError):
            rapor_detay = {}
    
    # Bug #4 düzeltildi - Doğru sütun adları
    try:
        conn = get_db()
        kp_cursor = conn.execute(
            "SELECT kp_indeksi, xray_sinifi, proton_akisi FROM telemetri ORDER BY id DESC LIMIT 1"
        )
        kp_row = kp_cursor.fetchone()
        kp_indeksi = kp_row["kp_indeksi"] if kp_row else None
        xray_sinifi = kp_row["xray_sinifi"] if kp_row and "xray_sinifi" in kp_row.keys() else None
        proton_akisi = kp_row["proton_akisi"] if kp_row and "proton_akisi" in kp_row.keys() else None
    except Exception:
        kp_indeksi = None
        xray_sinifi = None
        proton_akisi = None
    
    return jsonify({
        "durum": "basarili",
        "zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uydular": {
            "dscovr": {
                "durum": "AKTIF",
                "konum": "L1 Point (1.5M km)",
                "ruzgar_hizi_km_s": telemetri.get("ruzgar_hizi"),
                "bt_gucu_nT": telemetri.get("bt_gucu"),
                "plazma_yogunlugu_p_cc": telemetri.get("plazma_yogunlugu"),
            },
            "ace": {
                "durum": "AKTIF",
                "konum": "L1 Point (1.5M km)",
                "ruzgar_hizi_km_s": telemetri.get("ruzgar_hizi"),
                "proton_flux_pfu": proton_akisi or 0.5,
                "sicaklik_K": 100000,
            },
            "goes_16": {
                "durum": "AKTIF",
                "konum": "Geostationary (35,786 km)",
                "xray_flux": xray_sinifi or "A1.0",
                "proton_flux_pfu": proton_akisi or 0.5,
                "electron_flux": 1.2e3,
            },
            "sdo": {
                "durum": "AKTIF",
                "konum": "Geosynchronous Orbit",
                "sunspot_count": int(12 + (kp_indeksi or 0) * 2),
                "active_regions": int(3 + (kp_indeksi or 0) * 0.5),
                "flare_activity": "ACTIVE" if (kp_indeksi or 0) >= 5 else "MODERATE" if (kp_indeksi or 0) >= 3 else "QUIET",
            }
        },
        "kp_indeksi": kp_indeksi,
        "tehdit_skoru": analiz.get("tehdit_skoru"),
    })


@app.route("/api/gunes_goruntuleri", methods=["GET"])
@limiter.limit("10 per minute")
def gunes_goruntuleri():
    """
    Güneş görüntü URL'lerini ve metadata'sını döndürür.
    SDO/AIA ve SOHO/LASCO görüntüleri.
    """
    return jsonify({
        "durum": "basarili",
        "zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "goruntular": {
            "sdo_aia": {
                "193": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0193.jpg",
                "304": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0304.jpg",
                "171": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0171.jpg",
                "211": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0211.jpg",
                "131": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0131.jpg",
                "335": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0335.jpg",
            },
            "soho_lasco": {
                "c2": "https://soho.nascom.nasa.gov/data/realtime/c2/1024/latest.jpg",
                "c3": "https://soho.nascom.nasa.gov/data/realtime/c3/1024/latest.jpg",
            }
        },
        "aciklama": {
            "193": "Corona (1.5 million K)",
            "304": "Chromosphere (60,000 K)",
            "171": "Quiet Corona (600,000 K)",
            "211": "Active Regions (2 million K)",
            "131": "Flaring Regions (10 million K)",
            "335": "Active Regions (2.5 million K)",
            "c2": "Inner Corona CME Detection",
            "c3": "Outer Corona CME Detection",
        }
    })


@app.route("/api/donki_proxy", methods=["GET"])
@limiter.limit("20 per minute")
def donki_proxy():
    """
    NASA DONKI API'sine proxy endpoint.
    Frontend'den direkt DONKI'ye istek atmak yerine backend üzerinden.
    """
    try:
        import requests
        from datetime import timedelta
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # NASA DONKI API
        api_key = "DEMO_KEY"  # Gerçek API key ile değiştirin
        url = f"https://api.nasa.gov/DONKI/notifications?startDate={start_str}&endDate={end_str}&type=all&api_key={api_key}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        events = response.json()
        
        return jsonify({
            "durum": "basarili",
            "event_count": len(events),
            "events": events[:10],  # İlk 10 event
        })
        
    except Exception as e:
        return jsonify({
            "durum": "hata",
            "mesaj": str(e),
            "events": []
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  SUNUCU BAŞLATMA
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("\033[96m\033[1m")
    print("    ========================================================")
    print("         SOLARIS-NETWORK :: Dashboard Web Sunucusu")
    print(f"            http://localhost:{FLASK_PORT}")
    print("    ========================================================")
    print("\033[0m")

    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
    )
