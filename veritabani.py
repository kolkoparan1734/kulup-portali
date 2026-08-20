"""Öğrenci Kulüpleri Portalı - MySQL veri erişim katmanı.

Site artık tüm verisini (kulüpler, üyelikler, kullanıcılar, forum
mesajları) data/*.json dosyaları veya SQLite yerine tek bir MySQL
veritabanında (kulup_portali) tutuyor. Böylece MySQL Workbench'ten
doğrudan SQL sorguları çalıştırılabiliyor (ör. bir kulüpteki belirli
bir giriş yılına ait üye sayısını saymak).
"""

import os
from datetime import datetime

import pymysql
import pymysql.cursors

# Gerçek bir yayında bu değerler ortam değişkenlerinden okunmalı,
# prototipte (app.secret_key ile aynı mantıkla) sabit/varsayılan yazıyoruz.
DB_HOST = os.environ.get("MYSQL_HOST", "localhost")
DB_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
DB_USER = os.environ.get("MYSQL_USER", "root")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "187256Fk.")
DB_NAME = os.environ.get("MYSQL_DATABASE", "kulup_portali")


def _baglan(veritabani_secili=True):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME if veritabani_secili else None,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def init_db():
    """kulup_portali veritabanını ve tabloları yoksa oluşturur."""
    conn = _baglan(veritabani_secili=False)
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4")
    conn.close()

    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kulupler (
                id VARCHAR(64) PRIMARY KEY,
                isim VARCHAR(255) NOT NULL,
                logo VARCHAR(255) NOT NULL,
                kategori VARCHAR(255) NOT NULL,
                aciklama TEXT NOT NULL,
                baskan VARCHAR(255) NOT NULL,
                baskan_kullanici_adi VARCHAR(32) NULL,
                kapak_gorseli VARCHAR(255) NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS yonetim_kurulu (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kulup_id VARCHAR(64) NOT NULL,
                isim VARCHAR(255) NOT NULL,
                gorev VARCHAR(255) NOT NULL,
                FOREIGN KEY (kulup_id) REFERENCES kulupler(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS etkinlikler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kulup_id VARCHAR(64) NOT NULL,
                baslik VARCHAR(255) NOT NULL,
                tarih DATE NOT NULL,
                durum ENUM('gecmis', 'gelecek') NOT NULL,
                aciklama TEXT NOT NULL,
                gorsel VARCHAR(255) NULL,
                FOREIGN KEY (kulup_id) REFERENCES kulupler(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kullanicilar (
                kullanici_adi VARCHAR(32) PRIMARY KEY,
                sifre_hash VARCHAR(255) NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uyelikler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kulup_id VARCHAR(64) NOT NULL,
                ogrenci_no VARCHAR(32) NOT NULL,
                durum ENUM('onaylanan', 'bekleyen') NOT NULL,
                UNIQUE KEY benzersiz_uyelik (kulup_id, ogrenci_no),
                FOREIGN KEY (kulup_id) REFERENCES kulupler(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forum_mesajlari (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kulup_id VARCHAR(64) NOT NULL,
                kullanici_adi VARCHAR(32) NOT NULL,
                mesaj TEXT NOT NULL,
                tarih VARCHAR(20) NOT NULL,
                FOREIGN KEY (kulup_id) REFERENCES kulupler(id) ON DELETE CASCADE
            )
        """)
    conn.close()


# ---------------------------------------------------------------------------
# Kulüpler
# ---------------------------------------------------------------------------

def kulupleri_getir():
    """Ana sayfadaki kulüp kartları için özet bilgileri döndürür."""
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, isim, logo, kategori, aciklama, baskan, baskan_kullanici_adi, kapak_gorseli "
            "FROM kulupler ORDER BY isim"
        )
        satirlar = cur.fetchall()
    conn.close()
    return satirlar


def kulup_ozet_getir(kulup_id):
    """Tek bir kulübün, alt listeler (yönetim kurulu/etkinlik) olmadan temel bilgilerini döndürür."""
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM kulupler WHERE id = %s", (kulup_id,))
        kulup = cur.fetchone()
    conn.close()
    return kulup


def kulup_getir(kulup_id):
    """Kulüp detay sayfası için yönetim kurulu ve etkinliklerle birlikte tam veriyi döndürür."""
    kulup = kulup_ozet_getir(kulup_id)
    if kulup is None:
        return None

    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT isim, gorev FROM yonetim_kurulu WHERE kulup_id = %s ORDER BY id", (kulup_id,)
        )
        kulup["yonetim_kurulu"] = cur.fetchall()

        cur.execute(
            "SELECT baslik, tarih, durum, aciklama, gorsel FROM etkinlikler "
            "WHERE kulup_id = %s ORDER BY tarih",
            (kulup_id,),
        )
        etkinlikler = cur.fetchall()
    conn.close()

    for etkinlik in etkinlikler:
        etkinlik["tarih"] = etkinlik["tarih"].strftime("%Y-%m-%d")
    kulup["etkinlikler"] = etkinlikler
    return kulup


def etkinlik_ekle(kulup_id, baslik, tarih, durum, aciklama, gorsel):
    """Bir kulübe yeni etkinlik ekler. tarih 'YYYY-MM-DD' formatında bir metindir."""
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO etkinlikler (kulup_id, baslik, tarih, durum, aciklama, gorsel) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (kulup_id, baslik, tarih, durum, aciklama, gorsel),
        )
    conn.close()


# ---------------------------------------------------------------------------
# Kullanıcılar
# ---------------------------------------------------------------------------

def kullanici_bul(kullanici_adi):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM kullanicilar WHERE LOWER(kullanici_adi) = LOWER(%s)", (kullanici_adi,)
        )
        kullanici = cur.fetchone()
    conn.close()
    return kullanici


def kullanici_ekle(kullanici_adi, sifre_hash):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO kullanicilar (kullanici_adi, sifre_hash) VALUES (%s, %s)",
            (kullanici_adi, sifre_hash),
        )
    conn.close()


def kullanici_sifre_guncelle(kullanici_adi, yeni_sifre_hash):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE kullanicilar SET sifre_hash = %s WHERE LOWER(kullanici_adi) = LOWER(%s)",
            (yeni_sifre_hash, kullanici_adi),
        )
    conn.close()


# ---------------------------------------------------------------------------
# Üyelikler
# ---------------------------------------------------------------------------

def uyelik_durumu(kulup_id, kullanici_adi):
    """Bir kullanıcının bir kulüpteki durumunu döndürür: 'uye', 'bekliyor' veya 'yok'."""
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT durum FROM uyelikler WHERE kulup_id = %s AND ogrenci_no = %s",
            (kulup_id, kullanici_adi),
        )
        satir = cur.fetchone()
    conn.close()
    if satir is None:
        return "yok"
    return "uye" if satir["durum"] == "onaylanan" else "bekliyor"


def bekleyen_istekleri_getir(kulup_id):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ogrenci_no FROM uyelikler WHERE kulup_id = %s AND durum = 'bekleyen' ORDER BY id",
            (kulup_id,),
        )
        satirlar = cur.fetchall()
    conn.close()
    return [s["ogrenci_no"] for s in satirlar]


def onayli_uyeleri_getir(kulup_id):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ogrenci_no FROM uyelikler WHERE kulup_id = %s AND durum = 'onaylanan' ORDER BY id",
            (kulup_id,),
        )
        satirlar = cur.fetchall()
    conn.close()
    return [s["ogrenci_no"] for s in satirlar]


def uye_sayisi_getir(kulup_id):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS sayi FROM uyelikler WHERE kulup_id = %s AND durum = 'onaylanan'",
            (kulup_id,),
        )
        satir = cur.fetchone()
    conn.close()
    return satir["sayi"]


def uyelik_basvurusu_ekle(kulup_id, kullanici_adi):
    """Kullanıcı bu kulüpte hiç kaydı yoksa 'bekleyen' olarak ekler."""
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM uyelikler WHERE kulup_id = %s AND ogrenci_no = %s",
            (kulup_id, kullanici_adi),
        )
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO uyelikler (kulup_id, ogrenci_no, durum) VALUES (%s, %s, 'bekleyen')",
                (kulup_id, kullanici_adi),
            )
    conn.close()


def uyelik_onayla(kulup_id, kullanici_adi):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE uyelikler SET durum = 'onaylanan' "
            "WHERE kulup_id = %s AND ogrenci_no = %s AND durum = 'bekleyen'",
            (kulup_id, kullanici_adi),
        )
    conn.close()


def uyelik_reddet(kulup_id, kullanici_adi):
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM uyelikler WHERE kulup_id = %s AND ogrenci_no = %s AND durum = 'bekleyen'",
            (kulup_id, kullanici_adi),
        )
    conn.close()


# ---------------------------------------------------------------------------
# Forum
# ---------------------------------------------------------------------------

def forum_yukle(kulup_id, limit=20):
    """Bir kulübün son 'limit' kadar forum mesajını (eskiden yeniye) döndürür."""
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT kullanici_adi AS isim, mesaj, tarih FROM forum_mesajlari "
            "WHERE kulup_id = %s ORDER BY id DESC LIMIT %s",
            (kulup_id, limit),
        )
        satirlar = list(cur.fetchall())
    conn.close()
    satirlar.reverse()
    return satirlar


def forum_kaydet(kulup_id, kullanici_adi, mesaj):
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = _baglan()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO forum_mesajlari (kulup_id, kullanici_adi, mesaj, tarih) VALUES (%s, %s, %s, %s)",
            (kulup_id, kullanici_adi, mesaj, tarih),
        )
    conn.close()
