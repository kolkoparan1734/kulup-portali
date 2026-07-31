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


@app.errorhandler(404)
def sayfa_bulunamadi(hata):
    """Geçersiz adres veya bozuk veri dosyası durumunda gösterilecek sade hata sayfası."""
    return render_template("error.html"), 404


@app.route("/")
def anasayfa():
    """Ana sayfa: tüm kulüpleri kart (grid) şeklinde listeler."""
    kulupler = kulupleri_yukle()
    return render_template("index.html", kulupler=kulupler)


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

    return render_template(
        "club_detail.html",
        kulup=kulup,
        gecmis_etkinlikler=gecmis_etkinlikler,
        gelecek_etkinlikler=gelecek_etkinlikler,
        mesajlar=mesajlar,
    )


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