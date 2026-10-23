"""Öğrenci Dekanlığı Kulüp Paneli - JSON veri erişim katmanı.

Tüm veriler data/ klasöründeki JSON dosyalarında tutulur:
    clubs.json        -> kulüp bilgileri, yönetim kurulu, danışman, durum
    uyelikler.json    -> kulüp başına üye öğrenci numaraları ve katılım tarihleri
    ogrenciler.json   -> öğrenci no -> ad soyad, bölüm, sınıf, telefon, e-posta
    kullanicilar.json -> panele giriş yapabilen kullanıcılar (rol alanıyla)
    belgeler.json     -> kulüplere yüklenen evrakların listesi

Yazma işlemleri önce geçici bir dosyaya yapılıp sonra yerine taşınır;
böylece yazma yarıda kesilirse JSON dosyası bozulmaz.
"""

import json
import os
import threading
from datetime import date

VERI_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Aynı anda gelen iki istek aynı dosyayı yazmaya çalışmasın diye tek kilit.
_kilit = threading.RLock()

PANEL_ROLLERI = {"dekan", "yetkili"}
OGRENCI_ALANLARI = ("ad_soyad", "bolum", "sinif", "telefon", "eposta")


def _yol(dosya_adi):
    return os.path.join(VERI_KLASORU, dosya_adi)


