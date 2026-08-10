"""
Öğrenci Kulüpleri Portalı - Prototip
--------------------------------------
Bu dosya, Flask web çatısını (framework) kullanarak çalışan basit bir
web sunucusu oluşturur. Sunucu, verileri (kulüpler, üyelikler,
kullanıcılar, forum mesajları) MySQL'deki kulup_portali veritabanından
okur ve HTML sayfaları olarak tarayıcıda gösterir.

Nasıl çalıştırılır (VS Code terminalinde):
    1) pip install -r requirements.txt
    2) MySQL sunucusunun (ör. MySQL Workbench ile bağlandığın sunucu)
       çalıştığından emin ol (bkz. veritabani.py için bağlantı bilgileri)
    3) python app.py
    4) Tarayıcıda http://127.0.0.1:5000 adresini açın
"""

import os
from uuid import uuid4
from datetime import datetime
from flask import Flask, render_template, abort, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from kufur_filtresi import uygunsuz_icerik_mi
from ogrenci_no import gecerli_mi as ogrenci_no_gecerli_mi
import veritabani as db

# Sunucu her başladığında veritabanını ve tabloları garantiye alır
db.init_db()

# Flask uygulamasını başlatıyoruz.
app = Flask(__name__)

# Oturum (session) bilgilerini şifrelemek için gizli bir anahtar gerekiyor.
# Gerçek bir yayında bu değer ortam değişkeninden okunmalı, prototipte sabit yazıyoruz.
app.secret_key = "prototip-gizli-anahtar-degistirin"


@app.errorhandler(404)
def sayfa_bulunamadi(hata):
    """Geçersiz adres durumunda gösterilecek sade hata sayfası."""
    return render_template("error.html"), 404


@app.errorhandler(403)
def yetkisiz_erisim(hata):
    """Yetkisi olmayan bir işlem denendiğinde gösterilecek hata sayfası."""
    return render_template("error.html"), 403


@app.route("/")
def anasayfa():
    """Ana sayfa: tüm kulüpleri kart (grid) şeklinde listeler."""
    kulupler = db.kulupleri_getir()
    return render_template("index.html", kulupler=kulupler)


@app.route("/belgeler")
def belgeler():
    """Kulüp kurma/etkinlik başvurusu gibi resmi belgelerin indirilebildiği sayfa."""
    return render_template("belgeler.html")


@app.route("/kulup/<kulup_id>")
def kulup_detay(kulup_id):
    """Bir kulübün detay sayfası: logo, başkan, yönetim kurulu, etkinlikler, forum."""
    kulup = db.kulup_getir(kulup_id)
    if kulup is None:
        abort(404)

    # Etkinlikleri geçmiş / gelecek olarak iki ayrı listeye ayırıyoruz.
    gecmis_etkinlikler = [e for e in kulup["etkinlikler"] if e["durum"] == "gecmis"]
    gelecek_etkinlikler = [e for e in kulup["etkinlikler"] if e["durum"] == "gelecek"]

    # Bu kulübe ait forum mesajlarını yüklüyoruz (yoksa boş liste).
    mesajlar = db.forum_yukle(kulup_id)

    # Kullanıcının bu kulüpteki üyelik durumu (uye / bekliyor / yok).
    durum = "yok"
    if "kullanici_adi" in session:
        durum = db.uyelik_durumu(kulup_id, session["kullanici_adi"])

    # Bu kulübün başkanı, giriş yapmış kullanıcının kendisiyse (kulüp
    # verisinde "baskan_kullanici_adi" alanı tanımlıysa) bekleyen
    # istekleri ve onaylı üye listesini de gösteriyoruz.
    bekleyen_istekler = []
    onayli_uyeler = []
    kulup_baskani_mi = False
    if "kullanici_adi" in session and session["kullanici_adi"] == kulup.get("baskan_kullanici_adi"):
        kulup_baskani_mi = True
        bekleyen_istekler = db.bekleyen_istekleri_getir(kulup_id)
        onayli_uyeler = db.onayli_uyeleri_getir(kulup_id)

    uye_sayisi = db.uye_sayisi_getir(kulup_id)

    return render_template(
        "club_detail.html",
        kulup=kulup,
        gecmis_etkinlikler=gecmis_etkinlikler,
        gelecek_etkinlikler=gelecek_etkinlikler,
        mesajlar=mesajlar,
        uyelik_durumu=durum,
        uye_sayisi=uye_sayisi,
        kulup_baskani_mi=kulup_baskani_mi,
        bekleyen_istekler=bekleyen_istekler,
        onayli_uyeler=onayli_uyeler,
    )


