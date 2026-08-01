"""
Öğrenci Kulüpleri Portalı - Prototip
--------------------------------------
Bu dosya, Flask web çatısını (framework) kullanarak çalışan basit bir
web sunucusu oluşturur. Sunucu, data/clubs.json dosyasındaki kulüp
verilerini okur ve HTML sayfaları olarak tarayıcıda gösterir.

Nasıl çalıştırılır (VS Code terminalinde):
    1) pip install flask
    2) python app.py
    3) Tarayıcıda http://127.0.0.1:5000 adresini açın
"""

import json
import os
from datetime import datetime
from flask import Flask, render_template, abort, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

# Flask uygulamasını başlatıyoruz.
app = Flask(__name__)

# Oturum (session) bilgilerini şifrelemek için gizli bir anahtar gerekiyor.
# Gerçek bir yayında bu değer ortam değişkeninden okunmalı, prototipte sabit yazıyoruz.
app.secret_key = "prototip-gizli-anahtar-degistirin"

# JSON veri dosyalarının yolu
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "clubs.json")
FORUM_PATH = os.path.join(os.path.dirname(__file__), "data", "forum.json")
KULLANICI_PATH = os.path.join(os.path.dirname(__file__), "data", "kullanicilar.json")
UYELIK_PATH = os.path.join(os.path.dirname(__file__), "data", "uyelikler.json")


def kulupleri_yukle():
    """data/clubs.json dosyasını okuyup Python sözlüğüne (dict) çevirir.

    Dosyada bir sözdizimi hatası varsa (eksik/fazla virgül, kapanmamış
    tırnak vb.), sitenin tamamen çökmesi yerine sade bir "sayfa
    bulunamadı" (404) sayfası gösterilir.
    """
    with open(DATA_PATH, "r", encoding="utf-8") as dosya:
        try:
            return json.load(dosya)["kulupler"]
        except json.JSONDecodeError:
            abort(404)


def forum_yukle():
    """data/forum.json dosyasını okur. Dosya yoksa boş bir sözlük döndürür."""
    if not os.path.exists(FORUM_PATH):
        return {}
    with open(FORUM_PATH, "r", encoding="utf-8") as dosya:
        try:
            return json.load(dosya)
        except json.JSONDecodeError:
            return {}


def forum_kaydet(veri):
    """Forum verisini data/forum.json dosyasına yazar."""
    with open(FORUM_PATH, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False, indent=2)


def kullanicilari_yukle():
    """data/kullanicilar.json dosyasını okur. Dosya yoksa boş liste döndürür."""
    if not os.path.exists(KULLANICI_PATH):
        return []
    with open(KULLANICI_PATH, "r", encoding="utf-8") as dosya:
        try:
            return json.load(dosya)
        except json.JSONDecodeError:
            return []


def kullanicilari_kaydet(veri):
    """Kullanıcı listesini data/kullanicilar.json dosyasına yazar."""
    with open(KULLANICI_PATH, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False, indent=2)


def uyelikleri_yukle():
    """data/uyelikler.json dosyasını okur. Yapı: {kulup_id: {"onaylanan": [...], "bekleyen": [...]}}"""
    if not os.path.exists(UYELIK_PATH):
        return {}
    with open(UYELIK_PATH, "r", encoding="utf-8") as dosya:
        try:
            return json.load(dosya)
        except json.JSONDecodeError:
            return {}


def uyelikleri_kaydet(veri):
    """Üyelik verisini data/uyelikler.json dosyasına yazar."""
    with open(UYELIK_PATH, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False, indent=2)


def uyelik_durumu(uyelik_verisi, kulup_id, kullanici_adi):
    """Bir kullanıcının bir kulüpteki durumunu döndürür: 'uye', 'bekliyor' veya 'yok'."""
    kulup_uyelik = uyelik_verisi.get(kulup_id, {"onaylanan": [], "bekleyen": []})
    if kullanici_adi in kulup_uyelik.get("onaylanan", []):
        return "uye"
    if kullanici_adi in kulup_uyelik.get("bekleyen", []):
        return "bekliyor"
    return "yok"


@app.errorhandler(404)
def sayfa_bulunamadi(hata):
    """Geçersiz adres veya bozuk veri dosyası durumunda gösterilecek sade hata sayfası."""
    return render_template("error.html"), 404


@app.errorhandler(403)
def yetkisiz_erisim(hata):
    """Yetkisi olmayan bir işlem denendiğinde gösterilecek hata sayfası."""
    return render_template("error.html"), 403