def _yukle(dosya_adi, varsayilan):
    try:
        with open(_yol(dosya_adi), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return varsayilan


def _kaydet(dosya_adi, veri):
    gecici = _yol(dosya_adi) + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(gecici, _yol(dosya_adi))


# ---------------------------------------------------------------------------
# Kulüpler
# ---------------------------------------------------------------------------

def _kulup_varsayilanlari(kulup):
    """Eski kayıtlarda olmayan alanları varsayılan değerlerle tamamlar."""
    kulup.setdefault("durum", "aktif")
    kulup.setdefault("danisman", {})
    for alan in ("isim", "eposta", "telefon"):
        kulup["danisman"].setdefault(alan, "")
    kulup.setdefault("yonetim_kurulu", [])
    kulup.setdefault("aciklama", "")
    kulup.setdefault("logo", "")
    return kulup


def kulupleri_getir():
    """Tüm kulüpleri, üye sayılarıyla birlikte isme göre sıralı döndürür."""
    with _kilit:
        kulupler = _yukle("clubs.json", {"kulupler": []})["kulupler"]
        uyelikler = _yukle("uyelikler.json", {})
    for kulup in kulupler:
        _kulup_varsayilanlari(kulup)
        kulup["uye_sayisi"] = len(uyelikler.get(kulup["id"], {}).get("onaylanan", []))
    return sorted(kulupler, key=lambda k: k["isim"].lower())


def kulup_getir(kulup_id):
    for kulup in kulupleri_getir():
        if kulup["id"] == kulup_id:
            return kulup
    return None


def kategorileri_getir():
    return sorted({k["kategori"] for k in kulupleri_getir() if k.get("kategori")})


def kulup_kaydet(kulup):
    """Yeni kulübü ekler ya da aynı id'li kulübü günceller.

    Formda olmayan alanlar (ör. eski etkinlikler, kapak görseli) korunur.
    """
    kulup = {k: v for k, v in kulup.items() if k != "uye_sayisi"}
    with _kilit:
        veri = _yukle("clubs.json", {"kulupler": []})
        for i, mevcut in enumerate(veri["kulupler"]):
            if mevcut["id"] == kulup["id"]:
                mevcut.update(kulup)
                veri["kulupler"][i] = mevcut
                break
        else:
            veri["kulupler"].append(kulup)
        _kaydet("clubs.json", veri)


def kulup_sil(kulup_id):
    """Kulübü, üyelik kayıtlarını ve belge kayıtlarını siler.

    Silinen belgelerin dosya adlarını döndürür (dosyaları app.py siler).
    Öğrenci bilgileri (ogrenciler.json) başka kulüpler için korunur.
    """
    with _kilit:
        veri = _yukle("clubs.json", {"kulupler": []})
        veri["kulupler"] = [k for k in veri["kulupler"] if k["id"] != kulup_id]
        _kaydet("clubs.json", veri)

        uyelikler = _yukle("uyelikler.json", {})
        if uyelikler.pop(kulup_id, None) is not None:
            _kaydet("uyelikler.json", uyelikler)

        belgeler = _yukle("belgeler.json", [])
        silinenler = [b for b in belgeler if b["kulup_id"] == kulup_id]
        if silinenler:
            _kaydet("belgeler.json", [b for b in belgeler if b["kulup_id"] != kulup_id])
    return silinenler


# ---------------------------------------------------------------------------
# Üyeler
# ---------------------------------------------------------------------------

def _uye_satiri(ogrenci_no, ogrenciler, katilim_tarihi=""):
    bilgi = ogrenciler.get(ogrenci_no, {})
    satir = {"ogrenci_no": ogrenci_no, "katilim_tarihi": katilim_tarihi}
    for alan in OGRENCI_ALANLARI:
        satir[alan] = bilgi.get(alan, "")
    return satir


def uyeleri_getir(kulup_id):
    """Bir kulübün onaylı üyelerini öğrenci bilgileriyle birlikte döndürür."""
    with _kilit:
        kayit = _yukle("uyelikler.json", {}).get(kulup_id, {})
        ogrenciler = _yukle("ogrenciler.json", {})
    tarihler = kayit.get("katilim_tarihleri", {})
    return [_uye_satiri(no, ogrenciler, tarihler.get(no, "")) for no in kayit.get("onaylanan", [])]


def tum_uyeleri_getir():
    """Tüm kulüplerdeki üyelikleri tek liste olarak döndürür.

    Her satıra, öğrencinin üye olduğu tüm kulüplerin listesi (kulupleri) eklenir;
    böylece birden fazla kulüpteki öğrenciler işaretlenebilir.
    """
    kulup_isimleri = {k["id"]: k["isim"] for k in kulupleri_getir()}
    with _kilit:
        uyelikler = _yukle("uyelikler.json", {})
        ogrenciler = _yukle("ogrenciler.json", {})

    ogrenci_kulupleri = {}
    for kulup_id, kayit in uyelikler.items():
        if kulup_id not in kulup_isimleri:
            continue
        for no in kayit.get("onaylanan", []):
            ogrenci_kulupleri.setdefault(no, []).append(kulup_isimleri[kulup_id])

    satirlar = []
    for kulup_id, kayit in uyelikler.items():
        if kulup_id not in kulup_isimleri:
            continue
        tarihler = kayit.get("katilim_tarihleri", {})
        for no in kayit.get("onaylanan", []):
            satir = _uye_satiri(no, ogrenciler, tarihler.get(no, ""))
            satir["kulup_id"] = kulup_id
            satir["kulup_isim"] = kulup_isimleri[kulup_id]
            satir["kulupleri"] = sorted(ogrenci_kulupleri[no])
            satirlar.append(satir)
    return satirlar


def son_eklenen_uyeler(adet=8):
    """Katılım tarihi olan üyeliklerden en yenilerini döndürür."""
    tarihli = [s for s in tum_uyeleri_getir() if s["katilim_tarihi"]]
    return sorted(tarihli, key=lambda s: s["katilim_tarihi"], reverse=True)[:adet]


def uye_mi(kulup_id, ogrenci_no):
    with _kilit:
        return ogrenci_no in _yukle("uyelikler.json", {}).get(kulup_id, {}).get("onaylanan", [])


def uye_kaydet(kulup_id, ogrenci_no, bilgiler, katilim_tarihi, eski_ogrenci_no=None):
    """Üyeyi ekler veya günceller.

    bilgiler: OGRENCI_ALANLARI'ndaki değerler. Öğrenci bilgileri tüm
    kulüplerde ortaktır; bir kulüpte düzenlemek diğerlerinde de günceller.
    eski_ogrenci_no verilirse ve farklıysa, numara değişikliği yapılır.
    """
    katilim_tarihi = katilim_tarihi or date.today().isoformat()
    with _kilit:
        uyelikler = _yukle("uyelikler.json", {})
        kayit = uyelikler.setdefault(kulup_id, {"onaylanan": [], "bekleyen": []})
        onaylanan = kayit.setdefault("onaylanan", [])
        tarihler = kayit.setdefault("katilim_tarihleri", {})

        if eski_ogrenci_no and eski_ogrenci_no != ogrenci_no and eski_ogrenci_no in onaylanan:
            onaylanan[onaylanan.index(eski_ogrenci_no)] = ogrenci_no
            tarihler.pop(eski_ogrenci_no, None)
        elif ogrenci_no not in onaylanan:
            onaylanan.append(ogrenci_no)
        # Yönetimden eklenen üye, varsa bekleyen başvurusundan çıkarılır.
        if ogrenci_no in kayit.get("bekleyen", []):
            kayit["bekleyen"].remove(ogrenci_no)
        tarihler[ogrenci_no] = katilim_tarihi
        _kaydet("uyelikler.json", uyelikler)

        ogrenciler = _yukle("ogrenciler.json", {})
        ogrenci = ogrenciler.get(ogrenci_no, {})
        if eski_ogrenci_no and eski_ogrenci_no != ogrenci_no and not ogrenci:
            ogrenci = ogrenciler.get(eski_ogrenci_no, {})
        ogrenci.update({alan: bilgiler.get(alan, "") for alan in OGRENCI_ALANLARI})
        ogrenciler[ogrenci_no] = ogrenci
        _kaydet("ogrenciler.json", ogrenciler)


def uye_sil(kulup_id, ogrenci_no):
    """Öğrenciyi yalnızca bu kulüpten çıkarır; öğrenci bilgileri korunur."""
    with _kilit:
        uyelikler = _yukle("uyelikler.json", {})
        kayit = uyelikler.get(kulup_id)
        if kayit and ogrenci_no in kayit.get("onaylanan", []):
            kayit["onaylanan"].remove(ogrenci_no)
            kayit.get("katilim_tarihleri", {}).pop(ogrenci_no, None)
            _kaydet("uyelikler.json", uyelikler)


# ---------------------------------------------------------------------------
# Kullanıcılar
# ---------------------------------------------------------------------------

def kullanici_bul(kullanici_adi):
    with _kilit:
        for kullanici in _yukle("kullanicilar.json", []):
            if kullanici["kullanici_adi"].lower() == kullanici_adi.lower():
                return kullanici
    return None


def panel_yetkilisi_mi(kullanici):
    return kullanici is not None and kullanici.get("rol") in PANEL_ROLLERI


def kullanici_sifre_guncelle(kullanici_adi, yeni_sifre_hash):
    with _kilit:
        kullanicilar = _yukle("kullanicilar.json", [])
        for kullanici in kullanicilar:
            if kullanici["kullanici_adi"].lower() == kullanici_adi.lower():
                kullanici["sifre_hash"] = yeni_sifre_hash
        _kaydet("kullanicilar.json", kullanicilar)


# ---------------------------------------------------------------------------
# Belgeler
# ---------------------------------------------------------------------------

def belgeleri_getir(kulup_id=None):
    with _kilit:
        belgeler = _yukle("belgeler.json", [])
    if kulup_id:
        belgeler = [b for b in belgeler if b["kulup_id"] == kulup_id]
    return sorted(belgeler, key=lambda b: b["yukleme_tarihi"], reverse=True)


def belge_getir(belge_id):
    for belge in belgeleri_getir():
        if belge["id"] == belge_id:
            return belge
    return None


def belge_ekle(belge):
    with _kilit:
        belgeler = _yukle("belgeler.json", [])
        belgeler.append(belge)
        _kaydet("belgeler.json", belgeler)


def belge_sil(belge_id):
    with _kilit:
        belgeler = _yukle("belgeler.json", [])
        _kaydet("belgeler.json", [b for b in belgeler if b["id"] != belge_id])
