/* ═══════════════════════════════════════════════════════════════════════════
   UZAY HAVA DURUMU ANALİZ SİSTEMİ - YAPAY ZEKA DESTEKLİ
   Güneş aktivitesi verilerini analiz eder ve risk değerlendirmesi yapar
   Gelişmiş AI tabanlı yorum ve tahmin sistemi
   ═══════════════════════════════════════════════════════════════════════════ */

// ═══════════════════════════════════════════════════════════════════════════
//  YAPAY ZEKA ANALİZ MOTORUuzay_analiz.js
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Gelişmiş AI tabanlı uzay hava durumu analizi
 * Makine öğrenmesi benzeri mantık ile risk değerlendirmesi yapar
 */
class UzayHavaAI {
    constructor() {
        this.tarihce = [];
        this.maxTarihce = 100;
        this.ogrenmeKatsayisi = 0.15;
    }

    /**
     * Veriyi tarihçeye ekle ve öğrenme sürecini güncelle
     */
    veriEkle(veri, sonuc) {
        this.tarihce.push({ veri, sonuc, zaman: Date.now() });
        if (this.tarihce.length > this.maxTarihce) {
            this.tarihce.shift();
        }
    }

    /**
     * Trend analizi yap
     */
    trendAnalizi(parametre, deger) {
        if (this.tarihce.length < 5) return 'STABIL';
        
        const sonVeriler = this.tarihce.slice(-10).map(t => t.veri[parametre] || 0);
        const ortalama = sonVeriler.reduce((a, b) => a + b, 0) / sonVeriler.length;
        
        if (deger > ortalama * 1.3) return 'HIZLI ARTIŞ';
        if (deger > ortalama * 1.1) return 'ARTIŞ';
        if (deger < ortalama * 0.7) return 'HIZLI DÜŞÜŞ';
        if (deger < ortalama * 0.9) return 'DÜŞÜŞ';
        return 'STABIL';
    }

    /**
     * Gelecek tahmini yap (basit lineer regresyon)
     */
    gelecekTahmini(parametre) {
        if (this.tarihce.length < 10) return null;
        
        const sonVeriler = this.tarihce.slice(-20).map(t => t.veri[parametre] || 0);
        const n = sonVeriler.length;
        
        // Basit trend hesaplama
        let toplamArtis = 0;
        for (let i = 1; i < n; i++) {
            toplamArtis += (sonVeriler[i] - sonVeriler[i-1]);
        }
        const ortalamaArtis = toplamArtis / (n - 1);
        
        // 30 dakika sonrası tahmini (10 veri noktası)
        const tahmin = sonVeriler[n-1] + (ortalamaArtis * 10);
        
        return {
            mevcut: sonVeriler[n-1],
            tahmin: tahmin,
            degisim: ortalamaArtis * 10,
            guven: Math.min(95, 60 + (n * 1.5))
        };
    }

