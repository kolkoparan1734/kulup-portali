"""
Öğrenci Dekanlığı Kulüp Paneli
--------------------------------
Altınbaş Üniversitesi Öğrenci Dekanlığı'nın kulüpleri, üyeleri ve kulüp
evraklarını yönettiği iç kullanım paneli. Flask ile çalışır, tüm veriyi
data/*.json dosyalarında tutar (bkz. veri.py).

Nasıl çalıştırılır (VS Code terminalinde):
    1) pip install -r requirements.txt
    2) python app.py
    3) Tarayıcıda http://127.0.0.1:5000 adresini açın

Ortam değişkenleri (isteğe bağlı):
    PANEL_SECRET_KEY     -> oturum şifreleme anahtarı
    PANEL_KURTARMA_KODU  -> "Şifremi unuttum" sayfasında istenen kurtarma kodu.
                            Tanımlı değilse şifre sıfırlama kapalıdır.
"""

import hmac
import io
import os
import re
import secrets
from datetime import date, datetime
from functools import wraps
from uuid import uuid4

from flask import (
    Flask, render_template, abort, request, redirect, url_for, session, flash,
    send_file, send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import veri

app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET_KEY", "prototip-gizli-anahtar-degistirin")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # yükleme sınırı: 20 MB

BELGE_KLASORU = os.path.join(app.root_path, "uploads", "belgeler")
LOGO_KLASORU = os.path.join(app.static_folder, "images")

BELGE_UZANTILARI = {"pdf", "doc", "docx", "odt", "xls", "xlsx", "ods", "png", "jpg", "jpeg"}
LOGO_UZANTILARI = {"png", "jpg", "jpeg", "webp"}
BELGE_TURLERI = ["Tüzük", "Faaliyet Raporu", "Faaliyet Bildirim Formu", "Etkinlik Başvurusu",
                 "Danışman Formu", "Toplantı Tutanağı", "Diğer"]
YK_GOREVLERI = ["Başkan", "Başkan Yardımcısı", "Sekreter", "Sayman"]

# Giriş yapmadan açılabilen sayfalar.
ACIK_SAYFALAR = {"giris_yap", "sifremi_unuttum", "static"}


# ---------------------------------------------------------------------------
# Oturum ve güvenlik
# ---------------------------------------------------------------------------

@app.before_request
def oturum_kontrolu():
    """Giriş yapılmamışsa (veya kullanıcının panel yetkisi kalkmışsa) giriş sayfasına yönlendirir."""
    if request.endpoint in ACIK_SAYFALAR:
        return None
    kullanici = veri.kullanici_bul(session.get("kullanici_adi", ""))
    if not veri.panel_yetkilisi_mi(kullanici):
        # Sadece kullanıcı bilgisi silinir; csrf anahtarı kalmalı, yoksa
        # tarayıcının arka planda istediği /favicon.ico gibi adresler açık
        # giriş formunun anahtarını geçersiz kılar.
        session.pop("kullanici_adi", None)
        session.pop("ad_soyad", None)
        return redirect(url_for("giris_yap", sonra=request.full_path.rstrip("?") if request.method == "GET" else None))
    return None


@app.before_request
def csrf_kontrolu():
    """Tüm POST isteklerinde formdaki gizli anahtarı oturumdakiyle karşılaştırır."""
    if request.method == "POST":
        beklenen = session.get("csrf")
        gelen = request.form.get("csrf", "")
        if not beklenen or not hmac.compare_digest(beklenen, gelen):
            abort(400)


@app.context_processor
def sablon_degiskenleri():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {"csrf": session["csrf"], "aktif_sayfa": request.endpoint or ""}


def _guvenli_yonlendirme(hedef):
    """Sadece site içi göreli adreslere yönlendirmeye izin verir."""
    if hedef and hedef.startswith("/") and not hedef.startswith("//"):
        return hedef
    return url_for("ana_panel")


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
@app.errorhandler(500)
def hata_sayfasi(hata):
    kod = getattr(hata, "code", 500) or 500
    mesajlar = {
        400: "İstek geçersiz veya oturum süresi dolmuş. Sayfayı yenileyip tekrar deneyin.",
        403: "Bu işlem için yetkiniz yok.",
        404: "Aradığınız sayfa bulunamadı.",
        413: "Yüklenen dosya çok büyük (en fazla 20 MB).",
        500: "Beklenmeyen bir hata oluştu.",
    }
    return render_template("eror.html", kod=kod, mesaj=mesajlar.get(kod, "Bir hata oluştu.")), kod


# ---------------------------------------------------------------------------
# Giriş / çıkış
# ---------------------------------------------------------------------------

@app.route("/giris", methods=["GET", "POST"])
def giris_yap():
    hata = None
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "")
        kullanici = veri.kullanici_bul(kullanici_adi)

        if (veri.panel_yetkilisi_mi(kullanici)
                and check_password_hash(kullanici["sifre_hash"], sifre)):
            csrf = session.get("csrf")
            session.clear()
            session["csrf"] = csrf or secrets.token_hex(16)
            session["kullanici_adi"] = kullanici["kullanici_adi"]
            session["ad_soyad"] = kullanici.get("ad_soyad") or kullanici["kullanici_adi"]
            return redirect(_guvenli_yonlendirme(request.args.get("sonra")))
        hata = "Kullanıcı adı veya şifre hatalı ya da panele erişim yetkiniz yok."

    return render_template("giris.html", hata=hata)