@app.route("/kulup/<kulup_id>/katil", methods=["POST"])
def kulube_katil(kulup_id):
    """Giriş yapmış bir kullanıcının bir kulübe katılma isteği göndermesi."""
    kulup = db.kulup_ozet_getir(kulup_id)
    if kulup is None:
        abort(404)

    if "kullanici_adi" not in session:
        return redirect(url_for("giris_yap"))

    db.uyelik_basvurusu_ekle(kulup_id, session["kullanici_adi"])

    return redirect(url_for("kulup_detay", kulup_id=kulup_id))


@app.route("/kulup/<kulup_id>/onayla", methods=["POST"])
def uyelik_onayla(kulup_id):
    """Kulüp başkanının bekleyen bir üyelik isteğini onaylaması."""
    kulup = db.kulup_ozet_getir(kulup_id)
    if kulup is None:
        abort(404)

    # Sadece o kulübün başkanı (giriş yapmış ve kullanıcı adı eşleşen kişi) onaylayabilir.
    if session.get("kullanici_adi") != kulup.get("baskan_kullanici_adi"):
        abort(403)

    onaylanacak_kullanici = request.form.get("kullanici_adi", "").strip()
    db.uyelik_onayla(kulup_id, onaylanacak_kullanici)

    return redirect(url_for("kulup_detay", kulup_id=kulup_id))


@app.route("/kulup/<kulup_id>/reddet", methods=["POST"])
def uyelik_reddet(kulup_id):
    """Kulüp başkanının bekleyen bir üyelik isteğini reddetmesi."""
    kulup = db.kulup_ozet_getir(kulup_id)
    if kulup is None:
        abort(404)

    if session.get("kullanici_adi") != kulup.get("baskan_kullanici_adi"):
        abort(403)

    reddedilecek_kullanici = request.form.get("kullanici_adi", "").strip()
    db.uyelik_reddet(kulup_id, reddedilecek_kullanici)

    return redirect(url_for("kulup_detay", kulup_id=kulup_id))


@app.route("/kulup/<kulup_id>/etkinlik-ekle", methods=["POST"])
def etkinlik_ekle(kulup_id):
    """Kulüp başkanının kulübüne elle yeni bir etkinlik (foto, başlık, açıklama) eklemesi."""
    kulup = db.kulup_ozet_getir(kulup_id)
    if kulup is None:
        abort(404)

    if session.get("kullanici_adi") != kulup.get("baskan_kullanici_adi"):
        abort(403)

    baslik = request.form.get("baslik", "").strip()
    aciklama = request.form.get("aciklama", "").strip()
    tarih = request.form.get("tarih", "").strip()

    if not baslik or not aciklama or not tarih:
        flash("Başlık, açıklama ve tarih boş bırakılamaz.", "hata")
        return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#etkinlikler")

    try:
        etkinlik_tarihi = datetime.strptime(tarih, "%Y-%m-%d").date()
    except ValueError:
        flash("Geçerli bir tarih seçmelisiniz.", "hata")
        return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#etkinlikler")

    durum = "gelecek" if etkinlik_tarihi >= datetime.now().date() else "gecmis"

    gorsel_adi = None
    foto = request.files.get("foto")
    if foto and foto.filename:
        dosya_adi = secure_filename(foto.filename)
        gorsel_adi = f"{kulup_id}-{uuid4().hex}-{dosya_adi}"
        etkinlik_klasoru = os.path.join(app.static_folder, "images", "events")
        os.makedirs(etkinlik_klasoru, exist_ok=True)
        foto.save(os.path.join(etkinlik_klasoru, gorsel_adi))

    db.etkinlik_ekle(kulup_id, baslik, tarih, durum, aciklama, gorsel_adi)

    return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#etkinlikler")


