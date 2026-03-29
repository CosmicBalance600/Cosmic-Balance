"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     SOLARIS-NETWORK :: Veri Merkezi                         ║
║         Faz 2 – Çok Sensörlü Gerçek Zamanlı Uzay Havası Veri Motoru       ║
║                                                                            ║
║  Yazar   : Solaris Mühendislik Ekibi                                       ║
║  Sürüm   : 2.0.0                                                          ║
║  Açıklama : NOAA/SWPC uydu API'lerinden güneş rüzgarı plazma,             ║
║             manyetik alan, Kp İndeksi (jeomanyetik fırtına) ve             ║
║             GOES X-Ray (güneş patlaması) verilerini çeker, temizler        ║
║             ve NASA standartlarında sınıflandırarak birleştirir.            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import time
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Merkezi Konfigürasyon ──
from config import (
    PLAZMA_API_URL, MANYETIK_API_URL, KP_INDEKSI_API_URL,
    XRAY_FLARE_API_URL, PROTON_FLUX_API_URL,
    MAKS_DENEME_SAYISI, BEKLEME_SURESI_SANIYE,
    ISTEK_ZAMAN_ASIMI, KP_XRAY_ZAMAN_ASIMI,
    RENK_KIRMIZI, RENK_YESIL, RENK_SARI, RENK_MAVI,
    RENK_CYAN, RENK_PARLAK, RENK_SIFIRLA,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

def _zaman_damgasi():
    """
    Şu anki UTC zamanını ISO 8601 formatında döndürür.
    Loglama ve veri paketinde zaman damgası olarak kullanılır.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(seviye: str, mesaj: str):
    """
    Formatlı terminal log çıktısı üretir.
    Seviyeye göre renklendirilmiş mesajlar yazdırır:
      - BİLGİ  : Yeşil   (Başarılı işlemler)
      - UYARI  : Sarı    (Uyarılar, yeniden denemeler)
      - HATA   : Kırmızı (Kritik hatalar)
      - SİSTEM : Mavi    (Sistem durumu mesajları)
    """
    renk_haritasi = {
        "BİLGİ":  RENK_YESIL,
        "UYARI":  RENK_SARI,
        "HATA":   RENK_KIRMIZI,
        "SİSTEM": RENK_MAVI,
    }
    renk = renk_haritasi.get(seviye, RENK_SIFIRLA)
    zaman = _zaman_damgasi()
    print(f"{RENK_CYAN}[{zaman}]{RENK_SIFIRLA} {renk}{RENK_PARLAK}[{seviye}]{RENK_SIFIRLA} {mesaj}")


# ═══════════════════════════════════════════════════════════════════════════════
#  VERİ ÇEKME KATMANI (Data Fetching Layer)
# ═══════════════════════════════════════════════════════════════════════════════

def guvenli_veri_cek(api_url: str, veri_adi: str) -> list | None:
    """
    Belirtilen API adresinden veri çeker.
    Hata durumunda otomatik yeniden deneme mekanizması devreye girer.

    Parametreler:
        api_url  : Veri çekilecek API'nin tam URL adresi
        veri_adi : Log mesajlarında kullanılacak veri kaynağı adı

    Dönüş:
        list : Başarılı ise API'den gelen JSON verisi (liste formatında)
        None : Tüm denemeler başarısız olursa None döner
    """
    for deneme in range(1, MAKS_DENEME_SAYISI + 1):
        try:
            _log("BİLGİ", f"'{veri_adi}' verisi çekiliyor... (Deneme {deneme}/{MAKS_DENEME_SAYISI})")

            yanit = requests.get(
                api_url,
                timeout=ISTEK_ZAMAN_ASIMI,
                headers={
                    "User-Agent": "Solaris-Network/1.0 (Space Weather Early Warning System)",
                    "Accept": "application/json",
                }
            )

            # HTTP durum kodunu kontrol et
            yanit.raise_for_status()

            # JSON çözümleme
            veri = yanit.json()

            # Verinin geçerli bir liste olup olmadığını doğrula
            if not isinstance(veri, list) or len(veri) < 2:
                raise ValueError(f"API'den dönen veri beklenen formatta değil (satır sayısı: {len(veri) if isinstance(veri, list) else 'N/A'})")

            _log("BİLGİ", f"'{veri_adi}' verisi başarıyla alındı. ({len(veri) - 1} kayıt)")
            return veri

        except requests.exceptions.HTTPError as http_hatasi:
            _log("UYARI", f"[SİSTEM UYARISI] '{veri_adi}' – HTTP Hatası: {http_hatasi.response.status_code}. "
                          f"Bağlantı koptu, {BEKLEME_SURESI_SANIYE} saniye içinde tekrar deneniyor...")

        except requests.exceptions.ConnectionError:
            _log("UYARI", f"[SİSTEM UYARISI] '{veri_adi}' – Bağlantı kurulamadı. "
                          f"Bağlantı koptu, {BEKLEME_SURESI_SANIYE} saniye içinde tekrar deneniyor...")

        except requests.exceptions.Timeout:
            _log("UYARI", f"[SİSTEM UYARISI] '{veri_adi}' – İstek zaman aşımına uğradı ({ISTEK_ZAMAN_ASIMI}s). "
                          f"Bağlantı koptu, {BEKLEME_SURESI_SANIYE} saniye içinde tekrar deneniyor...")

        except (json.JSONDecodeError, ValueError) as veri_hatasi:
            _log("UYARI", f"[SİSTEM UYARISI] '{veri_adi}' – Veri ayrıştırma hatası: {veri_hatasi}. "
                          f"Bağlantı koptu, {BEKLEME_SURESI_SANIYE} saniye içinde tekrar deneniyor...")

        except Exception as genel_hata:
            _log("UYARI", f"[SİSTEM UYARISI] '{veri_adi}' – Beklenmeyen hata: {genel_hata}. "
                          f"Bağlantı koptu, {BEKLEME_SURESI_SANIYE} saniye içinde tekrar deneniyor...")

        # Son deneme değilse bekle
        if deneme < MAKS_DENEME_SAYISI:
            time.sleep(BEKLEME_SURESI_SANIYE)

    # Tüm denemeler başarısız
    _log("HATA", f"'{veri_adi}' verisi {MAKS_DENEME_SAYISI} deneme sonrasında alınamadı! Kaynak atlanıyor.")
    return None


def kp_indeksi_cek() -> dict | None:
    """
    NOAA Planetary Kp İndeksi verisini çeker ve NOAA G-Scale fırtına
    sınıflandırmasını hesaplar.

    Kaynak : https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json
    Format : JSON listesi – her satır [zaman, Kp, Kp_fraksiyon, a_beklenen, durum]

    G-Scale Sınıflandırma (NOAA Resmi Standart):
        Kp < 5  → G0 (Fırtına yok)
        Kp = 5  → G1 (Minor – Küçük Fırtına)
        Kp = 6  → G2 (Moderate – Orta Fırtına)
        Kp = 7  → G3 (Strong – Güçlü Fırtına)
        Kp = 8  → G4 (Severe – Şiddetli Fırtına)
        Kp ≥ 9  → G5 (Extreme – Aşırı Fırtına)

    Dayanıklılık: 3 denemelik retry döngüsü, 2 saniye bekleme aralığı.

    Dönüş:
        dict : Kp değeri, G-Scale sınıfı ve açıklama içeren sözlük
        None : Tüm denemeler başarısız ise None (sistem çalışmaya devam eder)
    """
    MAKS_DENEME = 3
    BEKLEME_SURESI = 2  # saniye

    for deneme in range(1, MAKS_DENEME + 1):
        try:
            if deneme == 1:
                _log("BİLGİ", "Kp İndeksi verisi çekiliyor (NOAA Planetary K-Index)...")
            else:
                _log("UYARI", f"Kp İndeksi – Yeniden deneniyor ({deneme}/{MAKS_DENEME})...")

            yanit = requests.get(
                KP_INDEKSI_API_URL,
                timeout=KP_XRAY_ZAMAN_ASIMI,
                headers={
                    "User-Agent": "Solaris-Network/2.0 (Space Weather Early Warning System)",
                    "Accept": "application/json",
                }
            )
            yanit.raise_for_status()
            veri = yanit.json()

            if not isinstance(veri, list) or len(veri) < 2:
                raise ValueError(f"Kp verisi beklenen formatta değil (kayıt: {len(veri) if isinstance(veri, list) else 'N/A'})")

            # Son geçerli kaydı al (ilk satır başlık)
            son_kayit = veri[-1]
            zaman_damgasi = son_kayit[0] if len(son_kayit) > 0 else None

            # Kp değerini çıkar (indeks 1 = Kp değeri)
            kp_raw = son_kayit[1] if len(son_kayit) > 1 else None
            kp_deger = float(kp_raw) if kp_raw is not None else None

            if kp_deger is None:
                raise ValueError("Kp değeri çözümlenemedi")

            # ── NOAA G-Scale Fırtına Sınıflandırması ──
            g_scale_tablo = [
                (9, "G5", "Extreme – Aşırı Jeomagnetik Fırtına"),
                (8, "G4", "Severe – Şiddetli Jeomagnetik Fırtına"),
                (7, "G3", "Strong – Güçlü Jeomagnetik Fırtına"),
                (6, "G2", "Moderate – Orta Seviye Jeomagnetik Fırtına"),
                (5, "G1", "Minor – Küçük Jeomagnetik Fırtına"),
            ]

            firtina_sinifi = "G0"
            firtina_aciklamasi = "Fırtına yok – Normal jeomagnetik koşullar"

            for esik, sinif, aciklama in g_scale_tablo:
                if kp_deger >= esik:
                    firtina_sinifi = sinif
                    firtina_aciklamasi = aciklama
                    break

            sonuc = {
                "zaman_damgasi": zaman_damgasi,
                "kp_degeri": round(kp_deger, 2),
                "firtina_sinifi": firtina_sinifi,
                "firtina_aciklamasi": firtina_aciklamasi,
            }

            _log("BİLGİ", f"Kp İndeksi başarıyla alındı: Kp={kp_deger:.2f} → {firtina_sinifi} ✓")
            return sonuc

        except requests.exceptions.Timeout:
            _log("UYARI", f"Kp İndeksi API zaman aşımı ({KP_XRAY_ZAMAN_ASIMI}s) – Deneme {deneme}/{MAKS_DENEME}")
        except requests.exceptions.ConnectionError:
            _log("UYARI", f"Kp İndeksi API bağlantı hatası – Deneme {deneme}/{MAKS_DENEME}")
        except requests.exceptions.HTTPError as http_hatasi:
            _log("UYARI", f"Kp İndeksi API HTTP hatası: {http_hatasi.response.status_code} – Deneme {deneme}/{MAKS_DENEME}")
        except (ValueError, TypeError, IndexError, KeyError) as veri_hatasi:
            _log("UYARI", f"Kp İndeksi veri ayrıştırma hatası: {veri_hatasi}")
            break  # Veri format hatasında retry anlamsız
        except Exception as genel_hata:
            _log("HATA", f"Kp İndeksi beklenmeyen hata: {genel_hata} – Deneme {deneme}/{MAKS_DENEME}")

        # Son deneme değilse bekle - Bug #14 düzeltildi
        if deneme < MAKS_DENEME:
            time.sleep(BEKLEME_SURESI)

    _log("UYARI", f"Kp İndeksi {MAKS_DENEME} denemede de alınamadı. Kaynak atlanıyor.")
    return None


def xray_flare_cek() -> dict | None:
    """
    GOES uydusu X-Ray (0.1-0.8nm) akı verisini çeker ve Güneş Patlaması
    (Solar Flare) sınıflandırmasını bilimsel formata göre hesaplar.

    Kaynak : https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json
    Format : JSON listesi – her obje {time_tag, satellite, energy, flux} içerir
    Filtre : Sadece "0.1-0.8nm" dalga boyundaki kayıtlar kullanılır

    Solar Flare Sınıflandırması (Bilimsel Standart – GOES X-Ray Flux):
        flux ≥ 1e-4 W/m² → X-Class (En Şiddetli)
        flux ≥ 1e-5 W/m² → M-Class (Güçlü)
        flux ≥ 1e-6 W/m² → C-Class (Orta)
        flux ≥ 1e-7 W/m² → B-Class (Küçük)
        flux <  1e-7 W/m² → A-Class (Çok Küçük)

    Dayanıklılık: 3 denemelik retry döngüsü, 2 saniye bekleme aralığı.

    Dönüş:
        dict : X-Ray akı değeri, flare sınıfı ve dalga boyu bilgisi
        None : Tüm denemeler başarısız ise None (sistem çalışmaya devam eder)
    """
    MAKS_DENEME = 3
    BEKLEME_SURESI = 2  # saniye

    for deneme in range(1, MAKS_DENEME + 1):
        try:
            if deneme == 1:
                _log("BİLGİ", "X-Ray Solar Flare verisi çekiliyor (GOES Primary)...")
            else:
                _log("UYARI", f"X-Ray – Yeniden deneniyor ({deneme}/{MAKS_DENEME})...")

            yanit = requests.get(
                XRAY_FLARE_API_URL,
                timeout=KP_XRAY_ZAMAN_ASIMI,
                headers={
                    "User-Agent": "Solaris-Network/2.0 (Space Weather Early Warning System)",
                    "Accept": "application/json",
                }
            )
            yanit.raise_for_status()
            veri = yanit.json()

            if not isinstance(veri, list) or len(veri) == 0:
                raise ValueError(f"X-Ray verisi beklenen formatta değil (kayıt: {len(veri) if isinstance(veri, list) else 'N/A'})")

            # ── 0.1-0.8nm dalga boyundaki en son kaydı filtrele ──
            hedef_kayit = None
            for kayit in reversed(veri):
                enerji = kayit.get("energy", "")
                if "0.1-0.8" in str(enerji):
                    flux_deger = kayit.get("flux")
                    if flux_deger is not None:
                        try:
                            float(flux_deger)
                            hedef_kayit = kayit
                            break
                        except (ValueError, TypeError):
                            continue

            if hedef_kayit is None:
                raise ValueError("0.1-0.8nm dalga boyunda geçerli bir X-Ray kaydı bulunamadı")

            flux = float(hedef_kayit["flux"])
            zaman_damgasi = hedef_kayit.get("time_tag", None)

            # ── Solar Flare Sınıflandırması ──
            flare_tablo = [
                (1e-4, "X-Class", "Aşırı Şiddetli Güneş Patlaması – Radyo karartması, uydu hasarı riski"),
                (1e-5, "M-Class", "Güçlü Güneş Patlaması – Kutup bölgelerinde radyo kesintisi"),
                (1e-6, "C-Class", "Orta Seviye Güneş Patlaması – Düşük radyo etkisi"),
                (1e-7, "B-Class", "Küçük Güneş Patlaması – Minimal etki"),
            ]

            flare_sinifi = "A-Class"
            flare_aciklamasi = "Çok Küçük Güneş Patlaması – Ölçülebilir etki yok"

            for esik, sinif, aciklama in flare_tablo:
                if flux >= esik:
                    flare_sinifi = sinif
                    flare_aciklamasi = aciklama
                    break

            sonuc = {
                "zaman_damgasi": zaman_damgasi,
                "xray_flux_W_m2": flux,
                "flare_sinifi": flare_sinifi,
                "flare_aciklamasi": flare_aciklamasi,
                "dalga_boyu_nm": "0.1-0.8",
            }

            _log("BİLGİ", f"X-Ray verisi başarıyla alındı: flux={flux:.2e} → {flare_sinifi} ✓")
            return sonuc

        except requests.exceptions.Timeout:
            _log("UYARI", f"X-Ray API zaman aşımı ({KP_XRAY_ZAMAN_ASIMI}s) – Deneme {deneme}/{MAKS_DENEME}")
        except requests.exceptions.ConnectionError:
            _log("UYARI", f"X-Ray API bağlantı hatası – Deneme {deneme}/{MAKS_DENEME}")
        except requests.exceptions.HTTPError as http_hatasi:
            _log("UYARI", f"X-Ray API HTTP hatası: {http_hatasi.response.status_code} – Deneme {deneme}/{MAKS_DENEME}")
        except (ValueError, TypeError, IndexError, KeyError) as veri_hatasi:
            _log("UYARI", f"X-Ray veri ayrıştırma hatası: {veri_hatasi}")
            break  # Veri format hatasında retry anlamsız
        except Exception as genel_hata:
            _log("HATA", f"X-Ray beklenmeyen hata: {genel_hata} – Deneme {deneme}/{MAKS_DENEME}")

        # Son deneme değilse bekle - Bug #14 düzeltildi
        if deneme < MAKS_DENEME:
            time.sleep(BEKLEME_SURESI)

    _log("UYARI", f"X-Ray verisi {MAKS_DENEME} denemede de alınamadı. Kaynak atlanıyor.")
    return None


def proton_flux_cek() -> dict | None:
    """
    NOAA GOES uydusu ≥10 MeV integral proton akısı verisini çeker ve
    NOAA S-Scale (Solar Radiation Storm) sınıflandırmasını hesaplar.

    Kaynak : https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json
    Format : JSON listesi – her obje {time_tag, satellite, flux, energy} içerir
    Filtre : Sadece ">=10 MeV" enerji bandındaki kayıtlar kullanılır

    S-Scale Sınıflandırma (NOAA Resmi Standart – Proton Flux Units, pfu):
        flux ≥ 100000 pfu → S5 (Extreme – Aşırı Radyasyon Fırtınası)
        flux ≥ 10000  pfu → S4 (Severe – Şiddetli Radyasyon Fırtınası)
        flux ≥ 1000   pfu → S3 (Strong – Güçlü Radyasyon Fırtınası)
        flux ≥ 100    pfu → S2 (Moderate – Orta Radyasyon Fırtınası)
        flux ≥ 10     pfu → S1 (Minor – Küçük Radyasyon Fırtınası)
        flux < 10     pfu → S0 (Fırtına yok – Normal radyasyon seviyesi)

    Dayanıklılık: 3 denemelik retry döngüsü, 2 saniye bekleme aralığı.

    Dönüş:
        dict : Proton akısı değeri, S-Scale sınıfı ve açıklama içeren sözlük
        None : Tüm denemeler başarısız ise None (sistem çalışmaya devam eder)
    """
    MAKS_DENEME = 3
    BEKLEME_SURESI = 2  # saniye

    for deneme in range(1, MAKS_DENEME + 1):
        try:
            if deneme == 1:
                _log("BİLGİ", "Proton Flux verisi çekiliyor (GOES ≥10 MeV Integral Protons)...")
            else:
                _log("UYARI", f"Proton Flux – Yeniden deneniyor ({deneme}/{MAKS_DENEME})...")

            yanit = requests.get(
                PROTON_FLUX_API_URL,
                timeout=KP_XRAY_ZAMAN_ASIMI,
                headers={
                    "User-Agent": "Solaris-Network/2.0 (Space Weather Early Warning System)",
                    "Accept": "application/json",
                }
            )
            yanit.raise_for_status()
            veri = yanit.json()

            if not isinstance(veri, list) or len(veri) == 0:
                raise ValueError(f"Proton verisi beklenen formatta değil (kayıt: {len(veri) if isinstance(veri, list) else 'N/A'})")

            # ── >=10 MeV enerji bandındaki en son kaydı filtrele ──
            hedef_kayit = None
            for kayit in reversed(veri):
                enerji = kayit.get("energy", "")
                if "10" in str(enerji) and "MeV" in str(enerji):
                    flux_deger = kayit.get("flux")
                    if flux_deger is not None:
                        try:
                            float(flux_deger)
                            hedef_kayit = kayit
                            break
                        except (ValueError, TypeError):
                            continue

            if hedef_kayit is None:
                raise ValueError("≥10 MeV enerji bandında geçerli bir Proton kaydı bulunamadı")

            flux = float(hedef_kayit["flux"])
            zaman_damgasi = hedef_kayit.get("time_tag", None)

            # ── NOAA S-Scale Radyasyon Fırtınası Sınıflandırması ──
            s_scale_tablo = [
                (100000, "S5", "Extreme – Aşırı Radyasyon Fırtınası – Astronot tehlikesi, uydu kaybı riski"),
                (10000,  "S4", "Severe – Şiddetli Radyasyon – Yörünge elektroniğinde ciddi arıza riski"),
                (1000,   "S3", "Strong – Güçlü Radyasyon – Uydu bellek bozulması, kutup radyo karartması"),
                (100,    "S2", "Moderate – Orta Radyasyon – Yüksek enlem uçuşlarında doz artışı"),
                (10,     "S1", "Minor – Küçük Radyasyon – Kutup bölgelerinde HF radyo bozulması"),
            ]

            radyasyon_sinifi = "S0"
            radyasyon_aciklamasi = "Fırtına yok – Normal radyasyon seviyesi"

            for esik, sinif, aciklama in s_scale_tablo:
                if flux >= esik:
                    radyasyon_sinifi = sinif
                    radyasyon_aciklamasi = aciklama
                    break

            sonuc = {
                "zaman_damgasi": zaman_damgasi,
                "proton_flux_pfu": flux,
                "radyasyon_sinifi": radyasyon_sinifi,
                "radyasyon_aciklamasi": radyasyon_aciklamasi,
                "enerji_bandi": ">=10 MeV",
            }

            _log("BİLGİ", f"Proton Flux başarıyla alındı: flux={flux:.2f} pfu → {radyasyon_sinifi} ✓")
            return sonuc

        except requests.exceptions.Timeout:
            _log("UYARI", f"Proton Flux API zaman aşımı ({KP_XRAY_ZAMAN_ASIMI}s) – Deneme {deneme}/{MAKS_DENEME}")
        except requests.exceptions.ConnectionError:
            _log("UYARI", f"Proton Flux API bağlantı hatası – Deneme {deneme}/{MAKS_DENEME}")
        except requests.exceptions.HTTPError as http_hatasi:
            _log("UYARI", f"Proton Flux API HTTP hatası: {http_hatasi.response.status_code} – Deneme {deneme}/{MAKS_DENEME}")
        except (ValueError, TypeError, IndexError, KeyError) as veri_hatasi:
            _log("UYARI", f"Proton Flux veri ayrıştırma hatası: {veri_hatasi}")
            break  # Veri format hatasında retry anlamsız
        except Exception as genel_hata:
            _log("HATA", f"Proton Flux beklenmeyen hata: {genel_hata} – Deneme {deneme}/{MAKS_DENEME}")

        # Son deneme değilse bekle
        if deneme < MAKS_DENEME:
            time.sleep(BEKLEME_SURESI)

    _log("UYARI", f"Proton Flux verisi {MAKS_DENEME} denemede de alınamadı. Kaynak atlanıyor.")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  VERİ TEMİZLEME KATMANI (Data Cleaning Layer)
# ═══════════════════════════════════════════════════════════════════════════════

def _guvenli_float(deger) -> float | None:
    """
    Bir değeri güvenli bir şekilde float tipine dönüştürür.
    Dönüştürme başarısız olursa (None, boş string, geçersiz değer) None döner.

    Bu fonksiyon API'den gelen bozuk veya eksik verileri zararsız hale getirir.
    """
    if deger is None:
        return None
    try:
        sonuc = float(deger)
        return sonuc
    except (ValueError, TypeError):
        return None


def plazma_verisini_temizle(ham_veri: list) -> dict:
    """
    NOAA Plazma API'sinden gelen ham veriyi temizler ve yapılandırır.

    Ham veri formatı (ilk satır başlık):
        [zaman_damgasi, yoğunluk, hız, sıcaklık]

    Dönüş:
        dict: Temizlenmiş plazma verisi sözlüğü
            - zaman_damgasi : Son ölçümün zaman bilgisi
            - yogunluk_p_cc : Plazma yoğunluğu (parçacık/cm³)
            - hiz_km_s      : Güneş rüzgarı hızı (km/s)
            - sicaklik_K    : Plazma sıcaklığı (Kelvin)
    """
    # Son geçerli veri kaydını bul (en güncel olan)
    son_kayit = None
    for kayit in reversed(ham_veri[1:]):  # İlk satır başlık, onu atla
        yogunluk = _guvenli_float(kayit[1])
        hiz = _guvenli_float(kayit[2])
        # En az biri geçerli ise bu kaydı kullan
        if yogunluk is not None or hiz is not None:
            son_kayit = kayit
            break

    if son_kayit is None:
        _log("UYARI", "Plazma verisinde geçerli bir kayıt bulunamadı, son satır kullanılıyor.")
        son_kayit = ham_veri[-1]

    return {
        "zaman_damgasi": son_kayit[0],
        "yogunluk_p_cc": _guvenli_float(son_kayit[1]),
        "hiz_km_s": _guvenli_float(son_kayit[2]),
        "sicaklik_K": _guvenli_float(son_kayit[3]) if len(son_kayit) > 3 else None,
    }


def manyetik_verisini_temizle(ham_veri: list) -> dict:
    """
    NOAA Manyetik Alan API'sinden gelen ham veriyi temizler ve yapılandırır.

    Ham veri formatı (ilk satır başlık):
        [zaman_damgasi, bx_gsm, by_gsm, bz_gsm, lon_gsm, lat_gsm, bt]

    Dönüş:
        dict: Temizlenmiş manyetik alan verisi sözlüğü
            - zaman_damgasi : Son ölçümün zaman bilgisi
            - bt_nT         : Toplam manyetik alan gücü (nanoTesla)
            - bz_gsm_nT     : Manyetik alanın Bz bileşeni (nanoTesla)
            - bx_gsm_nT     : Manyetik alanın Bx bileşeni (nanoTesla)
            - by_gsm_nT     : Manyetik alanın By bileşeni (nanoTesla)
    """
    # Son geçerli veri kaydını bul (en güncel olan)
    son_kayit = None
    for kayit in reversed(ham_veri[1:]):  # İlk satır başlık, onu atla
        bt = _guvenli_float(kayit[6]) if len(kayit) > 6 else None
        bz = _guvenli_float(kayit[3]) if len(kayit) > 3 else None
        # En az biri geçerli ise bu kaydı kullan
        if bt is not None or bz is not None:
            son_kayit = kayit
            break

    if son_kayit is None:
        _log("UYARI", "Manyetik veride geçerli bir kayıt bulunamadı, son satır kullanılıyor.")
        son_kayit = ham_veri[-1]

    return {
        "zaman_damgasi": son_kayit[0],
        "bt_nT": _guvenli_float(son_kayit[6]) if len(son_kayit) > 6 else None,
        "bz_gsm_nT": _guvenli_float(son_kayit[3]) if len(son_kayit) > 3 else None,
        "bx_gsm_nT": _guvenli_float(son_kayit[1]) if len(son_kayit) > 1 else None,
        "by_gsm_nT": _guvenli_float(son_kayit[2]) if len(son_kayit) > 2 else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  VERİ BİRLEŞTİRME KATMANI (Data Fusion Layer)
# ═══════════════════════════════════════════════════════════════════════════════

def master_veri_paketi_olustur(
    plazma: dict | None,
    manyetik: dict | None,
    kp_verisi: dict | None = None,
    xray_verisi: dict | None = None,
    proton_verisi: dict | None = None,
) -> dict:
    """
    Tüm sensör verilerini (Plazma, Manyetik, Kp İndeksi, X-Ray, Proton Flux)
    tek bir master veri paketinde birleştirir. Herhangi bir kaynaktan veri
    alınamasa bile sistem çalışmaya devam eder (graceful degradation).

    Parametreler:
        plazma        : Temizlenmiş plazma verisi sözlüğü veya None
        manyetik      : Temizlenmiş manyetik alan verisi sözlüğü veya None
        kp_verisi     : Kp İndeksi verisi sözlüğü veya None
        xray_verisi   : X-Ray Solar Flare verisi sözlüğü veya None
        proton_verisi : Proton Flux (≥10 MeV) verisi sözlüğü veya None

    Dönüş:
        dict: Birleştirilmiş master veri paketi (5 sensör)
    """
    # Veri kaynağı durumlarını belirle
    plazma_durumu = "AKTIF" if plazma is not None else "DEVRE_DISI"
    manyetik_durumu = "AKTIF" if manyetik is not None else "DEVRE_DISI"
    kp_durumu = "AKTIF" if kp_verisi is not None else "DEVRE_DISI"
    xray_durumu = "AKTIF" if xray_verisi is not None else "DEVRE_DISI"
    proton_durumu = "AKTIF" if proton_verisi is not None else "DEVRE_DISI"

    # Genel sistem durumunu hesapla (5 kaynak)
    aktif_kaynaklar = [plazma_durumu, manyetik_durumu, kp_durumu, xray_durumu, proton_durumu]
    aktif_sayisi = aktif_kaynaklar.count("AKTIF")

    if aktif_sayisi == 5:
        sistem_durumu = "TAM_OPERASYONEL"
    elif aktif_sayisi >= 1:
        sistem_durumu = "KISMI_OPERASYONEL"
    else:
        sistem_durumu = "VERİ_YOK"

    master_paket = {
        "sistem_bilgisi": {
            "motor_adi": "Solaris-Network Veri Motoru",
            "surum": "3.0.0",
            "olusturma_zamani_utc": _zaman_damgasi(),
            "sistem_durumu": sistem_durumu,
            "aktif_sensor_sayisi": f"{aktif_sayisi}/5",
            "veri_kaynaklari": {
                "plazma_api": plazma_durumu,
                "manyetik_api": manyetik_durumu,
                "kp_indeksi_api": kp_durumu,
                "xray_flare_api": xray_durumu,
                "proton_flux_api": proton_durumu,
            }
        },
        "gunes_ruzgari": {
            "plazma": plazma if plazma else {
                "zaman_damgasi": None,
                "yogunluk_p_cc": None,
                "hiz_km_s": None,
                "sicaklik_K": None,
            },
            "manyetik_alan": manyetik if manyetik else {
                "zaman_damgasi": None,
                "bt_nT": None,
                "bz_gsm_nT": None,
                "bx_gsm_nT": None,
                "by_gsm_nT": None,
            }
        },
        "jeomanyetik_durum": kp_verisi if kp_verisi else {
            "zaman_damgasi": None,
            "kp_degeri": None,
            "firtina_sinifi": "N/A",
            "firtina_aciklamasi": "Veri alınamadı",
        },
        "gunes_patlamasi": xray_verisi if xray_verisi else {
            "zaman_damgasi": None,
            "xray_flux_W_m2": None,
            "flare_sinifi": "N/A",
            "flare_aciklamasi": "Veri alınamadı",
            "dalga_boyu_nm": "0.1-0.8",
        },
        "radyasyon_durumu": proton_verisi if proton_verisi else {
            "zaman_damgasi": None,
            "proton_flux_pfu": None,
            "radyasyon_sinifi": "N/A",
            "radyasyon_aciklamasi": "Veri alınamadı",
            "enerji_bandi": ">=10 MeV",
        },
    }

    return master_paket


# ═══════════════════════════════════════════════════════════════════════════════
#  PARALEL VERİ TOPLAMA (Concurrent Data Collection)
# ═══════════════════════════════════════════════════════════════════════════════

def verileri_paralel_topla() -> tuple:
    """
    Beş NOAA API'sinden verileri eş zamanlı (paralel) olarak toplar.
    ThreadPoolExecutor kullanarak ağ gecikmesini minimize eder.

    Paralel Görevler:
        1. Plazma API       → guvenli_veri_cek()
        2. Manyetik Alan API → guvenli_veri_cek()
        3. Kp İndeksi API   → kp_indeksi_cek()
        4. X-Ray Flare API  → xray_flare_cek()
        5. Proton Flux API  → proton_flux_cek()

    Dönüş:
        tuple: (plazma_ham, manyetik_ham, kp_verisi, xray_verisi, proton_verisi)
               Başarısız kaynaklar için None döner.
    """
    _log("SİSTEM", "Paralel veri toplama başlatılıyor (5 sensör)...")

    plazma_ham = None
    manyetik_ham = None
    kp_verisi = None
    xray_verisi = None
    proton_verisi = None

    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="solaris-veri") as havuz:
        # Beş API'ye eş zamanlı istek gönder
        gorevler = {
            havuz.submit(guvenli_veri_cek, PLAZMA_API_URL, "Plazma"): "plazma",
            havuz.submit(guvenli_veri_cek, MANYETIK_API_URL, "Manyetik Alan"): "manyetik",
            havuz.submit(kp_indeksi_cek): "kp",
            havuz.submit(xray_flare_cek): "xray",
            havuz.submit(proton_flux_cek): "proton",
        }

        for tamamlanan in as_completed(gorevler):
            kaynak = gorevler[tamamlanan]
            try:
                sonuc = tamamlanan.result()
                if kaynak == "plazma":
                    plazma_ham = sonuc
                elif kaynak == "manyetik":
                    manyetik_ham = sonuc
                elif kaynak == "kp":
                    kp_verisi = sonuc
                elif kaynak == "xray":
                    xray_verisi = sonuc
                elif kaynak == "proton":
                    proton_verisi = sonuc
            except Exception as hata:
                _log("HATA", f"'{kaynak}' görev hatası: {hata}")

    return plazma_ham, manyetik_ham, kp_verisi, xray_verisi, proton_verisi


# ═══════════════════════════════════════════════════════════════════════════════
#  SONUÇ GÖRÜNTÜLEME (Result Display)
# ═══════════════════════════════════════════════════════════════════════════════

def master_paketi_yazdir(paket: dict):
    """
    Birleştirilmiş master veri paketini terminal ekranında
    renkli ve düzenli JSON formatında görüntüler.
    """
    ayirici = "═" * 72
    print()
    print(f"{RENK_CYAN}{RENK_PARLAK}╔{ayirici}╗{RENK_SIFIRLA}")
    print(f"{RENK_CYAN}{RENK_PARLAK}║{'SOLARIS-NETWORK :: Master Veri Paketi':^72}║{RENK_SIFIRLA}")
    print(f"{RENK_CYAN}{RENK_PARLAK}╚{ayirici}╝{RENK_SIFIRLA}")
    print()

    # JSON çıktısını güzelleştirilmiş formatta yazdır
    json_cikti = json.dumps(paket, indent=4, ensure_ascii=False)
    print(f"{RENK_YESIL}{json_cikti}{RENK_SIFIRLA}")

    print()
    print(f"{RENK_CYAN}{RENK_PARLAK}{'─' * 74}{RENK_SIFIRLA}")

    # Durum özetini yazdır
    durum = paket["sistem_bilgisi"]["sistem_durumu"]
    sensor = paket["sistem_bilgisi"].get("aktif_sensor_sayisi", "?/4")
    durum_renk = {
        "TAM_OPERASYONEL": RENK_YESIL,
        "KISMI_OPERASYONEL": RENK_SARI,
        "VERİ_YOK": RENK_KIRMIZI,
    }.get(durum, RENK_SIFIRLA)

    print(f"  {RENK_PARLAK}Sistem Durumu : {durum_renk}{durum}{RENK_SIFIRLA} ({sensor} sensör aktif)")

    # Hızlı özet bilgileri yazdır – Güneş Rüzgarı
    plazma = paket["gunes_ruzgari"]["plazma"]
    mag = paket["gunes_ruzgari"]["manyetik_alan"]

    hiz = plazma.get("hiz_km_s")
    yogunluk = plazma.get("yogunluk_p_cc")
    bt = mag.get("bt_nT")
    bz = mag.get("bz_gsm_nT")

    print(f"  {RENK_PARLAK}Rüzgar Hızı   : {RENK_SIFIRLA}{hiz if hiz is not None else 'N/A'} km/s")
    print(f"  {RENK_PARLAK}Yoğunluk      : {RENK_SIFIRLA}{yogunluk if yogunluk is not None else 'N/A'} p/cm³")
    print(f"  {RENK_PARLAK}Bt (Toplam)   : {RENK_SIFIRLA}{bt if bt is not None else 'N/A'} nT")
    print(f"  {RENK_PARLAK}Bz (Yön)      : {RENK_SIFIRLA}{bz if bz is not None else 'N/A'} nT")

    print(f"{RENK_CYAN}{RENK_PARLAK}{'─' * 74}{RENK_SIFIRLA}")

    # Kp İndeksi özeti
    kp = paket.get("jeomanyetik_durum", {})
    kp_deger = kp.get("kp_degeri")
    kp_sinif = kp.get("firtina_sinifi", "N/A")
    kp_renk = RENK_KIRMIZI if kp_sinif not in ("G0", "N/A") else RENK_YESIL
    print(f"  {RENK_PARLAK}Kp İndeksi    : {RENK_SIFIRLA}{kp_deger if kp_deger is not None else 'N/A'} → {kp_renk}{kp_sinif}{RENK_SIFIRLA}")

    # X-Ray Solar Flare özeti
    xray = paket.get("gunes_patlamasi", {})
    flux = xray.get("xray_flux_W_m2")
    flare_sinif = xray.get("flare_sinifi", "N/A")
    flare_renk = RENK_KIRMIZI if flare_sinif in ("X-Class", "M-Class") else RENK_SARI if flare_sinif == "C-Class" else RENK_YESIL
    flux_str = f"{flux:.2e}" if flux is not None else "N/A"
    print(f"  {RENK_PARLAK}X-Ray Flux    : {RENK_SIFIRLA}{flux_str} W/m² → {flare_renk}{flare_sinif}{RENK_SIFIRLA}")

    # Proton Flux (Radyasyon) özeti
    proton = paket.get("radyasyon_durumu", {})
    proton_flux = proton.get("proton_flux_pfu")
    rad_sinif = proton.get("radyasyon_sinifi", "N/A")
    rad_renk = RENK_KIRMIZI if rad_sinif in ("S3", "S4", "S5") else RENK_SARI if rad_sinif in ("S1", "S2") else RENK_YESIL
    proton_str = f"{proton_flux:.2f}" if proton_flux is not None else "N/A"
    print(f"  {RENK_PARLAK}Proton Flux   : {RENK_SIFIRLA}{proton_str} pfu → {rad_renk}{rad_sinif}{RENK_SIFIRLA}")

    print(f"{RENK_CYAN}{RENK_PARLAK}{'─' * 74}{RENK_SIFIRLA}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANA ÇALIŞTIRMA NOKTASI (Main Entry Point)
# ═══════════════════════════════════════════════════════════════════════════════

def calistir():
    """
    Solaris-Network Veri Motorunun ana çalıştırma fonksiyonu.
    Tüm veri toplama, temizleme, birleştirme ve görüntüleme sürecini
    baştan sona yönetir.

    Çalışma sırası:
        1. Paralel veri toplama (Plazma + Manyetik + Kp + X-Ray + Proton)
        2. Ham verileri temizleme (Plazma & Manyetik)
        3. Master veri paketi oluşturma (5 sensör birleşimi)
        4. Sonucu ekrana yazdırma
    """
    # ── Başlangıç Banneri ──
    print()
    print(f"{RENK_MAVI}{RENK_PARLAK}")
    print("    ╔═══════════════════════════════════════════════════════════╗")
    print("    ║       ☀  SOLARIS-NETWORK  ::  Veri Motoru v3.0.0        ║")
    print("    ║       Çok Sensörlü Uzay Havası Erken Uyarı Sistemi      ║")
    print("    ║  [Plazma · Manyetik · Kp İndeksi · X-Ray · Proton]    ║")
    print("    ╚═══════════════════════════════════════════════════════════╝")
    print(f"{RENK_SIFIRLA}")

    _log("SİSTEM", "Motor başlatılıyor (5 sensör modu)...")

    # ── ADIM 1: Paralel Veri Toplama (5 kaynak eş zamanlı) ──
    plazma_ham, manyetik_ham, kp_verisi, xray_verisi, proton_verisi = verileri_paralel_topla()

    # ── ADIM 2: Ham Verileri Temizleme (Plazma & Manyetik) ──
    # Not: Kp, X-Ray ve Proton fonksiyonları kendi içlerinde temizlenmiş veri döner
    _log("SİSTEM", "Veriler temizleniyor ve yapılandırılıyor...")

    temiz_plazma = None
    temiz_manyetik = None

    if plazma_ham is not None:
        try:
            temiz_plazma = plazma_verisini_temizle(plazma_ham)
            _log("BİLGİ", "Plazma verisi başarıyla temizlendi.")
        except Exception as hata:
            _log("HATA", f"Plazma verisi temizlenirken hata: {hata}")

    if manyetik_ham is not None:
        try:
            temiz_manyetik = manyetik_verisini_temizle(manyetik_ham)
            _log("BİLGİ", "Manyetik alan verisi başarıyla temizlendi.")
        except Exception as hata:
            _log("HATA", f"Manyetik alan verisi temizlenirken hata: {hata}")

    # ── ADIM 3: Master Veri Paketi Oluşturma (5 sensör birleşimi) ──
    _log("SİSTEM", "Master veri paketi oluşturuluyor (5 sensör)...")
    master_paket = master_veri_paketi_olustur(
        temiz_plazma, temiz_manyetik, kp_verisi, xray_verisi, proton_verisi
    )

    # ── ADIM 4: Sonucu Ekrana Yazdırma ──
    master_paketi_yazdir(master_paket)

    _log("SİSTEM", "Veri motoru döngüsü tamamlandı (5/5 sensör işlendi). ✓")

    return master_paket


# ═══════════════════════════════════════════════════════════════════════════════
#  MODÜL GİRİŞ NOKTASI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    calistir()
