"""Öğrenci Dekanlığı Kulüp Paneli - JSON veri erişim katmanı.

Tüm veriler data/ klasöründeki JSON dosyalarında tutulur:
    clubs.json        -> kulüp bilgileri, yönetim kurulu, danışman, durum
    uyelikler.json    -> kulüp başına üye öğrenci numaraları ve katılım tarihleri
    ogrenciler.json   -> öğrenci no -> ad soyad, bölüm, sınıf, telefon, e-posta
    kullanicilar.json -> panele giriş yapabilen kullanıcılar (rol alanıyla)
    belgeler.json     -> kulüplere yüklenen evrakların listesi (döneme bağlı)
    danismanlar.json  -> danışman hocalar; kulüpler danisman_id ile bağlanır
    donemler.json     -> akademik dönemler ve aktif dönem
    etkinlik_basvurulari.json -> kulüplerin etkinlik başvuruları ve dekanlık kararları
    zorunlu_evraklar.json -> dönem başına zorunlu evraklar, teslim tarihleri, elden teslimler
    gorev_gecmisi.json -> başkan/yönetim kurulu görev kayıtları (silinmez, kapatılır)
    karneler.json     -> dönem sonu dekanlık değerlendirmesi (1-5 puan + not)
    ayarlar.json      -> panel ayarları (kulüp başkanı girişi, oturum süresi)
    islem_gecmisi.json -> kim, ne zaman, hangi kayıtta neyi değiştirdi
    duyurular.json    -> kulüplere gönderilen duyuruların arşivi

Kulüp, belge ve etkinlik başvurusu silinmez; "arsiv" alanı eklenerek arşive
alınır. Arşivdeki kayıtlar (ve arşivdeki kulübün belgeleri/başvuruları)
normal listelerde görünmez; dekan geri getirebilir veya kalıcı silebilir.

Yazma işlemleri önce geçici bir dosyaya yapılıp sonra yerine taşınır;
böylece yazma yarıda kesilirse JSON dosyası bozulmaz.
"""

import glob
import json
import os
import shutil
import threading
from datetime import date, datetime
from uuid import uuid4

VERI_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Aynı anda gelen iki istek aynı dosyayı yazmaya çalışmasın diye tek kilit.
_kilit = threading.RLock()

ROLLER = {"dekan": "Dekan", "personel": "Dekanlık Personeli", "baskan": "Kulüp Başkanı"}
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


def yeni_id():
    return uuid4().hex[:12]


def yedek_al(etiket):
    """data/*.json dosyalarını data/yedek/<tarih>_<etiket>/ klasörüne kopyalar."""
    klasor = os.path.join(VERI_KLASORU, "yedek", f"{datetime.now():%Y-%m-%d_%H%M}_{etiket}")
    os.makedirs(klasor, exist_ok=True)
    with _kilit:
        for dosya in glob.glob(os.path.join(VERI_KLASORU, "*.json")):
            shutil.copy2(dosya, klasor)
    return klasor


# ---------------------------------------------------------------------------
# Dönemler
# ---------------------------------------------------------------------------

def _donem_verisi():
    return _yukle("donemler.json", {"aktif": "", "donemler": []})


def donemleri_getir():
    """Dönemleri en yeniden eskiye sıralı döndürür; aktif olanı işaretler."""
    with _kilit:
        veri = _donem_verisi()
    donemler = sorted(veri["donemler"], key=lambda d: d.get("baslangic", ""), reverse=True)
    for donem in donemler:
        donem["aktif"] = donem["id"] == veri["aktif"]
    return donemler


def donem_getir(donem_id):
    return next((d for d in donemleri_getir() if d["id"] == donem_id), None)


def aktif_donem():
    return next((d for d in donemleri_getir() if d["aktif"]), None)


def donem_kaydet(donem):
    donem = {k: v for k, v in donem.items() if k != "aktif"}
    with _kilit:
        veri = _donem_verisi()
        for mevcut in veri["donemler"]:
            if mevcut["id"] == donem["id"]:
                mevcut.update(donem)
                break
        else:
            veri["donemler"].append(donem)
        if not veri["aktif"]:
            veri["aktif"] = donem["id"]
        _kaydet("donemler.json", veri)