@app.route("/sifremi-unuttum", methods=["GET", "POST"])
def sifremi_unuttum():
    """Yetkili kullanıcının, kurtarma koduyla yeni şifre belirlemesi."""
    kurtarma_kodu = os.environ.get("PANEL_KURTARMA_KODU", "")
    hata = None
    if request.method == "POST" and kurtarma_kodu:
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        kod = request.form.get("kurtarma_kodu", "")
        yeni_sifre = request.form.get("yeni_sifre", "")
        yeni_sifre_tekrar = request.form.get("yeni_sifre_tekrar", "")
        kullanici = veri.kullanici_bul(kullanici_adi)

        if not veri.panel_yetkilisi_mi(kullanici) or not hmac.compare_digest(kod, kurtarma_kodu):
            hata = "Kullanıcı adı veya kurtarma kodu hatalı."
        elif len(yeni_sifre) < 8:
            hata = "Yeni şifre en az 8 karakter olmalı."
        elif yeni_sifre != yeni_sifre_tekrar:
            hata = "Girdiğiniz şifreler birbiriyle uyuşmuyor."
        else:
            veri.kullanici_sifre_guncelle(kullanici["kullanici_adi"], generate_password_hash(yeni_sifre))
            flash("Şifreniz güncellendi, yeni şifrenizle giriş yapabilirsiniz.", "basarili")
            return redirect(url_for("giris_yap"))

    return render_template("sifremi_unuttum.html", hata=hata, aktif=bool(kurtarma_kodu))


@app.route("/cikis")
def cikis_yap():
    session.clear()
    flash("Oturumunuz kapatıldı.", "basarili")
    return redirect(url_for("giris_yap"))


# ---------------------------------------------------------------------------
# Ana panel
# ---------------------------------------------------------------------------

@app.route("/")
def ana_panel():
    kulupler = veri.kulupleri_getir()
    tum_uyeler = veri.tum_uyeleri_getir()
    ozet = {
        "kulup": len(kulupler),
        "uye": len({u["ogrenci_no"] for u in tum_uyeler}),
        "uyelik": len(tum_uyeler),
        "aktif": sum(1 for k in kulupler if k["durum"] == "aktif"),
        "pasif": sum(1 for k in kulupler if k["durum"] != "aktif"),
    }
    en_buyukler = sorted(kulupler, key=lambda k: k["uye_sayisi"], reverse=True)[:6]
    return render_template(
        "panel.html",
        ozet=ozet,
        son_uyeler=veri.son_eklenen_uyeler(),
        en_buyukler=en_buyukler,
        en_fazla=max((k["uye_sayisi"] for k in en_buyukler), default=0),
    )