@app.route("/kayit", methods=["GET", "POST"])
def kayit_ol():
    """Yeni öğrenci hesabı oluşturma sayfası."""
    hata = None
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "").strip()

        if not kullanici_adi or not sifre:
            hata = "Kullanıcı adı ve şifre boş bırakılamaz."
        elif not ogrenci_no_gecerli_mi(kullanici_adi):
            hata = "Kullanıcı adı öğrenci numaranız olmalı (9 haneli, 20-26 ile başlamalı)."
        elif db.kullanici_bul(kullanici_adi):
            hata = "Bu kullanıcı adı zaten alınmış."
        else:
            db.kullanici_ekle(kullanici_adi, generate_password_hash(sifre))
            # Kayıt olduktan hemen sonra otomatik giriş yapılmış sayılır.
            session["kullanici_adi"] = kullanici_adi
            return redirect(url_for("anasayfa"))

    return render_template("kayit.html", hata=hata)


@app.route("/giris", methods=["GET", "POST"])
def giris_yap():
    """Öğrenci giriş sayfası."""
    hata = None
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "").strip()

        kullanici = db.kullanici_bul(kullanici_adi)

        if kullanici and check_password_hash(kullanici["sifre_hash"], sifre):
            session["kullanici_adi"] = kullanici["kullanici_adi"]
            return redirect(url_for("anasayfa"))
        else:
            hata = "Kullanıcı adı veya şifre hatalı."

    return render_template("giris.html", hata=hata)


@app.route("/sifremi-unuttum", methods=["GET", "POST"])
def sifremi_unuttum():
    """Şifresini unutan öğrencinin öğrenci numarasıyla yeni şifre belirlemesi."""
    hata = None
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        yeni_sifre = request.form.get("yeni_sifre", "").strip()
        yeni_sifre_tekrar = request.form.get("yeni_sifre_tekrar", "").strip()

        kullanici = db.kullanici_bul(kullanici_adi)

        if not kullanici:
            hata = "Bu kullanıcı adıyla kayıtlı bir hesap bulunamadı."
        elif not yeni_sifre or not yeni_sifre_tekrar:
            hata = "Yeni şifre boş bırakılamaz."
        elif yeni_sifre != yeni_sifre_tekrar:
            hata = "Girdiğiniz şifreler birbiriyle uyuşmuyor."
        else:
            db.kullanici_sifre_guncelle(kullanici["kullanici_adi"], generate_password_hash(yeni_sifre))
            flash("Şifreniz güncellendi, yeni şifrenizle giriş yapabilirsiniz.", "basarili")
            return redirect(url_for("giris_yap"))

    return render_template("sifremi_unuttum.html", hata=hata)


@app.route("/cikis")
def cikis_yap():
    """Oturumu kapatır (çıkış yapar)."""
    session.pop("kullanici_adi", None)
    return redirect(url_for("anasayfa"))


@app.route("/kulup/<kulup_id>/forum", methods=["POST"])
def forum_mesaj_gonder(kulup_id):
    """Forum sekmesinden gönderilen yeni bir mesajı kaydeder. Sadece giriş yapmış kullanıcılar mesaj gönderebilir."""
    kulup = db.kulup_ozet_getir(kulup_id)
    if kulup is None:
        abort(404)

    # Giriş yapılmamışsa mesaj kaydedilmez, giriş sayfasına yönlendirilir.
    if "kullanici_adi" not in session:
        return redirect(url_for("giris_yap"))

    mesaj = request.form.get("mesaj", "").strip()

    if mesaj:
        if uygunsuz_icerik_mi(mesaj):
            flash("Mesajın küfür/argo içerdiği için gönderilemedi.", "hata")
        else:
            db.forum_kaydet(kulup_id, session["kullanici_adi"], mesaj)

    # Mesaj gönderildikten sonra kullanıcıyı yine aynı kulübün forum
    # sekmesine geri yönlendiriyoruz.
    return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#forum")


if __name__ == "__main__":
    # debug=True: kod değiştikçe sunucu otomatik yeniden başlar.
    app.run(debug=True)
