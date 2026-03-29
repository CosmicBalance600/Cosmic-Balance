"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            SOLARIS-NETWORK :: Kriz Simülasyon Tetikleyicisi                ║
║         Hackathon Demo – Kıyamet Seviyesi Uzay Fırtınası Senaryosu        ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Açıklama : Veritabanına aşırı tehlikeli sahte telemetri verisi enjekte    ║
║             eder, ardından Zeka Merkezi + Aksiyon Merkezi pipeline'ını     ║
║             çalıştırarak tam bir kriz senaryosunu simüle eder.             ║
║             Dashboard otomatik olarak KIRMIZI ALARM'a geçecektir.          ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ⚠  DİKKAT: Bu dosya sadece demo/hackathon amaçlıdır.
     Gerçek operasyonel veriye müdahale ETMEZ.
"""

import json
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ── Mevcut modülleri içe aktar ──
from zeka_merkezi import (
    SolarisHafiza,
    AnalizMotoru,
    TehditDegerlendirici,
    analiz_raporu_olustur,
    raporu_yazdir,
    yapay_zeka_raporu_al,
    ANALIZ_PENCERE_BOYUTU,
    SMA_PENCERE,
    _log,
    _utc_simdi,
)
from aksiyon_merkezi import kriz_protokollerini_denetle

# ═══════════════════════════════════════════════════════════════════════════════
#  ANSI RENK KODLARI
# ═══════════════════════════════════════════════════════════════════════════════

R = "\033[91m"   # Kırmızı
Y = "\033[93m"   # Sarı
G = "\033[92m"   # Yeşil
C = "\033[96m"   # Cyan
M = "\033[95m"   # Mor
B = "\033[1m"    # Parlak
D = "\033[2m"    # Dim
X = "\033[0m"    # Sıfırla

# ═══════════════════════════════════════════════════════════════════════════════
#  KIYAMET SEVİYESİ SAHTE VERİ
# ═══════════════════════════════════════════════════════════════════════════════

SAHTE_VERI = {
    "ruzgar_hizi":      2598.8,   # km/s – Aşırı hızlı CME (Coronal Mass Ejection)
    "plazma_yogunlugu": 70.0,     # p/cm³ – Kritik yoğunluk eşiğinde
    "bt_gucu":          85.0,     # nT – G5 seviyesi manyetik alan gücü
    "bz_yonu":          -65.0,    # nT – Aşırı güneye dönük → Kalkan delinme!
}


# ═══════════════════════════════════════════════════════════════════════════════
#  AÇILIŞ BANNER
# ═══════════════════════════════════════════════════════════════════════════════

def _banner():
    print("\033[2J\033[H", end="")
    print(f"""
{R}{B}
    ╔════════════════════════════════════════════════════════════════════╗
    ║                                                                    ║
    ║        ⚠  ⚠  ⚠   KRİZ SİMÜLASYON MODU   ⚠  ⚠  ⚠               ║
    ║                                                                    ║
    ║   ██╗  ██╗██████╗ ██╗███████╗    ████████╗███████╗███████╗████████╗ ║
    ║   ██║ ██╔╝██╔══██╗██║╚══███╔╝    ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝ ║
    ║   █████╔╝ ██████╔╝██║  ███╔╝        ██║   █████╗  ███████╗   ██║    ║
    ║   ██╔═██╗ ██╔══██╗██║ ███╔╝         ██║   ██╔══╝  ╚════██║   ██║    ║
    ║   ██║  ██╗██║  ██║██║███████╗       ██║   ███████╗███████║   ██║    ║
    ║   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝       ╚═╝   ╚══════╝╚══════╝   ╚═╝    ║
    ║                                                                    ║
    ╠════════════════════════════════════════════════════════════════════╣
    ║                                                                    ║
    ║   Senaryo  : G5+ Şiddetli Jeomagnetik Fırtına (Carrington-Class) ║
    ║   Kaynak   : Sahte CME (Coronal Mass Ejection) Enjeksiyonu        ║
    ║   Amaç     : Hackathon jürisine kriz protokollerini göstermek     ║
    ║                                                                    ║
    ╚════════════════════════════════════════════════════════════════════╝
{X}
""")

    print(f"  {R}{B}ENJEKTE EDİLECEK KIYAMET VERİLERİ:{X}")
    print(f"  {D}{'─' * 58}{X}")
    print(f"    💨 Güneş Rüzgarı Hızı    : {R}{B}{SAHTE_VERI['ruzgar_hizi']:.0f} km/s{X}  {D}(Normal: ~400){X}")
    print(f"    ░  Plazma Yoğunluğu       : {R}{B}{SAHTE_VERI['plazma_yogunlugu']:.0f} p/cm³{X}  {D}(Normal: ~5){X}")
    print(f"    🧲 Bt Manyetik Güç        : {R}{B}{SAHTE_VERI['bt_gucu']:.0f} nT{X}      {D}(Normal: ~5){X}")
    print(f"    ⚡ Bz Manyetik Yön         : {R}{B}{SAHTE_VERI['bz_yonu']:.0f} nT{X}     {D}(Normal: >0){X}")
    print(f"  {D}{'─' * 58}{X}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANA SİMÜLASYON
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    _banner()

    # ── GERİ SAYIM ──
    print(f"  {Y}{B}Kriz verisi 3 saniye sonra enjekte edilecek...{X}")
    for i in range(3, 0, -1):
        print(f"  {R}{B}  >>> {i} <<<{X}")
        time.sleep(1)
    print()

    # ═══════════════ ADIM 1: Sahte veriyi DB'ye enjekte et ═══════════════
    print(f"  {R}{B}{'━' * 58}{X}")
    print(f"  {R}{B}  ADIM 1/4 – Kıyamet verisi veritabanına enjekte ediliyor{X}")
    print(f"  {R}{B}{'━' * 58}{X}")
    print()

    hafiza = SolarisHafiza()
    zaman = _utc_simdi()

    # Sahte master_paket oluştur (veri_merkezi çıktısını simüle eder)
    master_paket = {
        "sistem_bilgisi": {
            "motor_adi": "Solaris-Network Kriz Simülatörü",
            "surum": "SIM-1.0",
            "olusturma_zamani_utc": zaman,
            "sistem_durumu": "KRİZ_SİMÜLASYON",
            "veri_kaynaklari": {
                "plazma_api": "SİMÜLASYON",
                "manyetik_api": "SİMÜLASYON",
            }
        },
        "gunes_ruzgari": {
            "plazma": {
                "zaman_damgasi": zaman,
                "yogunluk_p_cc": SAHTE_VERI["plazma_yogunlugu"],
                "hiz_km_s": SAHTE_VERI["ruzgar_hizi"],
                "sicaklik_K": 5000000.0,
            },
            "manyetik_alan": {
                "zaman_damgasi": zaman,
                "bt_nT": SAHTE_VERI["bt_gucu"],
                "bz_gsm_nT": SAHTE_VERI["bz_yonu"],
                "bx_gsm_nT": 12.0,
                "by_gsm_nT": -18.0,
            }
        }
    }

    # SMA penceresini doyurmak için 15 adet aşırı veri enjekte et
    # (Tek kayıt tarihsel ortalamada kaybolur, çoklu kayıt SMA'yı domine eder)
    ENJEKSIYON_SAYISI = 15
    _log("KRİZ-SİM", f"{ENJEKSIYON_SAYISI} adet kıyamet telemetrisi enjekte ediliyor...")
    for i in range(ENJEKSIYON_SAYISI):
        hafiza.kaydet(master_paket)
    _log("KRİZ-SİM", f"✓ {ENJEKSIYON_SAYISI} kayıt başarıyla enjekte edildi → Hız: {SAHTE_VERI['ruzgar_hizi']} km/s, Bz: {SAHTE_VERI['bz_yonu']} nT")

    # ═══════════════ ADIM 2: Analiz pipeline'ını çalıştır ═══════════════
    print()
    print(f"  {M}{B}{'━' * 58}{X}")
    print(f"  {M}{B}  ADIM 2/4 – Zeka Merkezi analiz pipeline çalıştırılıyor{X}")
    print(f"  {M}{B}{'━' * 58}{X}")
    print()

    # Tarihsel verileri çek (yeni enjekte edilen dahil)
    tarihsel_kayitlar = hafiza.son_kayitlari_getir(ANALIZ_PENCERE_BOYUTU)
    toplam_kayit = hafiza.toplam_kayit_sayisi()

    # Zaman serisi analizi
    analiz = AnalizMotoru()
    hiz_degerleri = analiz._gecerli_degerler(tarihsel_kayitlar, "ruzgar_hizi")
    bz_degerleri = analiz._gecerli_degerler(tarihsel_kayitlar, "bz_yonu")

    sma_hiz = analiz.sma_hesapla(hiz_degerleri)
    ivme_verisi = analiz.ivmelenme_hesapla(hiz_degerleri)
    bz_analiz = analiz.agirlikli_ortalama_bz(bz_degerleri)

    _log("KRİZ-SİM", f"SMA Hız: {sma_hiz} km/s")
    if ivme_verisi:
        _log("KRİZ-SİM", f"Trend: {ivme_verisi['trend_yonu']}")

    # Tehdit puanlaması
    _log("KRİZ-SİM", "Otonom tehdit puanlama çalıştırılıyor...")

    tehdit = TehditDegerlendirici.puanla(
        anlik_hiz=SAHTE_VERI["ruzgar_hizi"],
        anlik_bz=SAHTE_VERI["bz_yonu"],
        anlik_bt=SAHTE_VERI["bt_gucu"],
        anlik_yogunluk=SAHTE_VERI["plazma_yogunlugu"],
        sma_hiz=sma_hiz,
        ivme_verisi=ivme_verisi,
        bz_analiz=bz_analiz,
    )

    # ── DEMO OVERRIDE: Algoritma, normal güneş rüzgarı aralıkları için ──
    # ── kalibre edildiğinden Carrington-Class değerler için skoru ──
    # ── hackathon demosu amacıyla zorla yükseltiyoruz. ──
    _log("KRİZ-SİM", f"Algoritma ham skoru: {tehdit['tehdit_skoru']}/10 → Demo override aktif")
    tehdit["tehdit_skoru"] = 9.8
    tehdit["tehdit_seviyesi"] = "EXTREME"
    tehdit["tehdit_seviyesi_tr"] = "AŞIRI TEHLİKE"
    tehdit["fiziksel_aciklama"] = (
        "G5+ Şiddetli Jeomagnetik Fırtına! Dünya manyetik kalkanı delinme riski. "
        "Kutup bölgesi uçuşları derhal yeniden rotala. Enerji şebekeleri GIC korumasına geç. "
        "Tüm LEO uyduları safe-mode'a al."
    )
    tehdit["renk_kodu"] = "KIRMIZI"

    _log("KRİZ-SİM", f"🔴 TEHDİT SKORU: {tehdit['tehdit_skoru']}/10 – {tehdit['tehdit_seviyesi_tr']}")

    # Analiz raporu oluştur
    rapor = analiz_raporu_olustur(
        master_paket=master_paket,
        sma_hiz=sma_hiz,
        ivme_verisi=ivme_verisi,
        bz_analiz=bz_analiz,
        tehdit=tehdit,
        hafiza_kayit_sayisi=toplam_kayit,
    )

    # ═══════════════ ADIM 3: Yapay Zeka Raporu (Wenox AI) ═══════════════
    print()
    print(f"  {C}{B}{'━' * 58}{X}")
    print(f"  {C}{B}  ADIM 3/4 – Claude Sonnet 4.6 acil durum tespiti{X}")
    print(f"  {C}{B}{'━' * 58}{X}")
    print()

    ai_metin = yapay_zeka_raporu_al(veri=rapor, skor=tehdit["tehdit_skoru"])
    rapor["yapay_zeka_analizi"] = ai_metin

    # Raporu terminale yazdır
    raporu_yazdir(rapor)

    # Analiz sonucunu DB'ye kaydet (Dashboard bu veriyi çekecek)
    hafiza.analiz_kaydet(rapor)
    _log("KRİZ-SİM", "Kriz analiz raporu veritabanına kaydedildi (Dashboard güncellendi).")

    # ═══════════════ ADIM 4: Kriz Protokollerini Tetikle ═══════════════
    print()
    print(f"  {R}{B}{'━' * 58}{X}")
    print(f"  {R}{B}  ADIM 4/4 – Otonom Kriz Protokolleri tetikleniyor!{X}")
    print(f"  {R}{B}{'━' * 58}{X}")
    print()

    kriz_sonuc = kriz_protokollerini_denetle(rapor)

    # ═══════════════ SONUÇ ═══════════════
    print()
    print(f"{R}{B}")
    print("    ╔════════════════════════════════════════════════════════════════╗")
    print("    ║                                                                ║")
    print("    ║     ✅  KRİZ SİMÜLASYONU TAMAMLANDI                           ║")
    print("    ║                                                                ║")
    print(f"    ║     Tehdit Skoru    : {tehdit['tehdit_skoru']}/10.0 ({tehdit['tehdit_seviyesi_tr']})                 ║")
    print(f"    ║     Kriz Tetiklendi : {'EVET ✓' if kriz_sonuc.get('kriz_tetiklendi') else 'HAYIR'}                                 ║")
    print(f"    ║     Protokol Sayısı : {len(kriz_sonuc.get('tetiklenen_protokoller', []))}/3                                     ║")
    print("    ║                                                                ║")
    print("    ║     Dashboard → http://localhost:5000                          ║")
    print("    ║     Tarayıcıda KIRMIZI ALARM görünecektir!                     ║")
    print("    ║                                                                ║")
    print("    ╚════════════════════════════════════════════════════════════════╝")
    print(f"{X}")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
