"""Tanıtım videosu ve denemeler için ayrı bir demo veri seti oluşturur.

    python demo/veri_olustur.py

demo/veri/ ve demo/uploads/ klasörlerini SIFIRDAN yazar (önceki demo verisi silinir).
Gerçek veriye (data/, uploads/) hiç dokunmaz. Paneli demo veriyle açmak için:

    PowerShell:
        $env:PANEL_VERI_KLASORU = "demo/veri"; $env:PANEL_YUKLEME_KLASORU = "demo/uploads"; python app.py

Demo hesapları (yalnızca demo veri setinde vardır):
    Dekan          : demo.dekan    / Demo-Dekan-2026
    Kulüp başkanı  : demo.baskan   / Demo-Baskan-2026   (Örnek Fotoğrafçılık Kulübü)
    Kulüp başkanı  : demo.baskan2  / Demo-Baskan-2026   (Örnek Satranç Kulübü)
"""

import json
import os
import shutil
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

DEMO = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(DEMO, "veri")
YUKLEME = os.path.join(DEMO, "uploads")

DEKAN = ("demo.dekan", "Demo-Dekan-2026")
BASKAN = ("demo.baskan", "Demo-Baskan-2026")
BASKAN2 = ("demo.baskan2", "Demo-Baskan-2026")