    /**
     * Akıllı yorum oluştur
     */
    akıllıYorumOlustur(veriler, analiz) {
        const yorumlar = [];
        const tehditSkoru = veriler.tehdit_skoru;
        
        // Trend bazlı yorumlar
        const ruzgarTrend = this.trendAnalizi('ruzgar_hizi', veriler.ruzgar_hizi);
        const kpTrend = this.trendAnalizi('kp_indeksi', veriler.kp_indeksi);
        
        // Kritik durum analizi
        if (tehditSkoru >= 8) {
            yorumlar.push('🚨 KRİTİK UYARI: Aşırı yüksek uzay hava aktivitesi tespit edildi.');
            
            if (veriler.bz_yonu < -10) {
                yorumlar.push('Manyetik alan şiddetli güneye dönük - jeomanyetik fırtına riski maksimum seviyede.');
            }
            
            if (veriler.ruzgar_hizi > 700) {
                yorumlar.push('Güneş rüzgarı hızı kritik eşiği aştı - uydu sistemleri acil koruma moduna alınmalı.');
            }
            
            yorumlar.push('Tüm uzay operasyonları durdurulmalı, kritik altyapı korunmalıdır.');
            
        } else if (tehditSkoru >= 5) {
            yorumlar.push('⚠️ YÜKSEK RİSK: Önemli uzay hava aktivitesi gözlemleniyor.');
            
            if (ruzgarTrend === 'HIZLI ARTIŞ') {
                yorumlar.push('Güneş rüzgarı hızla artıyor - durum kötüleşebilir.');
            }
            
            if (veriler.kp_indeksi >= 5) {
                yorumlar.push(`Kp indeksi ${veriler.kp_indeksi.toFixed(1)} seviyesinde - orta-güçlü jeomanyetik fırtına aktif.`);
            }
            
            yorumlar.push('Uydu operasyonları yakından izlenmeli, yedekleme sistemleri hazır tutulmalı.');
            
        } else if (tehditSkoru >= 3) {
            yorumlar.push('📊 ORTA SEVİYE: Uzay hava koşulları normal üzerinde.');
            
            if (veriler.plazma_yogunlugu > 15) {
                yorumlar.push(`Plazma yoğunluğu ${veriler.plazma_yogunlugu.toFixed(1)} p/cm³ - ortalamanın üzerinde.`);
            }
            
            if (kpTrend === 'ARTIŞ') {
                yorumlar.push('Jeomanyetik aktivite artış eğiliminde - gelişmeler takip edilmeli.');
            }
            
            yorumlar.push('Rutin izleme protokolleri yeterli, ancak dikkatli olunmalı.');
            
        } else {
            yorumlar.push('✅ NORMAL KOŞULLAR: Uzay hava durumu sakin ve stabil.');
            
            if (veriler.ruzgar_hizi < 350) {
                yorumlar.push('Güneş rüzgarı düşük hızda - ideal koşullar.');
            }
            
            if (veriler.kp_indeksi < 2) {
                yorumlar.push('Jeomanyetik aktivite minimal seviyede.');
            }
            
            yorumlar.push('Tüm uzay operasyonları için uygun koşullar mevcut.');
        }
        
        // Gelecek tahmini ekle
        const ruzgarTahmini = this.gelecekTahmini('ruzgar_hizi');
        if (ruzgarTahmini && Math.abs(ruzgarTahmini.degisim) > 50) {
            if (ruzgarTahmini.degisim > 0) {
                yorumlar.push(`⚡ TAHMİN: Güneş rüzgarı hızının önümüzdeki 30 dakikada ${Math.abs(ruzgarTahmini.degisim).toFixed(0)} km/s artması bekleniyor.`);
            } else {
                yorumlar.push(`📉 TAHMİN: Güneş rüzgarı hızının önümüzdeki 30 dakikada ${Math.abs(ruzgarTahmini.degisim).toFixed(0)} km/s azalması bekleniyor.`);
            }
        }
        
        return yorumlar.join(' ');
    }

    /**
     * Güvenilirlik skoru hesapla
     */
    guvenilirlikHesapla(veriler, analiz) {
        let guvenilirlik = 100;
        
        // Veri kalitesi kontrolü
        if (veriler.ruzgar_hizi === 0 || veriler.ruzgar_hizi > 2000) guvenilirlik -= 20;
        if (veriler.plazma_yogunlugu === 0 || veriler.plazma_yogunlugu > 200) guvenilirlik -= 15;
        if (Math.abs(veriler.bz_yonu) > 50) guvenilirlik -= 10;
        
        // Tarihçe bazlı güvenilirlik
        if (this.tarihce.length < 10) {
            guvenilirlik -= (10 - this.tarihce.length) * 3;
        }
        
        // Tutarlılık kontrolü
        if (this.tarihce.length >= 5) {
            const sonTehditler = this.tarihce.slice(-5).map(t => t.sonuc.tehdit_skoru);
            const standartSapma = this.standartSapmaHesapla(sonTehditler);
            
            if (standartSapma > 3) {
                guvenilirlik -= 10; // Yüksek değişkenlik
            }
        }
        
        return Math.max(60, Math.min(100, guvenilirlik));
    }