@app.route("/")
def anasayfa():
    """Ana sayfa: tüm kulüpleri kart (grid) şeklinde listeler."""
    kulupler = kulupleri_yukle()
    return render_template("index.html", kulupler=kulupler)


@app.route("/belgeler")
def belgeler():
    """Kulüp kurma/etkinlik başvurusu gibi resmi belgelerin indirilebildiği sayfa."""
    return render_template("belgeler.html")


@app.route("/kulup/<kulup_id>")
def kulup_detay(kulup_id):
    """Bir kulübün detay sayfası: logo, başkan, yönetim kurulu, etkinlikler, forum."""
    kulupler = kulupleri_yukle()

    # Gelen id'ye (örn. 'dans') sahip kulübü listede arıyoruz.
    kulup = next((k for k in kulupler if k["id"] == kulup_id), None)

    if kulup is None:
        # Kulüp bulunamazsa 404 (Sayfa Bulunamadı) hatası döndürülür.
        abort(404)

    # Etkinlikleri geçmiş / gelecek olarak iki ayrı listeye ayırıyoruz.
    gecmis_etkinlikler = [e for e in kulup["etkinlikler"] if e["durum"] == "gecmis"]
    gelecek_etkinlikler = [e for e in kulup["etkinlikler"] if e["durum"] == "gelecek"]

    # Bu kulübe ait forum mesajlarını yüklüyoruz (yoksa boş liste).
    forum_verisi = forum_yukle()
    mesajlar = forum_verisi.get(kulup_id, [])

    # Kullanıcının bu kulüpteki üyelik durumu (uye / bekliyor / yok).
    uyelik_verisi = uyelikleri_yukle()
    durum = "yok"
    if "kullanici_adi" in session:
        durum = uyelik_durumu(uyelik_verisi, kulup_id, session["kullanici_adi"])

    # Bu kulübün başkanı, giriş yapmış kullanıcının kendisiyse (kulüp
    # verisinde "baskan_kullanici_adi" alanı tanımlıysa) bekleyen
    # istekleri de gösteriyoruz.
    bekleyen_istekler = []
    kulup_baskani_mi = False
    if "kullanici_adi" in session and session["kullanici_adi"] == kulup.get("baskan_kullanici_adi"):
        kulup_baskani_mi = True
        bekleyen_istekler = uyelik_verisi.get(kulup_id, {}).get("bekleyen", [])

    uye_sayisi = len(uyelik_verisi.get(kulup_id, {}).get("onaylanan", []))

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
    )


@app.route("/kulup/<kulup_id>/katil", methods=["POST"])
def kulube_katil(kulup_id):
    """Giriş yapmış bir kullanıcının bir kulübe katılma isteği göndermesi."""
    kulupler = kulupleri_yukle()
    kulup = next((k for k in kulupler if k["id"] == kulup_id), None)
    if kulup is None:
        abort(404)

    if "kullanici_adi" not in session:
        return redirect(url_for("giris_yap"))

    kullanici_adi = session["kullanici_adi"]
    uyelik_verisi = uyelikleri_yukle()

    if kulup_id not in uyelik_verisi:
        uyelik_verisi[kulup_id] = {"onaylanan": [], "bekleyen": []}

    zaten_uye = kullanici_adi in uyelik_verisi[kulup_id]["onaylanan"]
    zaten_bekliyor = kullanici_adi in uyelik_verisi[kulup_id]["bekleyen"]

    if not zaten_uye and not zaten_bekliyor:
        uyelik_verisi[kulup_id]["bekleyen"].append(kullanici_adi)
        uyelikleri_kaydet(uyelik_verisi)

    return redirect(url_for("kulup_detay", kulup_id=kulup_id))


@app.route("/kulup/<kulup_id>/onayla", methods=["POST"])
def uyelik_onayla(kulup_id):
    """Kulüp başkanının bekleyen bir üyelik isteğini onaylaması."""
    kulupler = kulupleri_yukle()
    kulup = next((k for k in kulupler if k["id"] == kulup_id), None)
    if kulup is None:
        abort(404)

    # Sadece o kulübün başkanı (giriş yapmış ve kullanıcı adı eşleşen kişi) onaylayabilir.
    if session.get("kullanici_adi") != kulup.get("baskan_kullanici_adi"):
        abort(403)

    onaylanacak_kullanici = request.form.get("kullanici_adi", "").strip()
    uyelik_verisi = uyelikleri_yukle()
    kulup_uyelik = uyelik_verisi.get(kulup_id, {"onaylanan": [], "bekleyen": []})

    if onaylanacak_kullanici in kulup_uyelik["bekleyen"]:
        kulup_uyelik["bekleyen"].remove(onaylanacak_kullanici)
        if onaylanacak_kullanici not in kulup_uyelik["onaylanan"]:
            kulup_uyelik["onaylanan"].append(onaylanacak_kullanici)
        uyelik_verisi[kulup_id] = kulup_uyelik
        uyelikleri_kaydet(uyelik_verisi)

    return redirect(url_for("kulup_detay", kulup_id=kulup_id))


