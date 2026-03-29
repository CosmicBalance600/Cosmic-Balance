# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                SOLARIS-NETWORK :: Ana Orkestratör (The Daemon)              ║
║            Faz 3 – 7/24 Otonom Uzay Havası İzleme Sistemi                 ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Sürüm   : 3.0.0                                                          ║
║  Açıklama : Solaris-Network'ün 'Ana Şalteri'. Tüm fazları                 ║
║             (Veri → Zeka → Aksiyon) tek bir sürekli döngüde               ║
║             orkestre eder. Ctrl+C ile zarif kapanma desteği.               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Windows terminal encoding fix
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import time
import logging
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Faz 2 ve Faz 3 modül bağlantıları ──
# zeka_merkezi.calistir() zaten veri_merkezi.calistir()'ı içinden çağırır
from zeka_merkezi import calistir as zeka_motoru_calistir
from aksiyon_merkezi import kriz_protokollerini_denetle

# ═══════════════════════════════════════════════════════════════════════════════
#  SABİTLER (Constants)
# ═══════════════════════════════════════════════════════════════════════════════

# Döngü tekrar aralığı (saniye) – Üretimde 300 (5 dk), hackathon/test için 10
DONGU_ARALIGI_SANIYE = 15

# Terminal çıktı renk kodları (ANSI)
R_KIRMIZI  = "\033[91m"
R_YESIL    = "\033[92m"
R_SARI     = "\033[93m"
R_MAVI     = "\033[94m"
R_MOR      = "\033[95m"
R_CYAN     = "\033[96m"
R_BEYAZ    = "\033[97m"
R_TURUNCU  = "\033[38;5;208m"
R_PARLAK   = "\033[1m"
R_DIM      = "\033[2m"
R_SIFIRLA  = "\033[0m"


# ═══════════════════════════════════════════════════════════════════════════════
#  KURUMSAL DOSYA LOGLAMA (RotatingFileHandler)
# ═══════════════════════════════════════════════════════════════════════════════

# Log dosyası yolu (proje kök dizininde)
_LOG_DIZINI = Path(__file__).resolve().parent
_LOG_DOSYASI = _LOG_DIZINI / "solaris_daemon.log"

# Dosya logger'ı oluştur
solaris_logger = logging.getLogger("solaris-daemon")
solaris_logger.setLevel(logging.DEBUG)

# RotatingFileHandler: 5 MB maks, 3 yedek dosya
_dosya_handler = RotatingFileHandler(
    str(_LOG_DOSYASI),
    maxBytes=5 * 1024 * 1024,   # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_dosya_handler.setLevel(logging.DEBUG)
_dosya_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
)
solaris_logger.addHandler(_dosya_handler)


# ═══════════════════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