    /**
     * Standart sapma hesapla
     */
    standartSapmaHesapla(dizi) {
        const ortalama = dizi.reduce((a, b) => a + b, 0) / dizi.length;
        const varyans = dizi.reduce((sum, val) => sum + Math.pow(val - ortalama, 2), 0) / dizi.length;
        return Math.sqrt(varyans);
    }
}

// Global AI instance
const uzayAI = new UzayHavaAI();

/**
 * Uzay hava durumu verilerini AI destekli analiz eder
 * @param {Object} veriler - Analiz edilecek uzay hava durumu verileri
 * @param {boolean} aiAktif - AI analizini aktif et (varsayılan: true)
 * @returns {Object} Analiz sonucu (JSON formatında)
 */
function uzayHavaDurumuAnalizi(veriler, aiAktif = true) {
    const {
        ruzgar_hizi,
        plazma_yogunlugu,
        bt_gucu,
        bz_yonu,
        kp_indeksi,
        proton_akisi,
        xray_sinifi,
        tehdit_skoru
    } = veriler;

    // Risk faktörlerini hesapla
    let riskPuani = 0;
    let guvenilirlik = 100;
    let kritikDurumlar = [];
    let uyarilar = [];

    // Güneş rüzgarı analizi
    if (ruzgar_hizi > 700) {
        riskPuani += 3;
        kritikDurumlar.push('Aşırı yüksek güneş rüzgarı hızı');
    } else if (ruzgar_hizi > 500) {
        riskPuani += 2;
        uyarilar.push('Yüksek güneş rüzgarı hızı');
    } else if (ruzgar_hizi < 300) {
        uyarilar.push('Düşük güneş rüzgarı hızı');
    }

    // Plazma yoğunluğu analizi
    if (plazma_yogunlugu > 50) {
        riskPuani += 2;
        kritikDurumlar.push('Aşırı yüksek plazma yoğunluğu');
    } else if (plazma_yogunlugu > 20) {
        riskPuani += 1;
        uyarilar.push('Yüksek plazma yoğunluğu');
    }

    // Manyetik alan (Bt) analizi
    if (bt_gucu > 20) {
        riskPuani += 2;
        kritikDurumlar.push('Güçlü manyetik alan');
    } else if (bt_gucu > 10) {
        riskPuani += 1;
        uyarilar.push('Orta seviye manyetik alan');
    }

    // Manyetik alan yönü (Bz) analizi - Negatif değerler tehlikelidir
    if (bz_yonu < -10) {
        riskPuani += 3;
        kritikDurumlar.push('Güçlü güneye dönük manyetik alan (Bz)');
    } else if (bz_yonu < -5) {
        riskPuani += 2;
        uyarilar.push('Orta seviye güneye dönük manyetik alan');
    }

    // Kp indeksi analizi
    if (kp_indeksi >= 7) {
        riskPuani += 3;
        kritikDurumlar.push('Şiddetli jeomanyetik fırtına (Kp≥7)');
    } else if (kp_indeksi >= 5) {
        riskPuani += 2;
        uyarilar.push('Orta seviye jeomanyetik fırtına');
    } else if (kp_indeksi >= 3) {
        riskPuani += 1;
        uyarilar.push('Hafif jeomanyetik aktivite');
    }

    // Proton akısı analizi
    if (proton_akisi > 100) {
        riskPuani += 3;
        kritikDurumlar.push('Yüksek proton radyasyonu');
        guvenilirlik -= 5;
    } else if (proton_akisi > 10) {
        riskPuani += 1;
        uyarilar.push('Orta seviye proton radyasyonu');
    }

    // X-ray sınıfı analizi
    const xrayLevel = parseXrayClass(xray_sinifi);
    if (xrayLevel >= 5) { // X-class
        riskPuani += 3;
        kritikDurumlar.push('X-sınıfı güneş patlaması');
    } else if (xrayLevel >= 4) { // M-class
        riskPuani += 2;
        uyarilar.push('M-sınıfı güneş patlaması');
    } else if (xrayLevel >= 3) { // C-class
        riskPuani += 1;
        uyarilar.push('C-sınıfı güneş patlaması');
    }

    // Tehdit skoru ile çapraz kontrol
    const skorFarki = Math.abs(riskPuani - tehdit_skoru);
    if (skorFarki > 3) {
        guvenilirlik -= 10;
    }

    // Risk seviyesini belirle
    let riskSeviyesi;
    if (tehdit_skoru >= 8 || riskPuani >= 8) {
        riskSeviyesi = 'KRİTİK';
    } else if (tehdit_skoru >= 5 || riskPuani >= 5) {
        riskSeviyesi = 'YÜKSEK';
    } else if (tehdit_skoru >= 3 || riskPuani >= 3) {
        riskSeviyesi = 'ORTA';
    } else {
        riskSeviyesi = 'DÜŞÜK';
    }

    // Temel analiz objesi
    const temelAnaliz = {
        risk_seviyesi: riskSeviyesi,
        tehdit_skoru: tehdit_skoru,
        hesaplanan_risk_puani: riskPuani
    };

    // AI Analizi
    let durumOzeti, oneri, aiDetaylar = null;
    
    if (aiAktif && typeof uzayAI !== 'undefined') {
        // AI ile gelişmiş yorum oluştur
        durumOzeti = uzayAI.akıllıYorumOlustur(veriler, temelAnaliz);
        
        // AI güvenilirlik hesapla
        guvenilirlik = uzayAI.guvenilirlikHesapla(veriler, temelAnaliz);
        
        // AI öneri
        if (riskSeviyesi === 'KRİTİK') {
            oneri = 'ACİL ÖNLEM - Uydu sistemlerini koruma moduna alın, kritik operasyonları erteleyin';
        } else if (riskSeviyesi === 'YÜKSEK') {
            oneri = 'DİKKAT GEREKLİ - Sistemleri yakından izleyin, yedekleme prosedürlerini hazırlayın';
        } else if (riskSeviyesi === 'ORTA') {
            oneri = 'İZLEME DEVAM - Rutin kontroller yapın, parametreleri takip edin';
        } else {
            oneri = 'NORMAL OPERASYON - Standart izleme protokolü yeterli';
        }
        
        // AI detayları
        aiDetaylar = {
            ruzgar_trend: uzayAI.trendAnalizi('ruzgar_hizi', ruzgar_hizi),
            kp_trend: uzayAI.trendAnalizi('kp_indeksi', kp_indeksi),
            tahminler: {
                ruzgar: uzayAI.gelecekTahmini('ruzgar_hizi'),
                kp: uzayAI.gelecekTahmini('kp_indeksi')
            }
        };
        
        // Veriyi AI tarihçesine ekle
        uzayAI.veriEkle(veriler, temelAnaliz);
        
    } else {
        // Standart yorum (AI olmadan)
        if (riskSeviyesi === 'KRİTİK') {
            durumOzeti = `Kritik seviye uzay hava durumu tespit edildi. Güneş rüzgarı ${ruzgar_hizi.toFixed(0)} km/s hızında, `;
            durumOzeti += `manyetik alan ${bt_gucu.toFixed(1)} nT gücünde. `;
            if (bz_yonu < -5) {
                durumOzeti += `Manyetik alan güneye dönük (Bz: ${bz_yonu.toFixed(1)} nT), jeomanyetik fırtına riski çok yüksek. `;
            }
            durumOzeti += `Kp indeksi ${kp_indeksi.toFixed(1)} seviyesinde.`;
        } else if (riskSeviyesi === 'YÜKSEK') {
            durumOzeti = `Yüksek seviye uzay hava aktivitesi gözlemleniyor. `;
            durumOzeti += `Güneş rüzgarı ${ruzgar_hizi.toFixed(0)} km/s, manyetik alan ${bt_gucu.toFixed(1)} nT. `;
            durumOzeti += `Uydu sistemleri ve iletişim altyapısı etkilenebilir.`;
        } else if (riskSeviyesi === 'ORTA') {
            durumOzeti = `Orta seviye uzay hava aktivitesi mevcut. `;
            durumOzeti += `Güneş rüzgarı ${ruzgar_hizi.toFixed(0)} km/s hızında, parametreler normal sınırlar içinde. `;
            durumOzeti += `Rutin izleme devam ediyor.`;
        } else {
            durumOzeti = `Uzay hava durumu sakin. `;
            durumOzeti += `Tüm parametreler normal sınırlar içinde. Güneş rüzgarı ${ruzgar_hizi.toFixed(0)} km/s, `;
            durumOzeti += `Kp indeksi ${kp_indeksi.toFixed(1)}. Önemli bir aktivite beklenmemektedir.`;
        }
        
        if (riskSeviyesi === 'KRİTİK') {
            oneri = 'ACİL ÖNLEM - Uydu sistemlerini koruma moduna alın, kritik operasyonları erteleyin';
        } else if (riskSeviyesi === 'YÜKSEK') {
            oneri = 'DİKKAT GEREKLİ - Sistemleri yakından izleyin, yedekleme prosedürlerini hazırlayın';
        } else if (riskSeviyesi === 'ORTA') {
            oneri = 'İZLEME DEVAM - Rutin kontroller yapın, parametreleri takip edin';
        } else {
            oneri = 'NORMAL OPERASYON - Standart izleme protokolü yeterli';
        }
        
        guvenilirlik = Math.max(60, Math.min(100, guvenilirlik));
    }

    // Sonuç objesi
    const sonuc = {
        durum: 'basarili',
        yorum: durumOzeti,
        guvenilirlik: guvenilirlik,
        risk_seviyesi: riskSeviyesi,
        oneri: oneri,
        detaylar: {
            kritik_durumlar: kritikDurumlar,
            uyarilar: uyarilar,
            hesaplanan_risk_puani: riskPuani,
            tehdit_skoru: tehdit_skoru,
            analiz_zamani: new Date().toISOString()
        }
    };
    
    // AI detaylarını ekle
    if (aiDetaylar) {
        sonuc.ai_analiz = aiDetaylar;
    }
    
    return sonuc;
}