def _yaz(dosya, veri):
    with open(os.path.join(VERI, dosya), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _ornek_pdf(yol):
    """Videoda başvuruya eklenecek tek sayfalık örnek PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(yol, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 770, "Etkinlik Plani (ornek belge)")
    c.setFont("Helvetica", 11)
    for i, satir in enumerate([
        "Bu dosya tanitim videosu icin olusturulmus ornek bir ektir.",
        "Etkinlik: Sokak Fotografciligi Atolyesi",
        "Program: 14.00 Acilis - 14.15 Sunum - 15.00 Cekim yuruyusu - 16.30 Degerlendirme",
    ]):
        c.drawString(72, 735 - 20 * i, satir)
    c.save()


def olustur():
    for klasor in (VERI, YUKLEME):
        shutil.rmtree(klasor, ignore_errors=True)
        os.makedirs(klasor)

    bugun = date.today()
    simdi = datetime.now()

    def gun(n, saat="14:00"):
        return f"{bugun + timedelta(days=n):%Y-%m-%d}T{saat}"

    def an(gun_once, saat="10:30"):
        return f"{bugun - timedelta(days=gun_once):%Y-%m-%d} {saat}"

    donem_id = "demodonem001"
    _yaz("donemler.json", {"aktif": donem_id, "donemler": [{
        "id": donem_id, "ad": "Demo Dönemi",
        "baslangic": f"{bugun - timedelta(days=60):%Y-%m-%d}", "bitis": f"{bugun + timedelta(days=120):%Y-%m-%d}",
    }]})

    _yaz("ayarlar.json", {"baskan_girisi": True, "oturum_suresi_dk": 60})

    _yaz("danismanlar.json", [{
        "id": "demodanisman", "ad_soyad": "Selin Arslan", "unvan": "Dr. Öğr. Üyesi",
        "fakulte": "Güzel Sanatlar ve Tasarım Fakültesi", "bolum": "Görsel İletişim Tasarımı",
        "eposta": "selin.arslan@ornek.edu.tr", "telefon": "",
    }])

    _yaz("clubs.json", {"kulupler": [
        {
            "id": "ornek-fotograf", "isim": "Örnek Fotoğrafçılık Kulübü", "logo": "", "kategori": "Sanat / Kültür",
            "aciklama": "Tanıtım videosu için oluşturulmuş örnek kulüp.", "eposta": "fotograf@ornek.edu.tr",
            "baskan": "Deniz Aydın", "durum": "aktif", "danisman_id": "demodanisman",
            "yonetim_kurulu": [
                {"gorev": "Başkan", "isim": "Deniz Aydın"},
                {"gorev": "Başkan Yardımcısı", "isim": "Mert Kaplan"},
                {"gorev": "Sekreter", "isim": "İrem Şahin"},
                {"gorev": "Sayman", "isim": "Burak Çelik"},
            ],
        },
        {
            "id": "ornek-satranc", "isim": "Örnek Satranç Kulübü", "logo": "", "kategori": "Spor",
            "aciklama": "Tanıtım videosu için oluşturulmuş ikinci örnek kulüp.", "eposta": "satranc@ornek.edu.tr",
            "baskan": "Ece Yılmaz", "durum": "aktif", "danisman_id": "",
            "yonetim_kurulu": [{"gorev": "Başkan", "isim": "Ece Yılmaz"}],
        },
    ]})

    ogrenciler = {
        "900000001": {"ad_soyad": "Deniz Aydın", "bolum": "Görsel İletişim Tasarımı", "sinif": "3",
                      "telefon": "", "eposta": "deniz.aydin@ornek.edu.tr"},
        "900000002": {"ad_soyad": "Mert Kaplan", "bolum": "Mimarlık", "sinif": "2", "telefon": "", "eposta": ""},
        "900000003": {"ad_soyad": "İrem Şahin", "bolum": "Psikoloji", "sinif": "4", "telefon": "", "eposta": ""},
        "900000004": {"ad_soyad": "Ece Yılmaz", "bolum": "Bilgisayar Mühendisliği", "sinif": "3",
                      "telefon": "", "eposta": "ece.yilmaz@ornek.edu.tr"},
    }
    _yaz("ogrenciler.json", ogrenciler)
    kayit = f"{bugun - timedelta(days=30):%Y-%m-%d}"
    _yaz("uyelikler.json", {
        "ornek-fotograf": {"onaylanan": ["900000001", "900000002", "900000003"], "bekleyen": [],
                           "katilim_tarihleri": {n: kayit for n in ("900000001", "900000002", "900000003")}},
        "ornek-satranc": {"onaylanan": ["900000004"], "bekleyen": [], "katilim_tarihleri": {"900000004": kayit}},
    })

    olusturma = f"{simdi:%Y-%m-%d %H:%M}"
    _yaz("kullanicilar.json", [
        {"kullanici_adi": DEKAN[0], "sifre_hash": generate_password_hash(DEKAN[1]), "rol": "dekan",
         "ad_soyad": "Öğrenci Dekanı (Demo)", "aktif": True, "olusturma": olusturma},
        {"kullanici_adi": BASKAN[0], "sifre_hash": generate_password_hash(BASKAN[1]), "rol": "baskan",
         "ad_soyad": "Deniz Aydın", "kulup_id": "ornek-fotograf", "aktif": True, "olusturma": olusturma},
        {"kullanici_adi": BASKAN2[0], "sifre_hash": generate_password_hash(BASKAN2[1]), "rol": "baskan",
         "ad_soyad": "Ece Yılmaz", "kulup_id": "ornek-satranc", "aktif": True, "olusturma": olusturma},
    ])

    def basvuru(kimlik, kulup_id, ad, etkinlik, giren, gecmis, **alanlar):
        return {
            "id": kimlik, "kulup_id": kulup_id, "ad": ad, "aciklama": alanlar.get("aciklama", ""),
            "tarih_saat": etkinlik, "saat_belirsiz": False, "yer": alanlar.get("yer", "Mahmutbey Yerleşkesi"),
            "katilimci": alanlar.get("katilimci", 40), "konusmaci_var": False, "konusmaci": "",
            "butce": alanlar.get("butce", 0.0), "butce_aciklama": alanlar.get("butce_aciklama", ""),
            "ek_dosyalar": [], "kaynak": "baskan", "giren": giren, "olusturma": gecmis[0]["tarih"],
            "durum": gecmis[-1]["durum"], "gecmis": gecmis,
        }

    def adim(tarih, kullanici, durum, aciklama):
        return {"tarih": tarih, "kullanici": kullanici, "durum": durum, "aciklama": aciklama}

    kaydedildi = "Başvuru kaydedildi (kulüp başkanı panelden girdi)."
    _yaz("etkinlik_basvurulari.json", [
        basvuru("demobasvuru01", "ornek-fotograf", "Portre Fotoğrafçılığı Semineri", gun(-10), "Deniz Aydın", [
            adim(an(20), "Deniz Aydın", "beklemede", kaydedildi),
            adim(an(18, "15:10"), "Öğrenci Dekanı (Demo)", "onaylandi", "Salon rezervasyonu yapıldı."),
        ], yer="Konferans Salonu", katilimci=60),
        basvuru("demobasvuru02", "ornek-fotograf", "Gece Çekimi Gezisi", gun(5, "22:00"), "Deniz Aydın", [
            adim(an(6), "Deniz Aydın", "beklemede", kaydedildi),
            adim(an(5, "09:45"), "Öğrenci Dekanı (Demo)", "reddedildi",
                 "Yerleşke dışı gece etkinlikleri için danışman onay formu gerekiyor; form eklenerek yeniden başvurulabilir."),
        ], yer="Galata – Karaköy", katilimci=25),
        basvuru("demobasvuru03", "ornek-satranc", "Kulüpler Arası Satranç Turnuvası", gun(21, "10:00"), "Ece Yılmaz", [
            adim(an(1, "16:20"), "Ece Yılmaz", "beklemede", kaydedildi),
        ], yer="Spor Salonu, Çok Amaçlı Salon", katilimci=32, butce=1500.0, butce_aciklama="Madalya ve ikram",
           aciklama="Kulüp üyelerinin ve diğer kulüplerden davetli öğrencilerin katılacağı tek günlük turnuva."),
    ])

    _yaz("zorunlu_evraklar.json", [{
        "id": "demoevrak0001", "donem_id": donem_id, "tur": "Faaliyet Planı",
        "teslim_tarihi": f"{bugun + timedelta(days=10):%Y-%m-%d}", "aciklama": "", "elden": {},
    }])
    for dosya in ("belgeler.json", "islem_gecmisi.json", "gorev_gecmisi.json", "duyurular.json"):
        _yaz(dosya, [])
    _yaz("karneler.json", {})

    _ornek_pdf(os.path.join(DEMO, "ornek-etkinlik-plani.pdf"))
    print(f"Demo veri seti hazır: {VERI}")


if __name__ == "__main__":
    olustur()