def _utc_simdi() -> str:
    """Şu anki UTC zamanını ISO 8601 formatında döndürür."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(seviye: str, mesaj: str):
    """
    Renk kodlu, zaman damgalı terminal log çıktısı.
    Aynı zamanda solaris_daemon.log dosyasına da yazar (renkiz saf metin).
    """
    renk = {
        "DAEMON":    R_CYAN,
        "ORKESTRA":  R_MOR,
        "BİLGİ":    R_YESIL,
        "UYARI":    R_SARI,
        "HATA":     R_KIRMIZI,
        "SİSTEM":   R_MAVI,
    }.get(seviye, R_SIFIRLA)
    print(f"{R_CYAN}[{_utc_simdi()}]{R_SIFIRLA} {renk}{R_PARLAK}[{seviye}]{R_SIFIRLA} {mesaj}")

    # Dosya logu (renkiz saf metin)
    log_seviye_haritasi = {
        "DAEMON":    logging.INFO,
        "ORKESTRA":  logging.INFO,
        "BİLGİ":    logging.INFO,
        "UYARI":    logging.WARNING,
        "HATA":     logging.ERROR,
        "SİSTEM":   logging.INFO,
    }
    python_seviye = log_seviye_haritasi.get(seviye, logging.INFO)
    solaris_logger.log(python_seviye, f"[{seviye}] {mesaj}")


# ═══════════════════════════════════════════════════════════════════════════════
#  ASCII ART AÇILIŞ EKRANI
# ═══════════════════════════════════════════════════════════════════════════════

def acilis_ekranini_goster():
    """
    Solaris-Network ASCII art açılış ekranını ve sistem bilgilerini
    terminale bastırır. Fütüristik bir uzay istasyonu kontrol paneli
    hissiyatı verir.
    """
    # Terminal temizleme (opsiyonel – platformdan bağımsız)
    print("\033[2J\033[H", end="")

    banner = f"""
{R_CYAN}{R_PARLAK}
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                                                                       ║
    ║   {R_SARI}    ███████╗ ██████╗ ██╗      █████╗ ██████╗ ██╗███████╗{R_CYAN}           ║
    ║   {R_SARI}    ██╔════╝██╔═══██╗██║     ██╔══██╗██╔══██╗██║██╔════╝{R_CYAN}           ║
    ║   {R_SARI}    ███████╗██║   ██║██║     ███████║██████╔╝██║███████╗{R_CYAN}           ║
    ║   {R_SARI}    ╚════██║██║   ██║██║     ██╔══██║██╔══██╗██║╚════██║{R_CYAN}           ║
    ║   {R_SARI}    ███████║╚██████╔╝███████╗██║  ██║██║  ██║██║███████║{R_CYAN}           ║
    ║   {R_SARI}    ╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝{R_CYAN}           ║
    ║                                                                       ║
    ║   {R_TURUNCU}{R_PARLAK}      ███╗   ██╗███████╗████████╗██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗{R_CYAN}  ║
    ║   {R_TURUNCU}{R_PARLAK}      ████╗  ██║██╔════╝╚══██╔══╝██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝{R_CYAN}  ║
    ║   {R_TURUNCU}{R_PARLAK}      ██╔██╗ ██║█████╗     ██║   ██║ █╗ ██║██║   ██║██████╔╝█████╔╝{R_CYAN}   ║
    ║   {R_TURUNCU}{R_PARLAK}      ██║╚██╗██║██╔══╝     ██║   ██║███╗██║██║   ██║██╔══██╗██╔═██╗{R_CYAN}   ║
    ║   {R_TURUNCU}{R_PARLAK}      ██║ ╚████║███████╗   ██║   ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗{R_CYAN}  ║
    ║   {R_TURUNCU}{R_PARLAK}      ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝{R_CYAN}  ║
    ║                                                                       ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                       ║
    ║   {R_YESIL}☀  Uzay Havası Erken Uyarı Sistemi   │  Sürüm 3.0.0{R_CYAN}              ║
    ║   {R_YESIL}⚡ Otonom İzleme • Analiz • Aksiyon   │  Durum: ÇEVRİMİÇİ{R_CYAN}        ║
    ║                                                                       ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                       ║
    ║   {R_DIM}Faz 1 │ Veri Merkezi    │ NOAA/SWPC Gerçek Zamanlı Veri{R_CYAN}         ║
    ║   {R_DIM}Faz 2 │ Zeka Merkezi    │ Otonom Tehdit Puanlama (1-10){R_CYAN}         ║
    ║   {R_DIM}Faz 3 │ Aksiyon Merkezi │ Kriz Protokolleri & Webhook{R_CYAN}           ║
    ║                                                                       ║
    ╚═══════════════════════════════════════════════════════════════════════╝
{R_SIFIRLA}"""

    print(banner)

    # Sistem başlatma animasyonu
    baslangic_modulleri = [
        ("Veri Motoru (NOAA API Bağlantısı)", "Faz 1"),
        ("Zeka Merkezi (Tehdit Analiz Motoru)", "Faz 2"),
        ("Aksiyon Merkezi (Kriz Protokolleri)", "Faz 3"),
        ("SQLite Kalıcı Hafıza Birimi", "DB"),
        ("Daemon Orkestrasyon Döngüsü", "CORE"),
    ]

    print(f"  {R_PARLAK}{R_CYAN}Sistem Modülleri Başlatılıyor...{R_SIFIRLA}")
    print(f"  {R_DIM}{'─' * 62}{R_SIFIRLA}")

    for modul_adi, faz in baslangic_modulleri:
        time.sleep(0.3)  # Görsel efekt için kısa gecikme
        print(f"  {R_YESIL}  ✓{R_SIFIRLA}  [{R_CYAN}{faz:>5}{R_SIFIRLA}]  {modul_adi}")

    print(f"  {R_DIM}{'─' * 62}{R_SIFIRLA}")
    print()
    print(f"  {R_YESIL}{R_PARLAK}  ██  TÜM SİSTEMLER ÇEVRİMİÇİ – DAEMON AKTİF  ██{R_SIFIRLA}")
    print(f"  {R_DIM}  Tarama aralığı: {DONGU_ARALIGI_SANIYE} saniye │ Çıkış: Ctrl+C{R_SIFIRLA}")
    print()
    print(f"  {R_DIM}{'═' * 62}{R_SIFIRLA}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  DÖNGÜ DURUM RAPORU
# ═══════════════════════════════════════════════════════════════════════════════

def dongu_baslik_yazdir(dongu_sayisi: int):
    """Her tarama döngüsünün başında bilgi banneri bastırır."""
    print()
    print(f"{R_CYAN}{R_PARLAK}{'▓' * 74}{R_SIFIRLA}")
    print(f"{R_CYAN}{R_PARLAK}▓{'':^72}▓{R_SIFIRLA}")
    print(f"{R_CYAN}{R_PARLAK}▓{'☀  SOLARIS-NETWORK  ::  Tarama Döngüsü #' + str(dongu_sayisi):^72}▓{R_SIFIRLA}")
    print(f"{R_CYAN}{R_PARLAK}▓{'Zaman: ' + _utc_simdi():^72}▓{R_SIFIRLA}")
    print(f"{R_CYAN}{R_PARLAK}▓{'':^72}▓{R_SIFIRLA}")
    print(f"{R_CYAN}{R_PARLAK}{'▓' * 74}{R_SIFIRLA}")
    print()


def dongu_ozet_yazdir(dongu_sayisi: int, rapor: dict, kriz_sonuc: dict, sure_saniye: float):
    """Her tarama döngüsünün sonunda özet rapor bastırır."""
    tehdit = rapor.get("tehdit_degerlendirmesi", {})
    skor = tehdit.get("tehdit_skoru", 0.0)
    seviye_tr = tehdit.get("tehdit_seviyesi_tr", "N/A")

    # Skor rengini belirle
    if skor >= 9.0:
        skor_renk = f"{R_KIRMIZI}{R_PARLAK}"
    elif skor >= 7.0:
        skor_renk = R_KIRMIZI
    elif skor >= 5.0:
        skor_renk = R_SARI
    elif skor >= 3.0:
        skor_renk = R_SARI
    else:
        skor_renk = R_YESIL

    kriz_durum = f"{R_KIRMIZI}{R_PARLAK}EVET – Protokoller tetiklendi!{R_SIFIRLA}" if kriz_sonuc.get("kriz_tetiklendi") else f"{R_YESIL}HAYIR – Durum normal{R_SIFIRLA}"

    print()
    print(f"  {R_PARLAK}{'═' * 62}{R_SIFIRLA}")
    print(f"  {R_PARLAK}  📋 DÖNGÜ #{dongu_sayisi} – ÖZET RAPOR{R_SIFIRLA}")
    print(f"  {R_PARLAK}{'─' * 62}{R_SIFIRLA}")
    print(f"    Tehdit Skoru     : {skor_renk}{skor}/10.0 – {seviye_tr}{R_SIFIRLA}")
    print(f"    Kriz Tetiklendi  : {kriz_durum}")
    print(f"    İşlem Süresi     : {sure_saniye:.2f} saniye")
    print(f"    Sonraki Tarama   : {DONGU_ARALIGI_SANIYE} saniye sonra")
    print(f"  {R_PARLAK}{'═' * 62}{R_SIFIRLA}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  GERİ SAYIM GÖSTERGESİ
# ═══════════════════════════════════════════════════════════════════════════════

def geri_sayim(saniye: int):
    """
    Sonraki taramaya kadar olan süreyi canlı geri sayım olarak gösterir.
    Terminal'de tek satırda güncellenen dinamik bir sayaç.
    """
    for kalan in range(saniye, 0, -1):
        # İlerleme çubuğu
        gecen = saniye - kalan
        doluluk = int((gecen / saniye) * 30)
        bar = "█" * doluluk + "░" * (30 - doluluk)

        sys.stdout.write(
            f"\r  {R_DIM}⏳ Sonraki tarama: {R_CYAN}{R_PARLAK}{kalan:>3}s{R_SIFIRLA} "
            f"{R_DIM}│{R_SIFIRLA} {R_CYAN}{bar}{R_SIFIRLA} "
            f"{R_DIM}│ {_utc_simdi()}{R_SIFIRLA}   "
        )
        sys.stdout.flush()
        time.sleep(1)

    # Sayım tamamlandı – satırı temizle
    sys.stdout.write(f"\r{' ' * 90}\r")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════════
#  KAPANIŞ EKRANI
# ═══════════════════════════════════════════════════════════════════════════════

def kapanis_ekranini_goster(toplam_dongu: int):
    """Zarif kapanış mesajı ve istatistikleri gösterir."""
    print()
    print()
    print(f"{R_SARI}{R_PARLAK}")
    print("    ╔════════════════════════════════════════════════════════════════╗")
    print("    ║                                                                ║")
    print("    ║         ☀  SOLARIS-NETWORK  ::  SİSTEM KAPANIYOR              ║")
    print("    ║                                                                ║")
    print("    ╠════════════════════════════════════════════════════════════════╣")
    print(f"    ║   Toplam Tarama Döngüsü  :  {toplam_dongu:>6}                           ║")
    print(f"    ║   Kapanış Zamanı (UTC)   :  {_utc_simdi():<30}   ║")
    print("    ║   Kapanış Nedeni         :  Operatör İsteği (Ctrl+C)        ║")
    print("    ║   Durum                  :  GÜVENLİ KAPANIŞ ✓              ║")
    print("    ║                                                                ║")
    print("    ╚════════════════════════════════════════════════════════════════╝")
    print(f"{R_SIFIRLA}")
    print(f"  {R_DIM}  Solaris-Network Daemon kapatıldı. Tüm veriler korunmuştur.{R_SIFIRLA}")
    print(f"  {R_DIM}  Yeniden başlatmak için: python solaris_baslat.py{R_SIFIRLA}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANA DAEMON DÖNGÜSÜ
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Solaris-Network Ana Orkestratörü.
    'while True' döngüsüyle 7/24 sürekli çalışır.

    Her döngüde:
        1. zeka_merkezi.calistir() → Veri çekme + analiz + DB kayıt + rapor
        2. aksiyon_merkezi.kriz_protokollerini_denetle(rapor) → Kriz tetikleme
        3. Geri sayım → Sonraki döngüyü bekle

    Ctrl+C ile zarif kapanma (graceful shutdown) desteklenir.
    """
    # ── Muhteşem açılış ekranını göster ──
    acilis_ekranini_goster()

    dongu_sayisi = 0

    try:
        while True:
            dongu_sayisi += 1
            dongu_baslangic = time.time()

            # ── Döngü başlığı ──
            dongu_baslik_yazdir(dongu_sayisi)

            try:
                # ════════════════════════════════════════════════════
                #  ADIM 1 & 2: Veri Toplama + Zeka Analizi
                #  (zeka_merkezi.calistir() Faz 1'i de çağırır)
                # ════════════════════════════════════════════════════
                _log("ORKESTRA", "═══ Faz 1+2: Veri Toplama & Zeka Analizi başlatılıyor ═══")
                analiz_raporu = zeka_motoru_calistir()

                if not analiz_raporu:
                    _log("HATA", "Zeka Merkezi boş rapor döndürdü! Döngü atlanıyor.")
                    _log("UYARI", f"Sonraki deneme {DONGU_ARALIGI_SANIYE} saniye sonra...")
                    geri_sayim(DONGU_ARALIGI_SANIYE)
                    continue

                # ════════════════════════════════════════════════════
                #  ADIM 3: Kriz Protokol Denetimi
                # ════════════════════════════════════════════════════
                _log("ORKESTRA", "═══ Faz 3: Aksiyon Merkezi Kriz Denetimi başlatılıyor ═══")
                kriz_sonuc = kriz_protokollerini_denetle(analiz_raporu)

            except Exception as hata:
                _log("HATA", f"Döngü #{dongu_sayisi} sırasında beklenmeyen hata!")
                _log("HATA", f"  Hata detayı: {hata}")
                _log("HATA", f"  Traceback:\n{traceback.format_exc()}")

                # Hata durumunda bile döngüyü devam ettir (dayanıklılık)
                analiz_raporu = {}
                kriz_sonuc = {"kriz_tetiklendi": False}

            # ── Döngü süresi hesapla ──
            dongu_suresi = time.time() - dongu_baslangic

            # ── Döngü özeti ──
            dongu_ozet_yazdir(dongu_sayisi, analiz_raporu, kriz_sonuc, dongu_suresi)

            # ── Geri sayım ile bekleme ──
            _log("DAEMON", f"Sonraki tarama {DONGU_ARALIGI_SANIYE} saniye sonra başlayacak...")
            geri_sayim(DONGU_ARALIGI_SANIYE)

    except KeyboardInterrupt:
        # ── Zarif kapanma (Graceful Shutdown) ──
        kapanis_ekranini_goster(dongu_sayisi)
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODÜL GİRİŞ NOKTASI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