/**
 * X-ray sınıfını sayısal değere çevirir
 * @param {string} xrayClass - X-ray sınıfı (örn: "M5.2", "X1.0")
 * @returns {number} Sayısal seviye (0-6 arası)
 */
function parseXrayClass(xrayClass) {
    if (!xrayClass || typeof xrayClass !== 'string') return 0;
    
    const classLetter = xrayClass.charAt(0).toUpperCase();
    const magnitude = parseFloat(xrayClass.substring(1)) || 1.0;
    
    const classLevels = {
        'A': 0,
        'B': 1,
        'C': 2,
        'M': 3,
        'X': 4
    };
    
    const baseLevel = classLevels[classLetter] || 0;
    return baseLevel + (magnitude / 10);
}

/**
 * Örnek kullanım ve test fonksiyonu
 */
function testAnaliz() {
    const ornekVeri = {
        ruzgar_hizi: 450,
        plazma_yogunlugu: 8.5,
        bt_gucu: 6.2,
        bz_yonu: -3.1,
        kp_indeksi: 3.5,
        proton_akisi: 2.4,
        xray_sinifi: "C2.1",
        tehdit_skoru: 3.2
    };
    
    const sonuc = uzayHavaDurumuAnalizi(ornekVeri);
    console.log('Analiz Sonucu:', JSON.stringify(sonuc, null, 2));
    return sonuc;
}

// Node.js için export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        uzayHavaDurumuAnalizi,
        parseXrayClass,
        testAnaliz
    };
}

// Browser için global scope
if (typeof window !== 'undefined') {
    window.uzayHavaDurumuAnalizi = uzayHavaDurumuAnalizi;
    window.parseXrayClass = parseXrayClass;
    window.testAnaliz = testAnaliz;
}