@app.route("/kulup/<kulup_id>/reddet", methods=["POST"])
def uyelik_reddet(kulup_id):
    """Kulüp başkanının bekleyen bir üyelik isteğini reddetmesi."""
    kulupler = kulupleri_yukle()
    kulup = next((k for k in kulupler if k["id"] == kulup_id), None)
    if kulup is None:
        abort(404)

    if session.get("kullanici_adi") != kulup.get("baskan_kullanici_adi"):
        abort(403)

    reddedilecek_kullanici = request.form.get("kullanici_adi", "").strip()
    uyelik_verisi = uyelikleri_yukle()
    kulup_uyelik = uyelik_verisi.get(kulup_id, {"onaylanan": [], "bekleyen": []})

    if reddedilecek_kullanici in kulup_uyelik["bekleyen"]:
        kulup_uyelik["bekleyen"].remove(reddedilecek_kullanici)
        uyelik_verisi[kulup_id] = kulup_uyelik
        uyelikleri_kaydet(uyelik_verisi)

    return redirect(url_for("kulup_detay", kulup_id=kulup_id))


@app.route("/kayit", methods=["GET", "POST"])
def kayit_ol():
    """Yeni öğrenci hesabı oluşturma sayfası."""
    hata = None
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "").strip()

        if not kullanici_adi or not sifre:
            hata = "Kullanıcı adı ve şifre boş bırakılamaz."
        else:
            kullanicilar = kullanicilari_yukle()
            if any(k["kullanici_adi"].lower() == kullanici_adi.lower() for k in kullanicilar):
                hata = "Bu kullanıcı adı zaten alınmış."
            else:
                kullanicilar.append({
                    "kullanici_adi": kullanici_adi,
                    "sifre_hash": generate_password_hash(sifre),
                })
                kullanicilari_kaydet(kullanicilar)
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

        kullanicilar = kullanicilari_yukle()
        kullanici = next(
            (k for k in kullanicilar if k["kullanici_adi"].lower() == kullanici_adi.lower()),
            None,
        )

        if kullanici and check_password_hash(kullanici["sifre_hash"], sifre):
            session["kullanici_adi"] = kullanici["kullanici_adi"]
            return redirect(url_for("anasayfa"))
        else:
            hata = "Kullanıcı adı veya şifre hatalı."

    return render_template("giris.html", hata=hata)


@app.route("/cikis")
def cikis_yap():
    """Oturumu kapatır (çıkış yapar)."""
    session.pop("kullanici_adi", None)
    return redirect(url_for("anasayfa"))


@app.route("/kulup/<kulup_id>/forum", methods=["POST"])
def forum_mesaj_gonder(kulup_id):
    """Forum sekmesinden gönderilen yeni bir mesajı kaydeder. Sadece giriş yapmış kullanıcılar mesaj gönderebilir."""
    kulupler = kulupleri_yukle()
    kulup = next((k for k in kulupler if k["id"] == kulup_id), None)
    if kulup is None:
        abort(404)

    # Giriş yapılmamışsa mesaj kaydedilmez, giriş sayfasına yönlendirilir.
    if "kullanici_adi" not in session:
        return redirect(url_for("giris_yap"))

    mesaj = request.form.get("mesaj", "").strip()

    if mesaj:
        forum_verisi = forum_yukle()
        if kulup_id not in forum_verisi:
            forum_verisi[kulup_id] = []
        forum_verisi[kulup_id].append({
            "isim": session["kullanici_adi"],
            "mesaj": mesaj,
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
        })
        forum_kaydet(forum_verisi)

    # Mesaj gönderildikten sonra kullanıcıyı yine aynı kulübün forum
    # sekmesine geri yönlendiriyoruz (#forum ile hangi sekmenin açık
    # kalacağını tabs.js belirliyor).
    return redirect(url_for("kulup_detay", kulup_id=kulup_id) + "#forum")


if __name__ == "__main__":
    # debug=True: kod değiştikçe sunucu otomatik yeniden başlar (geliştirme için).
    app.run(debug=True)