# ---------------------------------------------------------------------------
# Kulüpler
# ---------------------------------------------------------------------------

def _kulup_veya_404(kulup_id):
    kulup = veri.kulup_getir(kulup_id)
    if kulup is None:
        abort(404)
    return kulup


_TR_HARF = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _kulup_id_uret(isim):
    temel = re.sub(r"[^a-z0-9]+", "-", isim.translate(_TR_HARF).lower()).strip("-")
    temel = re.sub(r"-?kulubu?$", "", temel) or "kulup"
    mevcutlar = {k["id"] for k in veri.kulupleri_getir()}
    aday, sayac = temel, 2
    while aday in mevcutlar:
        aday, sayac = f"{temel}-{sayac}", sayac + 1
    return aday


def _uzanti(dosya_adi):
    return dosya_adi.rsplit(".", 1)[-1].lower() if "." in dosya_adi else ""


@app.route("/kulupler")
def kulupler():
    return render_template(
        "kulupler.html",
        kulupler=veri.kulupleri_getir(),
        kategoriler=veri.kategorileri_getir(),
    )


@app.route("/kulupler/yeni", methods=["GET", "POST"])
@app.route("/kulupler/<kulup_id>/duzenle", methods=["GET", "POST"])
def kulup_form(kulup_id=None):
    mevcut = _kulup_veya_404(kulup_id) if kulup_id else None
    hata = None

    if request.method == "POST":
        f = request.form
        kulup = {
            "isim": f.get("isim", "").strip(),
            "kategori": f.get("kategori", "").strip(),
            "aciklama": f.get("aciklama", "").strip(),
            "baskan": f.get("baskan", "").strip(),
            "durum": "pasif" if f.get("durum") == "pasif" else "aktif",
            "danisman": {
                "isim": f.get("danisman_isim", "").strip(),
                "eposta": f.get("danisman_eposta", "").strip(),
                "telefon": f.get("danisman_telefon", "").strip(),
            },
            "yonetim_kurulu": [
                {"gorev": g.strip(), "isim": i.strip()}
                for g, i in zip(f.getlist("yk_gorev"), f.getlist("yk_isim"))
                if g.strip() and i.strip()
            ],
        }
        logo = request.files.get("logo")

        if not kulup["isim"] or not kulup["kategori"]:
            hata = "Kulüp adı ve kategori boş bırakılamaz."
        elif logo and logo.filename and _uzanti(logo.filename) not in LOGO_UZANTILARI:
            hata = "Logo PNG, JPG veya WEBP olmalı."
        else:
            kulup["id"] = mevcut["id"] if mevcut else _kulup_id_uret(kulup["isim"])
            if logo and logo.filename:
                dosya = f"{kulup['id']}_logo_{uuid4().hex[:6]}.{_uzanti(logo.filename)}"
                logo.save(os.path.join(LOGO_KLASORU, dosya))
                kulup["logo"] = dosya
            elif not mevcut:
                kulup["logo"] = ""
            veri.kulup_kaydet(kulup)
            flash(f"{kulup['isim']} {'güncellendi' if mevcut else 'eklendi'}.", "basarili")
            return redirect(url_for("kulup_detay", kulup_id=kulup["id"]))

        # Hatalı gönderimde formu girilen değerlerle tekrar göster.
        mevcut = {**(mevcut or {}), **kulup}

    return render_template(
        "kulup_form.html",
        kulup=mevcut,
        hata=hata,
        kategoriler=veri.kategorileri_getir(),
        yk_gorevleri=YK_GOREVLERI,
        # Yeni kulüpte standart görevler boş isimle hazır gelir.
        yk_satirlari=(mevcut or {}).get("yonetim_kurulu") or [{"gorev": g, "isim": ""} for g in YK_GOREVLERI],
    )