def donem_aktif_yap(donem_id):
    with _kilit:
        veri = _donem_verisi()
        if any(d["id"] == donem_id for d in veri["donemler"]):
            veri["aktif"] = donem_id
            _kaydet("donemler.json", veri)


def tarihin_donemi(tarih, donemler=None):
    """'YYYY-AA-GG...' tarihini kapsayan dönemi döndürür (yoksa None)."""
    gun = (tarih or "")[:10]
    for donem in donemler if donemler is not None else donemleri_getir():
        if donem.get("baslangic", "") <= gun <= donem.get("bitis", ""):
            return donem
    return None


def donem_kullanim_sayisi(donem_id):
    """Döneme bağlı kayıt sayısı (silmeden önce kontrol için)."""
    return (sum(1 for b in belgeleri_getir(arsiv=None) if b.get("donem_id") == donem_id)
            + len(zorunlu_evraklari_getir(donem_id)))


def donem_sil(donem_id):
    with _kilit:
        veri = _donem_verisi()
        veri["donemler"] = [d for d in veri["donemler"] if d["id"] != donem_id]
        _kaydet("donemler.json", veri)


# ---------------------------------------------------------------------------
# Danışmanlar
# ---------------------------------------------------------------------------

DANISMAN_ALANLARI = ("ad_soyad", "unvan", "fakulte", "bolum", "eposta", "telefon")


def _danisman_sozlugu():
    return {d["id"]: d for d in _yukle("danismanlar.json", [])}


def danisman_tam_adi(danisman):
    return " ".join(p for p in (danisman.get("unvan", ""), danisman.get("ad_soyad", "")) if p)


def danismanlari_getir():
    """Danışmanları, danışmanlık yaptıkları kulüplerle birlikte döndürür."""
    with _kilit:
        danismanlar = _yukle("danismanlar.json", [])
        kulupler = _yukle("clubs.json", {"kulupler": []})["kulupler"]
    for danisman in danismanlar:
        danisman["tam_ad"] = danisman_tam_adi(danisman)
        danisman["kulupler"] = sorted(
            ({"id": k["id"], "isim": k["isim"]} for k in kulupler if k.get("danisman_id") == danisman["id"]),
            key=lambda k: k["isim"].lower(),
        )
    return sorted(danismanlar, key=lambda d: d["ad_soyad"].lower())


def danisman_getir(danisman_id):
    return next((d for d in danismanlari_getir() if d["id"] == danisman_id), None)


def danisman_kaydet(danisman):
    danisman = {k: danisman.get(k, "") for k in ("id",) + DANISMAN_ALANLARI}
    with _kilit:
        danismanlar = _yukle("danismanlar.json", [])
        for mevcut in danismanlar:
            if mevcut["id"] == danisman["id"]:
                mevcut.update(danisman)
                break
        else:
            danismanlar.append(danisman)
        _kaydet("danismanlar.json", danismanlar)


def danisman_sil(danisman_id):
    """Danışmanı siler ve bağlı olduğu kulüplerden danışman bağlantısını kaldırır."""
    with _kilit:
        _kaydet("danismanlar.json", [d for d in _yukle("danismanlar.json", []) if d["id"] != danisman_id])
        veri = _yukle("clubs.json", {"kulupler": []})
        for kulup in veri["kulupler"]:
            if kulup.get("danisman_id") == danisman_id:
                kulup["danisman_id"] = ""
        _kaydet("clubs.json", veri)


# ---------------------------------------------------------------------------
# Kulüpler
# ---------------------------------------------------------------------------

# Kulüp kaydına yazılmayan, okurken hesaplanan alanlar.
_HESAPLANAN_KULUP_ALANLARI = {"uye_sayisi", "danisman"}


def _kulup_varsayilanlari(kulup, danismanlar):
    """Eski kayıtlarda olmayan alanları tamamlar, danışman bilgisini bağlar."""
    kulup.setdefault("durum", "aktif")
    kulup.setdefault("danisman_id", "")
    kulup.setdefault("yonetim_kurulu", [])
    kulup.setdefault("aciklama", "")
    kulup.setdefault("logo", "")
    danisman = danismanlar.get(kulup["danisman_id"], {})
    kulup["danisman"] = {
        "id": danisman.get("id", ""),
        "isim": danisman_tam_adi(danisman),
        "eposta": danisman.get("eposta", ""),
        "telefon": danisman.get("telefon", ""),
    }
    return kulup


