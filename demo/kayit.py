"""Tanıtım videosunu otomatik kaydeder: "Bir kulüp başvurusu geldiğinde nasıl onaylanır?"

Kurulum (bir kez):
    pip install playwright
    python -m playwright install chromium

Çalıştırma (proje klasöründe):
    python demo/kayit.py                 -> demo/video/dekan-onay-tanitim.webm
    python demo/kayit.py --goster        -> kayıt sırasında tarayıcı penceresini gösterir
    python demo/kayit.py --altyazisiz    -> alttaki anlatım yazısı olmadan kaydeder (üzerine ses okunacaksa)

Script her çalıştığında demo veri setini sıfırlar (demo/veri_olustur.py), paneli bu
veriyle geçici bir adreste açar ve demo/senaryo.md'deki akışı oynatır. Gerçek veriye
(data/, uploads/) dokunmaz. Video sessizdir; anlatım metni altyazı olarak görünür.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import date, timedelta

DEMO = os.path.dirname(os.path.abspath(__file__))
PROJE = os.path.dirname(DEMO)
sys.path.insert(0, DEMO)
import veri_olustur  # noqa: E402

PORT = 5055
ADRES = f"http://127.0.0.1:{PORT}"
VIDEO_KLASORU = os.path.join(DEMO, "video")
VIDEO_ADI = "dekan-onay-tanitim.webm"
BOYUT = {"width": 1280, "height": 720}
BASVURU_ADI = "Sokak Fotoğrafçılığı Atölyesi"

# Sayfa değişse de altyazının ekranda kalması için metin sessionStorage'da tutulur.
ALTYAZI_BETIGI = """
(() => {
    const goster = () => {
        const metin = sessionStorage.getItem("demoAltyazi");
        let kutu = document.getElementById("demo-altyazi");
        if (!metin) { if (kutu) kutu.remove(); return; }
        if (!kutu) {
            kutu = document.createElement("div");
            kutu.id = "demo-altyazi";
            kutu.style.cssText = "position:fixed;left:50%;bottom:18px;transform:translateX(-50%);" +
                "width:max-content;max-width:88%;z-index:99999;background:rgba(16,24,40,.93);color:#fff;" +
                "padding:10px 18px;border-radius:10px;font:500 17px/1.45 Inter,system-ui,sans-serif;" +
                "text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.3);pointer-events:none";
            document.body.appendChild(kutu);
        }
        kutu.textContent = metin;
    };
    window.__demoAltyazi = (metin) => { sessionStorage.setItem("demoAltyazi", metin || ""); goster(); };
    document.addEventListener("DOMContentLoaded", goster);
})();
"""


class Kayit:
    def __init__(self, sayfa, altyazi=True):
        self.sayfa = sayfa
        self.altyazi = altyazi

    def anlat(self, metin, ek_sn=0.0):
        """Anlatım metnini altyazıya yazar ve okunacak kadar bekler (yaklaşık 14 harf/sn)."""
        if self.altyazi:
            self.sayfa.evaluate("m => window.__demoAltyazi(m)", metin)
        self.sayfa.wait_for_timeout(int((max(3.0, len(metin) / 14) + ek_sn) * 1000))

    def bekle(self, sn):
        self.sayfa.wait_for_timeout(int(sn * 1000))

    def vurgula(self, hedef, sn=0.9):
        """Tıklanacak öğeyi görünür alana getirir ve kısa süre çerçeve içine alır."""
        hedef.scroll_into_view_if_needed()
        hedef.evaluate("o => { o.dataset.eskiCerceve = o.style.outline; o.style.outline = '3px solid #F2A900';"
                       " o.style.outlineOffset = '3px'; }")
        self.bekle(sn)
        hedef.evaluate("o => { o.style.outline = o.dataset.eskiCerceve || ''; o.style.outlineOffset = ''; }")

    def tikla(self, hedef):
        self.vurgula(hedef)
        hedef.click()
        self.sayfa.wait_for_load_state("networkidle")

    def yaz(self, secici, metin):
        alan = self.sayfa.locator(secici)
        alan.scroll_into_view_if_needed()
        alan.click()
        alan.press_sequentially(metin, delay=35)
        self.bekle(0.3)

    def giris(self, kullanici_adi, sifre):
        self.sayfa.goto(ADRES + "/giris")
        self.yaz("input[name='kullanici_adi']", kullanici_adi)
        self.yaz("input[name='sifre']", sifre)
        self.tikla(self.sayfa.get_by_role("button", name="Giriş Yap"))

    def cikis(self):
        self.tikla(self.sayfa.locator(".menu-cikis button"))


def senaryo(k):
    s = k.sayfa

    # 1 - Açılış
    s.goto(ADRES + "/giris")
    k.anlat("Bu videoda, bir kulüp etkinlik başvurusu gönderdiğinde dekanlığın bu başvuruyu "
            "panelden nasıl onayladığını adım adım göreceğiz.")

    # 2 - Kulüp başkanı giriş yapar
    k.anlat("Önce kulüp tarafına bakalım. Kulüp başkanı kendi kullanıcı adı ve şifresiyle panele giriş yapar.", -2)
    k.giris(*veri_olustur.BASKAN)

    # 3 - Kulüp başkanının ana sayfası
    k.anlat("Kulüp başkanı yalnızca kendi kulübünü görür: başvurularının durumu, dekanlığın açıklamaları "
            "ve teslim etmesi gereken evraklar bu sayfadadır.")

    # 4 - Yeni başvuru
    k.anlat("Yeni bir etkinlik için “Yeni Başvuru”ya tıklar.", -1)
    k.tikla(s.get_by_role("link", name="+ Yeni Başvuru"))
    k.anlat("Etkinliğin adını, tarihini, yerini ve katılımcı sayısını yazar; "
            "varsa etkinlik planını ek dosya olarak ekler.", -4)
    k.yaz("input[name='ad']", BASVURU_ADI)
    s.locator("input[name='tarih_saat']").fill(f"{date.today() + timedelta(days=14):%Y-%m-%d}T14:00")
    k.yaz("input[name='yer']", "Mahmutbey Yerleşkesi, Atölye 2")
    k.yaz("input[name='katilimci']", "30")
    k.yaz("textarea[name='aciklama']", "Kulüp üyeleriyle yerleşke çevresinde uygulamalı sokak fotoğrafçılığı atölyesi.")
    s.locator("input[name='butce']").fill("0")
    dosya = s.locator("input[name='ek_dosya']")
    dosya.scroll_into_view_if_needed()
    dosya.set_input_files(os.path.join(DEMO, "ornek-etkinlik-plani.pdf"))
    k.bekle(1.2)
    k.tikla(s.get_by_role("button", name="Başvuruyu Gönder"))

    # 5 - Başvuru gönderildi
    k.anlat("Başvuru gönderildi ve durumu “Bekliyor” oldu. Artık sıra dekanlıkta.")
    k.cikis()

    # 6 - Dekan giriş yapar
    k.anlat("Şimdi dekan olarak giriş yapalım.", -1)
    k.giris(*veri_olustur.DEKAN)

    # 7 - Onay Bekleyenler
    k.vurgula(s.locator("#onay-bekleyenler"), 1.2)
    k.anlat("Ana panelin en üstünde “Onay Bekleyenler” yer alır. Kaç başvurunun beklediği, hangi kulüpten "
            "geldiği, kimin ne zaman gönderdiği tek bakışta görülür.")

    # 8 - Detay
    k.anlat("Başvuruyu incelemek için “İncele”ye tıklıyoruz.", -1)
    k.tikla(s.locator("#onay-bekleyenler tr", has_text=BASVURU_ADI).get_by_role("link", name="İncele"))
    k.anlat("Detay sayfasında başvurunun tüm bilgileri ve ekli belgeler yer alır. "
            "Ek dosyayı indirip inceleyebilirsiniz.", -3)
    k.vurgula(s.get_by_role("link", name="İndir").first, 1.5)

    # 9 - Karar
    k.vurgula(s.locator("#karar"), 1.2)
    k.anlat("Karar bölümünde Onayla ve Reddet düğmeleri bulunur. Reddetmek için açıklama yazmak zorunludur; "
            "boş bırakıp “Reddet”e basarsak panel uyarır.", -4)
    k.vurgula(s.locator("#karar button[value='reddedildi']"))
    s.locator("#karar button[value='reddedildi']").click()
    k.bekle(2.5)
    k.anlat("Biz bu başvuruyu uygun buluyoruz. Kulübe iletilecek kısa bir not yazıp “Onayla”ya basıyoruz.", -4)
    k.yaz("#karar textarea[name='aciklama']", "Uygun görüldü. Atölye 2 sizin adınıza rezerve edildi.")
    k.tikla(s.locator("#karar button[value='onaylandi']"))

    # 10 - Onaylandı, kayıtlar
    k.anlat("Başvuru onaylandı. Kararı kimin, ne zaman verdiği başvurunun süreç geçmişine yazılır.")
    k.tikla(s.get_by_role("link", name="İşlem Geçmişi"))
    k.anlat("Aynı kayıt, paneldeki tüm işlemlerle birlikte “İşlem Geçmişi” sayfasında da görünür.")

    # 11 - Liste ve filtreler
    k.tikla(s.locator(".yanmenu").get_by_role("link", name="Etkinlik Başvuruları"))
    k.anlat("“Etkinlik Başvuruları” sayfasında tüm başvuruları duruma, kulübe ve tarihe göre filtreleyebilirsiniz.", -3)
    k.tikla(s.locator(".sekme", has_text="Bekliyor"))
    k.bekle(1.5)
    k.tikla(s.locator(".sekme", has_text="Onaylandı"))
    k.bekle(1.5)
    k.cikis()

    # 12 - Kulüp başkanı sonucu görür
    k.anlat("Son olarak kulüp başkanı tekrar giriş yaptığında sonucu görür.", -1)
    k.giris(*veri_olustur.BASKAN)
    k.vurgula(s.locator("tr", has_text=BASVURU_ADI), 1.5)
    k.anlat("Başvurusu “Onaylandı” olarak görünür; dekanlığın yazdığı açıklama da yanında yer alır.")

    # 13 - Kapanış
    k.anlat("Özetle: “Onay Bekleyenler”den başvuruyu açın, inceleyin; onaylayın ya da açıklama yazarak reddedin. "
            "Kulüp başkanı sonucu kendi panelinden takip eder.", 1.5)


def _sunucuyu_baslat():
    ortam = dict(os.environ, PANEL_VERI_KLASORU=veri_olustur.VERI, PANEL_YUKLEME_KLASORU=veri_olustur.YUKLEME,
                 PANEL_DEBUG="0", PANEL_HTTPS="0")
    sunucu = subprocess.Popen(
        [sys.executable, "-c", f"import app; app.app.run(port={PORT})"],
        cwd=PROJE, env=ortam, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if sunucu.poll() is not None:
            sys.exit("Panel başlatılamadı. Önce 'pip install -r requirements.txt' çalıştırın.")
        try:
            urllib.request.urlopen(ADRES + "/giris", timeout=1)
            return sunucu
        except OSError:
            time.sleep(0.5)
    sunucu.terminate()
    sys.exit(f"Panel {ADRES} adresinde açılamadı (port {PORT} kullanımda olabilir).")


def main():
    secenekler = argparse.ArgumentParser(description="Dekan onay akışı tanıtım videosunu kaydeder.")
    secenekler.add_argument("--goster", action="store_true", help="tarayıcı penceresini göster")
    secenekler.add_argument("--altyazisiz", action="store_true", help="anlatım altyazısı olmadan kaydet")
    args = secenekler.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright kurulu değil:\n    pip install playwright\n    python -m playwright install chromium")

    veri_olustur.olustur()
    os.makedirs(VIDEO_KLASORU, exist_ok=True)
    sunucu = _sunucuyu_baslat()
    try:
        with sync_playwright() as p:
            tarayici = p.chromium.launch(headless=not args.goster)
            baglam = tarayici.new_context(viewport=BOYUT, record_video_dir=VIDEO_KLASORU,
                                          record_video_size=BOYUT, locale="tr-TR")
            baglam.add_init_script(ALTYAZI_BETIGI)
            sayfa = baglam.new_page()
            sayfa.set_default_timeout(15000)
            basla = time.time()
            senaryo(Kayit(sayfa, altyazi=not args.altyazisiz))
            sure = time.time() - basla
            baglam.close()  # video dosyası bağlam kapanınca yazılır
            ham_video = sayfa.video.path()
            tarayici.close()
    finally:
        sunucu.terminate()

    hedef = os.path.join(VIDEO_KLASORU, VIDEO_ADI)
    shutil.move(ham_video, hedef)
    print(f"Video hazır ({int(sure // 60)} dk {int(sure % 60)} sn): {hedef}")


if __name__ == "__main__":
    main()
