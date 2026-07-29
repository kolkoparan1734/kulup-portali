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
from flask import Flask, render_template, abort

# Flask uygulamasını başlatıyoruz.
app = Flask(__name__)

# JSON veri dosyasının yolu
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "clubs.json")


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
    """Bir kulübün detay sayfası: logo, başkan, yönetim kurulu, etkinlikler."""
    kulupler = kulupleri_yukle()

    # Gelen id'ye (örn. 'yelken') sahip kulübü listede arıyoruz.
    kulup = next((k for k in kulupler if k["id"] == kulup_id), None)

    if kulup is None:
        # Kulüp bulunamazsa 404 (Sayfa Bulunamadı) hatası döndürülür.
        abort(404)

    # Etkinlikleri geçmiş / gelecek olarak iki ayrı listeye ayırıyoruz.
    gecmis_etkinlikler = [e for e in kulup["etkinlikler"] if e["durum"] == "gecmis"]
    gelecek_etkinlikler = [e for e in kulup["etkinlikler"] if e["durum"] == "gelecek"]

    return render_template(
        "club_detail.html",
        kulup=kulup,
        gecmis_etkinlikler=gecmis_etkinlikler,
        gelecek_etkinlikler=gelecek_etkinlikler,
    )


if __name__ == "__main__":
    # debug=True: kod değiştikçe sunucu otomatik yeniden başlar (geliştirme için).
    app.run(debug=True)