def _arsiv_kaydi(kullanici):
    return {"tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "kullanici": kullanici}


def kulupleri_getir(arsiv=False):
    """Kulüpleri, üye sayılarıyla birlikte isme göre sıralı döndürür.

    arsiv=False: sadece arşivde olmayanlar, True: sadece arşivdekiler, None: hepsi.
    """
    with _kilit:
        kulupler = _yukle("clubs.json", {"kulupler": []})["kulupler"]
    if arsiv is not None:
        kulupler = [k for k in kulupler if bool(k.get("arsiv")) == arsiv]
    with _kilit:
        uyelikler = _yukle("uyelikler.json", {})
        danismanlar = _danisman_sozlugu()
    for kulup in kulupler:
        _kulup_varsayilanlari(kulup, danismanlar)
        kulup["uye_sayisi"] = len(uyelikler.get(kulup["id"], {}).get("onaylanan", []))
    return sorted(kulupler, key=lambda k: k["isim"].lower())


def kulup_getir(kulup_id):
    for kulup in kulupleri_getir():
        if kulup["id"] == kulup_id:
            return kulup
    return None


def tum_kulup_idleri():
    """Arşivdekiler dahil tüm kulüp id'leri (yeni id üretirken çakışmayı önlemek için)."""
    with _kilit:
        return {k["id"] for k in _yukle("clubs.json", {"kulupler": []})["kulupler"]}


def kulup_arsiv_ayarla(kulup_id, kullanici=None):
    """kullanici verilirse kulübü arşive alır, None ise arşivden çıkarır."""
    with _kilit:
        veri = _yukle("clubs.json", {"kulupler": []})
        for kulup in veri["kulupler"]:
            if kulup["id"] == kulup_id:
                if kullanici is None:
                    kulup.pop("arsiv", None)
                else:
                    kulup["arsiv"] = _arsiv_kaydi(kullanici)
        _kaydet("clubs.json", veri)


def kategorileri_getir():
    return sorted({k["kategori"] for k in kulupleri_getir() if k.get("kategori")})


def kulup_kaydet(kulup):
    """Yeni kulübü ekler ya da aynı id'li kulübü günceller.

    Formda olmayan alanlar (ör. eski etkinlikler, kapak görseli) korunur.
    """
    kulup = {k: v for k, v in kulup.items() if k not in _HESAPLANAN_KULUP_ALANLARI}
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
    """Kulübü, üyelik, belge ve etkinlik başvurusu kayıtlarını siler.

    (silinen belgeler, silinen başvuru ek dosyaları) döndürür; dosyaları app.py siler.
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

        basvurular = _yukle("etkinlik_basvurulari.json", [])
        ek_dosyalar = [d for b in basvurular if b["kulup_id"] == kulup_id for d in b.get("ek_dosyalar", [])]
        if any(b["kulup_id"] == kulup_id for b in basvurular):
            _kaydet("etkinlik_basvurulari.json", [b for b in basvurular if b["kulup_id"] != kulup_id])
    return silinenler, ek_dosyalar


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


def kullanici_rolu(kullanici):
    """Eski "yetkili" rolü dekanlık personeli sayılır."""
    rol = (kullanici or {}).get("rol", "")
    return "personel" if rol == "yetkili" else rol


def panel_yetkilisi_mi(kullanici):
    """Kullanıcı panele girebilir mi? (aktif, panel rolü var; başkansa giriş açık ve kulübü mevcut)"""
    if kullanici is None or not kullanici.get("aktif", True):
        return False
    rol = kullanici_rolu(kullanici)
    if rol == "baskan":
        return ayarlari_getir()["baskan_girisi"] and kulup_getir(kullanici.get("kulup_id", "")) is not None
    return rol in ROLLER


def panel_kullanicilari_getir():
    """Panel kullanıcıları (öğrenci hesapları hariç, şifre özetleri olmadan)."""
    with _kilit:
        kullanicilar = _yukle("kullanicilar.json", [])
    sonuc = []
    for k in kullanicilar:
        rol = kullanici_rolu(k)
        if rol in ROLLER:
            sonuc.append({**{a: v for a, v in k.items() if a != "sifre_hash"}, "rol": rol,
                          "aktif": k.get("aktif", True), "rol_ad": ROLLER[rol]})
    return sorted(sonuc, key=lambda k: (list(ROLLER).index(k["rol"]),
                                        (k.get("ad_soyad") or k["kullanici_adi"]).lower()))


def kullanici_kaydet(kullanici_adi, alanlar):
    """Kullanıcıyı ekler veya verilen alanlarını günceller (diğer alanlar korunur)."""
    with _kilit:
        kullanicilar = _yukle("kullanicilar.json", [])
        for k in kullanicilar:
            if k["kullanici_adi"].lower() == kullanici_adi.lower():
                k.update(alanlar)
                break
        else:
            kullanicilar.append({"kullanici_adi": kullanici_adi, **alanlar})
        _kaydet("kullanicilar.json", kullanicilar)


# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

VARSAYILAN_AYARLAR = {"baskan_girisi": False, "oturum_suresi_dk": 30}


def ayarlari_getir():
    with _kilit:
        return {**VARSAYILAN_AYARLAR, **_yukle("ayarlar.json", {})}


def ayarlari_kaydet(ayarlar):
    with _kilit:
        _kaydet("ayarlar.json", {**ayarlari_getir(), **ayarlar})


# ---------------------------------------------------------------------------
# İşlem geçmişi
# ---------------------------------------------------------------------------

def islem_ekle(kayit):
    kayit = {"id": yeni_id(), "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **kayit}
    with _kilit:
        islemler = _yukle("islem_gecmisi.json", [])
        islemler.append(kayit)
        _kaydet("islem_gecmisi.json", islemler)


def islemleri_getir(kullanici_adi="", kulup_id="", kayit_turu="", baslangic="", bitis=""):
    """İşlemleri yeniden eskiye döndürür; tarih filtreleri 'YYYY-AA-GG' (dahil)."""
    with _kilit:
        islemler = _yukle("islem_gecmisi.json", [])
    sonuc = [
        i for i in islemler
        if (not kullanici_adi or i.get("kullanici_adi") == kullanici_adi)
        and (not kulup_id or i.get("kulup_id") == kulup_id)
        and (not kayit_turu or i.get("kayit_turu") == kayit_turu)
        and (not baslangic or i["tarih"][:10] >= baslangic)
        and (not bitis or i["tarih"][:10] <= bitis)
    ]
    # Kayıtlar eklenme sırasıyla tutulur; ters çevirmek aynı saniyedekileri de doğru sıralar.
    return sonuc[::-1]


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

def belgeleri_getir(kulup_id=None, donem_id=None, arsiv=False):
    """Belgeleri yüklenme tarihine göre (yeniden eskiye) döndürür.

    arsiv=False: arşivde olmayan belgeler (arşivdeki kulüplerinkiler hariç),
    True: tek tek arşive alınmış belgeler, None: hepsi.
    """
    with _kilit:
        belgeler = _yukle("belgeler.json", [])
    if arsiv is False:
        aktif_kulupler = {k["id"] for k in kulupleri_getir()}
        belgeler = [b for b in belgeler if not b.get("arsiv") and b["kulup_id"] in aktif_kulupler]
    elif arsiv:
        belgeler = [b for b in belgeler if b.get("arsiv")]
    if kulup_id:
        belgeler = [b for b in belgeler if b["kulup_id"] == kulup_id]
    if donem_id:
        belgeler = [b for b in belgeler if b.get("donem_id") == donem_id]
    return sorted(belgeler, key=lambda b: b["yukleme_tarihi"], reverse=True)


def belge_getir(belge_id, arsiv=False):
    for belge in belgeleri_getir(arsiv=arsiv):
        if belge["id"] == belge_id:
            return belge
    return None


def belge_ekle(belge):
    with _kilit:
        belgeler = _yukle("belgeler.json", [])
        belgeler.append(belge)
        _kaydet("belgeler.json", belgeler)


def _liste_arsiv_ayarla(dosya_adi, kayit_id, kullanici):
    with _kilit:
        kayitlar = _yukle(dosya_adi, [])
        for kayit in kayitlar:
            if kayit["id"] == kayit_id:
                if kullanici is None:
                    kayit.pop("arsiv", None)
                else:
                    kayit["arsiv"] = _arsiv_kaydi(kullanici)
        _kaydet(dosya_adi, kayitlar)


def belge_arsiv_ayarla(belge_id, kullanici=None):
    """kullanici verilirse belgeyi arşive alır, None ise arşivden çıkarır."""
    _liste_arsiv_ayarla("belgeler.json", belge_id, kullanici)


def belge_sil(belge_id):
    with _kilit:
        belgeler = _yukle("belgeler.json", [])
        _kaydet("belgeler.json", [b for b in belgeler if b["id"] != belge_id])


# ---------------------------------------------------------------------------
# Etkinlik başvuruları
# ---------------------------------------------------------------------------

BASVURU_DURUMLARI = {
    "beklemede": "Beklemede",
    "onaylandi": "Onaylandı",
    "reddedildi": "Reddedildi",
    "revizyon": "Revizyon istendi",
}


def basvurulari_getir(kulup_id=None, durum=None, arsiv=False):
    """Başvuruları etkinlik tarihine göre (yeniden eskiye) döndürür.

    Her başvuruya kulüp adı ve etkinlik tarihine göre hesaplanan dönem eklenir.
    arsiv=False: arşivde olmayanlar (arşivdeki kulüplerinkiler hariç),
    True: tek tek arşive alınmış başvurular, None: hepsi.
    """
    with _kilit:
        basvurular = _yukle("etkinlik_basvurulari.json", [])
    tum_kulupler = kulupleri_getir(arsiv=None)
    aktif_kulupler = {k["id"] for k in tum_kulupler if not k.get("arsiv")}
    kulup_isimleri = {k["id"]: k["isim"] for k in tum_kulupler}
    donemler = donemleri_getir()
    sonuc = []
    for b in basvurular:
        if (kulup_id and b["kulup_id"] != kulup_id) or (durum and b["durum"] != durum):
            continue
        if arsiv is False and (b.get("arsiv") or b["kulup_id"] not in aktif_kulupler):
            continue
        if arsiv and not b.get("arsiv"):
            continue
        b["kulup_isim"] = kulup_isimleri.get(b["kulup_id"], "—")
        b["durum_ad"] = BASVURU_DURUMLARI.get(b["durum"], b["durum"])
        donem = tarihin_donemi(b["tarih_saat"], donemler)
        b["donem_id"] = donem["id"] if donem else ""
        b["donem_ad"] = donem["ad"] if donem else ""
        sonuc.append(b)
    return sorted(sonuc, key=lambda b: b["tarih_saat"], reverse=True)


def basvuru_getir(basvuru_id, arsiv=False):
    return next((b for b in basvurulari_getir(arsiv=arsiv) if b["id"] == basvuru_id), None)


def bekleyen_basvuru_sayisi(kulup_id=None):
    return len(basvurulari_getir(kulup_id=kulup_id, durum="beklemede"))


def basvuru_arsiv_ayarla(basvuru_id, kullanici=None):
    """kullanici verilirse başvuruyu arşive alır, None ise arşivden çıkarır."""
    _liste_arsiv_ayarla("etkinlik_basvurulari.json", basvuru_id, kullanici)


_HESAPLANAN_BASVURU_ALANLARI = {"kulup_isim", "durum_ad", "donem_id", "donem_ad", "arsiv"}


def basvuru_kaydet(basvuru):
    """Başvuruyu ekler veya aynı id'liyi günceller (verilmeyen alanlar korunur)."""
    basvuru = {k: v for k, v in basvuru.items() if k not in _HESAPLANAN_BASVURU_ALANLARI}
    with _kilit:
        basvurular = _yukle("etkinlik_basvurulari.json", [])
        for mevcut in basvurular:
            if mevcut["id"] == basvuru["id"]:
                mevcut.update(basvuru)
                break
        else:
            basvurular.append(basvuru)
        _kaydet("etkinlik_basvurulari.json", basvurular)


def basvuru_gecmise_ekle(basvuru_id, kullanici, durum, aciklama):
    """Başvurunun durumunu değiştirir ve değişikliği başvuru geçmişine yazar."""
    with _kilit:
        basvurular = _yukle("etkinlik_basvurulari.json", [])
        for b in basvurular:
            if b["id"] == basvuru_id:
                b["durum"] = durum
                b.setdefault("gecmis", []).append({
                    "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "kullanici": kullanici,
                    "durum": durum,
                    "aciklama": aciklama,
                })
                _kaydet("etkinlik_basvurulari.json", basvurular)
                return True
    return False


def basvuru_sil(basvuru_id):
    """Başvuruyu siler, ek dosya adlarını döndürür (dosyaları app.py siler)."""
    with _kilit:
        basvurular = _yukle("etkinlik_basvurulari.json", [])
        silinen = next((b for b in basvurular if b["id"] == basvuru_id), None)
        _kaydet("etkinlik_basvurulari.json", [b for b in basvurular if b["id"] != basvuru_id])
    return silinen["ek_dosyalar"] if silinen else []


# ---------------------------------------------------------------------------
# Zorunlu evraklar ve evrak takibi
# ---------------------------------------------------------------------------

# Teslim tarihine bu kadar gün (veya daha az) kalmışsa "süresi yaklaşıyor" sayılır.
YAKLASIYOR_GUN = 14

EVRAK_DURUMLARI = {
    "teslim": "Teslim edildi",
    "yaklasiyor": "Süresi yaklaşıyor",
    "eksik": "Eksik (süresi geçti)",
    "bekleniyor": "Bekleniyor",
}


def zorunlu_evraklari_getir(donem_id=None):
    """Zorunlu evrakları teslim tarihine göre sıralı döndürür."""
    with _kilit:
        evraklar = _yukle("zorunlu_evraklar.json", [])
    if donem_id:
        evraklar = [e for e in evraklar if e["donem_id"] == donem_id]
    for evrak in evraklar:
        evrak.setdefault("elden", {})
    return sorted(evraklar, key=lambda e: (e["teslim_tarihi"], e["tur"]))


def zorunlu_evrak_getir(evrak_id):
    return next((e for e in zorunlu_evraklari_getir() if e["id"] == evrak_id), None)


def zorunlu_evrak_kaydet(evrak):
    with _kilit:
        evraklar = _yukle("zorunlu_evraklar.json", [])
        for mevcut in evraklar:
            if mevcut["id"] == evrak["id"]:
                mevcut.update(evrak)
                break
        else:
            evraklar.append(evrak)
        _kaydet("zorunlu_evraklar.json", evraklar)


def zorunlu_evrak_sil(evrak_id):
    with _kilit:
        _kaydet("zorunlu_evraklar.json", [e for e in _yukle("zorunlu_evraklar.json", []) if e["id"] != evrak_id])


def elden_teslim_ayarla(evrak_id, kulup_id, kullanici):
    """Elden teslim işaretini açar/kapatır. Yeni durumu (True/False) döndürür."""
    with _kilit:
        evraklar = _yukle("zorunlu_evraklar.json", [])
        for evrak in evraklar:
            if evrak["id"] == evrak_id:
                elden = evrak.setdefault("elden", {})
                if kulup_id in elden:
                    del elden[kulup_id]
                    durum = False
                else:
                    elden[kulup_id] = {"tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "kullanici": kullanici}
                    durum = True
                _kaydet("zorunlu_evraklar.json", evraklar)
                return durum
    return False


def evrak_durumlari(donem_id, bugun=None, kulupler=None):
    """Kulüp x zorunlu evrak tablosunu hesaplar.

    Bir evrak; kulüp o dönemde aynı türde belge yüklediyse veya dekanlık
    "elden teslim alındı" olarak işaretlediyse teslim edilmiş sayılır.
    Dönüş: (evraklar, satırlar). Her satır: kulup, hucreler, sayılar.
    """
    bugun = bugun or date.today()
    evraklar = zorunlu_evraklari_getir(donem_id)
    kulupler = kulupler if kulupler is not None else kulupleri_getir()
    yuklenen = {}
    for belge in belgeleri_getir(donem_id=donem_id):
        yuklenen.setdefault((belge["kulup_id"], belge["tur"]), belge)

    satirlar = []
    for kulup in kulupler:
        hucreler = []
        for evrak in evraklar:
            belge = yuklenen.get((kulup["id"], evrak["tur"]))
            elden = evrak["elden"].get(kulup["id"])
            kalan = (date.fromisoformat(evrak["teslim_tarihi"]) - bugun).days
            if belge or elden:
                durum = "teslim"
            elif kalan < 0:
                durum = "eksik"
            elif kalan <= YAKLASIYOR_GUN:
                durum = "yaklasiyor"
            else:
                durum = "bekleniyor"
            hucreler.append({"evrak": evrak, "durum": durum, "belge": belge, "elden": elden, "kalan_gun": kalan})
        sayilar = {d: sum(1 for h in hucreler if h["durum"] == d) for d in EVRAK_DURUMLARI}
        satirlar.append({"kulup": kulup, "hucreler": hucreler, "sayilar": sayilar})
    return evraklar, satirlar


# ---------------------------------------------------------------------------
# Görev geçmişi (başkan ve yönetim kurulu değişiklikleri)
# ---------------------------------------------------------------------------

def kulup_gorevleri(kulup):
    """Kulübün şu anki görev -> kişi eşleşmeleri: {(görev, isim), ...}.

    Başkan, kulübün "baskan" alanından alınır; yönetim kurulundaki diğer
    görevler oradan eklenir (kuruldaki "Başkan" satırı başkan alanının kopyasıdır).
    """
    gorevler = set()
    if kulup.get("baskan"):
        gorevler.add(("Başkan", kulup["baskan"]))
    for uye in kulup.get("yonetim_kurulu", []):
        if uye["gorev"] != "Başkan" and uye.get("isim"):
            gorevler.add((uye["gorev"], uye["isim"]))
    return gorevler


def gorev_gecmisi_getir(kulup_id):
    """Kulübün görev kayıtları: önce görevdekiler, sonra bitenler (yeniden eskiye)."""
    with _kilit:
        kayitlar = [k for k in _yukle("gorev_gecmisi.json", []) if k["kulup_id"] == kulup_id]
    donemler = {d["id"]: d["ad"] for d in donemleri_getir()}
    for k in kayitlar:
        k["donem_ad"] = donemler.get(k.get("donem_id"), "")
        k["bitis_donem_ad"] = donemler.get(k.get("bitis_donem_id"), "")
    gorev_sirasi = {"Başkan": 0, "Başkan Yardımcısı": 1, "Sekreter": 2, "Sayman": 3}
    devam = sorted((k for k in kayitlar if not k["bitis"]), key=lambda k: (gorev_sirasi.get(k["gorev"], 9), k["gorev"]))
    biten = sorted((k for k in kayitlar if k["bitis"]), key=lambda k: k["bitis"], reverse=True)
    return devam + biten


def gorev_degisikliklerini_kaydet(kulup_id, eski_gorevler, yeni_gorevler, kullanici, kayit_oncesi=False):
    """Eski ve yeni görev kümelerini karşılaştırır: biten görevleri kapatır, yenileri açar.

    Hiçbir kayıt silinmez; görevden ayrılanın kaydına bitiş tarihi ve dönemi yazılır.
    kayit_oncesi=True: ilk kurulumda mevcut görevliler için başlangıcı bilinmeyen kayıt açar.
    """
    bugun = date.today().isoformat()
    donem = aktif_donem()
    donem_id = donem["id"] if donem else ""
    with _kilit:
        kayitlar = _yukle("gorev_gecmisi.json", [])
        for kayit in kayitlar:
            if (kayit["kulup_id"] == kulup_id and not kayit["bitis"]
                    and (kayit["gorev"], kayit["isim"]) in eski_gorevler - yeni_gorevler):
                kayit["bitis"] = bugun
                kayit["bitis_donem_id"] = donem_id
                kayit["kapatan"] = kullanici
        acik = {(k["gorev"], k["isim"]) for k in kayitlar if k["kulup_id"] == kulup_id and not k["bitis"]}
        for gorev, isim in sorted(yeni_gorevler - acik):
            kayitlar.append({
                "id": yeni_id(), "kulup_id": kulup_id, "gorev": gorev, "isim": isim,
                "baslangic": "" if kayit_oncesi else bugun, "donem_id": "" if kayit_oncesi else donem_id,
                "bitis": "", "bitis_donem_id": "", "kaydeden": kullanici,
            })
        _kaydet("gorev_gecmisi.json", kayitlar)


# ---------------------------------------------------------------------------
# Kulüp karnesi
# ---------------------------------------------------------------------------

def karne_puanlari(donem_id):
    """{kulup_id: {"puan", "not", "guncelleyen", "tarih"}}"""
    with _kilit:
        return _yukle("karneler.json", {}).get(donem_id, {})


def karne_kaydet(donem_id, kulup_id, puan, notu, kullanici):
    with _kilit:
        karneler = _yukle("karneler.json", {})
        karneler.setdefault(donem_id, {})[kulup_id] = {
            "puan": puan, "not": notu, "guncelleyen": kullanici,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        _kaydet("karneler.json", karneler)


def donem_karneleri(donem_id, kulupler=None):
    """Dönemin kulüp karnelerini hesaplar.

    Etkinlik sayısı: etkinlik tarihi bu döneme düşen onaylı başvurular.
    Evrak teslim oranı: teslim edilen / zorunlu evrak (zorunlu evrak yoksa None).
    Üye sayısı: güncel üye sayısı (üyelik geçmişi tutulmadığından).
    Sıralama: dekanlık puanı (puansızlar sonda), sonra teslim oranı, etkinlik sayısı.
    """
    kulupler = kulupler if kulupler is not None else kulupleri_getir()
    puanlar = karne_puanlari(donem_id)
    etkinlik = {}
    for b in basvurulari_getir(durum="onaylandi"):
        if b["donem_id"] == donem_id:
            etkinlik[b["kulup_id"]] = etkinlik.get(b["kulup_id"], 0) + 1
    evraklar, satirlar = evrak_durumlari(donem_id, kulupler=kulupler)
    evrak_sayilari = {s["kulup"]["id"]: s["sayilar"] for s in satirlar}

    karneler = []
    for kulup in kulupler:
        sayilar = evrak_sayilari.get(kulup["id"], {})
        teslim = sayilar.get("teslim", 0)
        karneler.append({
            "kulup": kulup,
            "etkinlik": etkinlik.get(kulup["id"], 0),
            "evrak_teslim": teslim,
            "evrak_toplam": len(evraklar),
            "evrak_eksik": sayilar.get("eksik", 0),
            "teslim_orani": round(100 * teslim / len(evraklar)) if evraklar else None,
            "uye": kulup["uye_sayisi"],
            "puan": puanlar.get(kulup["id"], {}).get("puan"),
            "not": puanlar.get(kulup["id"], {}).get("not", ""),
            "degerlendirme": puanlar.get(kulup["id"]),
        })
    karneler.sort(key=lambda k: (k["puan"] is None, -(k["puan"] or 0), -(k["teslim_orani"] or 0),
                                 -k["etkinlik"], k["kulup"]["isim"].lower()))
    for sira, karne in enumerate(karneler, 1):
        karne["sira"] = sira if karne["puan"] is not None else None
    return karneler


# ---------------------------------------------------------------------------
# Duyurular
# ---------------------------------------------------------------------------

def kulup_eposta_adresleri(kulup, danisman_dahil=False):
    """Kulübe ulaşılabilecek e-posta adresleri: kulüp e-postası, aktif başkan
    hesaplarının e-postası ve (istenirse) danışman e-postası."""
    adresler = []
    if kulup.get("eposta"):
        adresler.append(kulup["eposta"])
    for k in panel_kullanicilari_getir():
        if k["rol"] == "baskan" and k.get("kulup_id") == kulup["id"] and k["aktif"] and k.get("eposta"):
            adresler.append(k["eposta"])
    if danisman_dahil and kulup["danisman"]["eposta"]:
        adresler.append(kulup["danisman"]["eposta"])
    # Aynı adres iki kez yazılmasın (büyük/küçük harf farkı gözetmeden).
    tekil = {}
    for adres in adresler:
        tekil.setdefault(adres.strip().lower(), adres.strip())
    return list(tekil.values())


def duyurulari_getir():
    with _kilit:
        return _yukle("duyurular.json", [])[::-1]


def duyuru_getir(duyuru_id):
    return next((d for d in duyurulari_getir() if d["id"] == duyuru_id), None)


def duyuru_ekle(duyuru):
    with _kilit:
        duyurular = _yukle("duyurular.json", [])
        duyurular.append(duyuru)
        _kaydet("duyurular.json", duyurular)
