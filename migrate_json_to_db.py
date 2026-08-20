"""Tek seferlik geçiş betiği: data/*.json dosyalarındaki eski verileri
MySQL'deki kulup_portali veritabanına aktarır.

MySQL'e geçiş yapılırken JSON dosyalarındaki mevcut kulüp/kullanıcı/üyelik/
forum verileri hiç taşınmadığı için ana sayfada kulüpler görünmüyordu.

Çalıştırmak için:
    python migrate_json_to_db.py

Betik tekrar çalıştırılırsa (INSERT IGNORE / ON DUPLICATE KEY sayesinde)
veriyi kopyalamadan güvenle yeniden çalışır.
"""

import json
from datetime import datetime

import veritabani as db

db.init_db()


def _yukle(dosya_adi):
    with open(f"data/{dosya_adi}", encoding="utf-8") as f:
        return json.load(f)


def kulupleri_aktar():
    veri = _yukle("clubs.json")
    conn = db._baglan()
    with conn.cursor() as cur:
        for kulup in veri["kulupler"]:
            cur.execute(
                "INSERT INTO kulupler (id, isim, logo, kategori, aciklama, baskan, "
                "baskan_kullanici_adi, kapak_gorseli) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE isim=VALUES(isim), logo=VALUES(logo), "
                "kategori=VALUES(kategori), aciklama=VALUES(aciklama), baskan=VALUES(baskan), "
                "baskan_kullanici_adi=VALUES(baskan_kullanici_adi), "
                "kapak_gorseli=VALUES(kapak_gorseli)",
                (
                    kulup["id"],
                    kulup["isim"],
                    kulup["logo"],
                    kulup["kategori"],
                    kulup["aciklama"],
                    kulup["baskan"],
                    kulup.get("baskan_kullanici_adi"),
                    kulup.get("kapak_gorseli"),
                ),
            )

            for uye in kulup.get("yonetim_kurulu", []):
                cur.execute(
                    "SELECT 1 FROM yonetim_kurulu WHERE kulup_id = %s AND isim = %s AND gorev = %s",
                    (kulup["id"], uye["isim"], uye["gorev"]),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        "INSERT INTO yonetim_kurulu (kulup_id, isim, gorev) VALUES (%s, %s, %s)",
                        (kulup["id"], uye["isim"], uye["gorev"]),
                    )

            for etkinlik in kulup.get("etkinlikler", []):
                cur.execute(
                    "SELECT 1 FROM etkinlikler WHERE kulup_id = %s AND baslik = %s AND tarih = %s",
                    (kulup["id"], etkinlik["baslik"], etkinlik["tarih"]),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        "INSERT INTO etkinlikler (kulup_id, baslik, tarih, durum, aciklama, gorsel) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            kulup["id"],
                            etkinlik["baslik"],
                            etkinlik["tarih"],
                            etkinlik["durum"],
                            etkinlik["aciklama"],
                            etkinlik.get("gorsel"),
                        ),
                    )
    conn.close()
    print(f"{len(veri['kulupler'])} kulüp aktarıldı.")


def kullanicilari_aktar():
    veri = _yukle("kullanicilar.json")
    conn = db._baglan()
    with conn.cursor() as cur:
        for kullanici in veri:
            cur.execute(
                "INSERT IGNORE INTO kullanicilar (kullanici_adi, sifre_hash) VALUES (%s, %s)",
                (kullanici["kullanici_adi"], kullanici["sifre_hash"]),
            )
    conn.close()
    print(f"{len(veri)} kullanıcı aktarıldı.")


def uyelikleri_aktar():
    veri = _yukle("uyelikler.json")
    conn = db._baglan()
    toplam = 0
    with conn.cursor() as cur:
        for kulup_id, durumlar in veri.items():
            for ogrenci_no in durumlar.get("onaylanan", []):
                cur.execute(
                    "INSERT IGNORE INTO uyelikler (kulup_id, ogrenci_no, durum) VALUES (%s, %s, 'onaylanan')",
                    (kulup_id, ogrenci_no),
                )
                toplam += 1
            for ogrenci_no in durumlar.get("bekleyen", []):
                cur.execute(
                    "INSERT IGNORE INTO uyelikler (kulup_id, ogrenci_no, durum) VALUES (%s, %s, 'bekleyen')",
                    (kulup_id, ogrenci_no),
                )
                toplam += 1
    conn.close()
    print(f"{toplam} üyelik kaydı aktarıldı.")


def forumu_aktar():
    veri = _yukle("forum.json")
    conn = db._baglan()
    toplam = 0
    with conn.cursor() as cur:
        for kulup_id, mesajlar in veri.items():
            for mesaj in mesajlar:
                cur.execute(
                    "SELECT 1 FROM forum_mesajlari WHERE kulup_id = %s AND kullanici_adi = %s "
                    "AND mesaj = %s AND tarih = %s",
                    (kulup_id, mesaj["isim"], mesaj["mesaj"], mesaj["tarih"]),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        "INSERT INTO forum_mesajlari (kulup_id, kullanici_adi, mesaj, tarih) "
                        "VALUES (%s, %s, %s, %s)",
                        (kulup_id, mesaj["isim"], mesaj["mesaj"], mesaj["tarih"]),
                    )
                    toplam += 1
    conn.close()
    print(f"{toplam} forum mesajı aktarıldı.")


if __name__ == "__main__":
    kulupleri_aktar()
    kullanicilari_aktar()
    uyelikleri_aktar()
    forumu_aktar()
    print("Geçiş tamamlandı.")