@app.route("/kulupler/<kulup_id>/sil", methods=["POST"])
def kulup_sil(kulup_id):
    kulup = _kulup_veya_404(kulup_id)
    for belge in veri.kulup_sil(kulup_id):
        _belge_dosyasini_sil(belge)
    flash(f"{kulup['isim']} silindi.", "basarili")
    return redirect(url_for("kulupler"))


@app.route("/kulupler/<kulup_id>")
def kulup_detay(kulup_id):
    kulup = _kulup_veya_404(kulup_id)
    return render_template(
        "kulup_detay.html",
        kulup=kulup,
        uyeler=veri.uyeleri_getir(kulup_id),
        belgeler=veri.belgeleri_getir(kulup_id),
    )


# ---------------------------------------------------------------------------
# Kulüp üyeleri
# ---------------------------------------------------------------------------

@app.route("/kulupler/<kulup_id>/uyeler/yeni", methods=["GET", "POST"])
@app.route("/kulupler/<kulup_id>/uyeler/<ogrenci_no>/duzenle", methods=["GET", "POST"])
def uye_form(kulup_id, ogrenci_no=None):
    kulup = _kulup_veya_404(kulup_id)
    mevcut = None
    if ogrenci_no:
        mevcut = next((u for u in veri.uyeleri_getir(kulup_id) if u["ogrenci_no"] == ogrenci_no), None)
        if mevcut is None:
            abort(404)
    hata = None

    if request.method == "POST":
        uye = {alan: request.form.get(alan, "").strip() for alan in veri.OGRENCI_ALANLARI}
        uye["ogrenci_no"] = request.form.get("ogrenci_no", "").strip()
        uye["katilim_tarihi"] = request.form.get("katilim_tarihi", "").strip()

        if not uye["ogrenci_no"] or not uye["ad_soyad"]:
            hata = "Öğrenci numarası ve ad soyad boş bırakılamaz."
        elif not re.fullmatch(r"[0-9A-Za-zçğıöşüÇĞİÖŞÜ]{1,32}", uye["ogrenci_no"]):
            hata = "Öğrenci numarası geçersiz."
        elif uye["eposta"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", uye["eposta"]):
            hata = "E-posta adresi geçersiz."
        elif uye["ogrenci_no"] != ogrenci_no and veri.uye_mi(kulup_id, uye["ogrenci_no"]):
            hata = "Bu öğrenci zaten bu kulübün üyesi."
        else:
            try:
                if uye["katilim_tarihi"]:
                    datetime.strptime(uye["katilim_tarihi"], "%Y-%m-%d")
            except ValueError:
                hata = "Katılım tarihi geçersiz."
            else:
                veri.uye_kaydet(kulup_id, uye["ogrenci_no"], uye, uye["katilim_tarihi"], ogrenci_no)
                flash(f"{uye['ad_soyad']} {'güncellendi' if mevcut else 'eklendi'}.", "basarili")
                return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#uyeler")
        mevcut = {**(mevcut or {}), **uye}

    return render_template(
        "uye_form.html",
        kulup=kulup,
        uye=mevcut,
        duzenleme=ogrenci_no is not None,
        hata=hata,
        bugun=date.today().isoformat(),
    )


@app.route("/kulupler/<kulup_id>/uyeler/<ogrenci_no>/sil", methods=["POST"])
def uye_sil(kulup_id, ogrenci_no):
    _kulup_veya_404(kulup_id)
    veri.uye_sil(kulup_id, ogrenci_no)
    flash(f"{ogrenci_no} numaralı öğrenci kulüpten çıkarıldı.", "basarili")
    return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#uyeler")


UYE_SUTUNLARI = [
    ("ad_soyad", "Ad Soyad"), ("ogrenci_no", "Öğrenci No"), ("bolum", "Bölüm"),
    ("sinif", "Sınıf"), ("telefon", "Telefon"), ("eposta", "E-posta"),
    ("katilim_tarihi", "Katılım Tarihi"),
]


def _dosya_adi(kulup):
    return f"{kulup['id']}-uyeler-{date.today().isoformat()}"


@app.route("/kulupler/<kulup_id>/uyeler.xlsx")
def uyeler_excel(kulup_id):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    kulup = _kulup_veya_404(kulup_id)
    kitap = Workbook()
    sayfa = kitap.active
    sayfa.title = "Üyeler"
    sayfa.append([baslik for _, baslik in UYE_SUTUNLARI])
    for hucre in sayfa[1]:
        hucre.font = Font(bold=True, color="FFFFFF")
        hucre.fill = PatternFill("solid", fgColor="1B2F8F")
    for uye in veri.uyeleri_getir(kulup_id):
        sayfa.append([uye[alan] for alan, _ in UYE_SUTUNLARI])
    for sutun, genislik in zip("ABCDEFG", (26, 14, 28, 8, 16, 30, 15)):
        sayfa.column_dimensions[sutun].width = genislik
    sayfa.freeze_panes = "A2"

    cikti = io.BytesIO()
    kitap.save(cikti)
    cikti.seek(0)
    return send_file(cikti, as_attachment=True, download_name=_dosya_adi(kulup) + ".xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _pdf_fontu():
    """Türkçe karakterleri destekleyen bir TTF yazı tipi kaydeder; bulamazsa Helvetica döner."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    adaylar = [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
    ]
    for normal, kalin in adaylar:
        if os.path.exists(normal) and os.path.exists(kalin):
            if "PanelFont" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("PanelFont", normal))
                pdfmetrics.registerFont(TTFont("PanelFont-Bold", kalin))
            return "PanelFont", "PanelFont-Bold"
    return "Helvetica", "Helvetica-Bold"


@app.route("/kulupler/<kulup_id>/uyeler.pdf")
def uyeler_pdf(kulup_id):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    kulup = _kulup_veya_404(kulup_id)
    uyeler = veri.uyeleri_getir(kulup_id)
    font, font_kalin = _pdf_fontu()

    cikti = io.BytesIO()
    belge = SimpleDocTemplate(cikti, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                              topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=f"{kulup['isim']} Üye Listesi")
    baslik = ParagraphStyle("baslik", fontName=font_kalin, fontSize=15, leading=19, textColor=colors.HexColor("#12205F"))
    alt = ParagraphStyle("alt", fontName=font, fontSize=9, leading=12, textColor=colors.HexColor("#757E8C"))
    hucre = ParagraphStyle("hucre", fontName=font, fontSize=8, leading=10)

    satirlar = [[baslik_ for _, baslik_ in UYE_SUTUNLARI]]
    for uye in uyeler:
        satirlar.append([Paragraph(str(uye[alan] or "—"), hucre) for alan, _ in UYE_SUTUNLARI])
    tablo = Table(satirlar, repeatRows=1,
                  colWidths=[5 * cm, 2.6 * cm, 5 * cm, 1.4 * cm, 3 * cm, 6 * cm, 2.6 * cm])
    tablo.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), font_kalin),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2F8F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F5FA")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9DCE6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    belge.build([
        Paragraph(f"{kulup['isim']} — Üye Listesi", baslik),
        Paragraph(f"Altınbaş Üniversitesi Öğrenci Dekanlığı · {len(uyeler)} üye · "
                  f"{date.today().strftime('%d.%m.%Y')}", alt),
        Spacer(1, 0.4 * cm),
        tablo,
    ])
    cikti.seek(0)
    return send_file(cikti, as_attachment=True, download_name=_dosya_adi(kulup) + ".pdf",
                     mimetype="application/pdf")


# ---------------------------------------------------------------------------
# Tüm üyeler
# ---------------------------------------------------------------------------

@app.route("/uyeler")
def uyeler():
    return render_template(
        "uyeler.html",
        uyeler=veri.tum_uyeleri_getir(),
        kulupler=veri.kulupleri_getir(),
        secili_kulup=request.args.get("kulup", ""),
    )


# ---------------------------------------------------------------------------
# Belgeler
# ---------------------------------------------------------------------------

def _belge_dosyasini_sil(belge):
    yol = os.path.join(BELGE_KLASORU, belge["dosya"])
    if os.path.exists(yol):
        os.remove(yol)


@app.route("/belgeler", methods=["GET", "POST"])
def belgeler():
    kulupler = veri.kulupleri_getir()
    kulup_isimleri = {k["id"]: k["isim"] for k in kulupler}

    if request.method == "POST":
        kulup_id = request.form.get("kulup_id", "")
        tur = request.form.get("tur", "")
        aciklama = request.form.get("aciklama", "").strip()
        dosya = request.files.get("dosya")

        if kulup_id not in kulup_isimleri:
            flash("Lütfen bir kulüp seçin.", "hata")
        elif tur not in BELGE_TURLERI:
            flash("Lütfen belge türünü seçin.", "hata")
        elif not dosya or not dosya.filename:
            flash("Lütfen yüklenecek dosyayı seçin.", "hata")
        elif _uzanti(dosya.filename) not in BELGE_UZANTILARI:
            flash("Bu dosya türü desteklenmiyor.", "hata")
        else:
            os.makedirs(BELGE_KLASORU, exist_ok=True)
            belge_id = uuid4().hex
            kayit_adi = f"{belge_id}.{_uzanti(dosya.filename)}"
            dosya.save(os.path.join(BELGE_KLASORU, kayit_adi))
            veri.belge_ekle({
                "id": belge_id,
                "kulup_id": kulup_id,
                "tur": tur,
                "aciklama": aciklama,
                "orijinal_ad": secure_filename(dosya.filename) or kayit_adi,
                "dosya": kayit_adi,
                "boyut": os.path.getsize(os.path.join(BELGE_KLASORU, kayit_adi)),
                "yukleyen": session.get("ad_soyad", ""),
                "yukleme_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            flash("Belge yüklendi.", "basarili")
        return redirect(url_for("belgeler", kulup=kulup_id))

    secili = request.args.get("kulup", "")
    liste = veri.belgeleri_getir(secili or None)
    for belge in liste:
        belge["kulup_isim"] = kulup_isimleri.get(belge["kulup_id"], "—")
    return render_template(
        "belgeler.html",
        belgeler=liste,
        kulupler=kulupler,
        secili_kulup=secili,
        belge_turleri=BELGE_TURLERI,
        uzantilar=", ".join(sorted(BELGE_UZANTILARI)),
    )


@app.route("/belgeler/<belge_id>/indir")
def belge_indir(belge_id):
    belge = veri.belge_getir(belge_id)
    if belge is None:
        abort(404)
    return send_from_directory(BELGE_KLASORU, belge["dosya"], as_attachment=True,
                               download_name=belge["orijinal_ad"])


@app.route("/belgeler/<belge_id>/sil", methods=["POST"])
def belge_sil(belge_id):
    belge = veri.belge_getir(belge_id)
    if belge is None:
        abort(404)
    veri.belge_sil(belge_id)
    _belge_dosyasini_sil(belge)
    flash("Belge silindi.", "basarili")
    return redirect(_guvenli_yonlendirme(request.form.get("geri")) if request.form.get("geri")
                    else url_for("belgeler"))


@app.template_filter("boyut")
def boyut_filtresi(bayt):
    for birim in ("B", "KB", "MB"):
        if bayt < 1024:
            return f"{bayt:.0f} {birim}"
        bayt /= 1024
    return f"{bayt:.1f} GB"


@app.template_filter("tarih")
def tarih_filtresi(deger):
    """'2026-10-24' -> '24.10.2026' (boşsa boş döner)."""
    try:
        return datetime.strptime(deger[:10], "%Y-%m-%d").strftime("%d.%m.%Y") + deger[10:]
    except (TypeError, ValueError):
        return deger or ""


if __name__ == "__main__":
    # debug=True: kod değiştikçe sunucu otomatik yeniden başlar.
    app.run(debug=True)
