# Tanıtım videosu senaryosu: “Bir kulüp başvurusu geldiğinde nasıl onaylanır?”

**İzleyici:** Öğrenci Dekanı ve dekanlık çalışanları
**Süre:** yaklaşık 2,5 dakika
**Akış:** kulüp başkanı başvuru gönderir → dekan giriş yapar → “Onay Bekleyenler”de görür → detayı inceler → onaylar → kulüp başkanı sonucu görür

## Videoyu hazırlamanın iki yolu

**1. Otomatik kayıt (önerilen).** Aşağıdaki akışın tamamını tarayıcıda kendiliğinden oynatır ve kaydeder:

```
pip install playwright
python -m playwright install chromium
python demo/kayit.py
```

Video `demo/video/dekan-onay-tanitim.webm` olarak kaydedilir. Ses yoktur; anlatım metni ekranın altında altyazı olarak görünür. Üzerine kendi sesinizi okuyacaksanız `python demo/kayit.py --altyazisiz` ile altyazısız kaydedip aşağıdaki anlatım metnini seslendirin.

**2. Elle ekran kaydı.** Kendi sesinizle, kendi hızınızda çekmek için:

1. Demo veriyi sıfırlayın: `python demo/veri_olustur.py`
2. Paneli demo veriyle açın (PowerShell):
   ```
   $env:PANEL_VERI_KLASORU = "demo/veri"; $env:PANEL_YUKLEME_KLASORU = "demo/uploads"; python app.py
   ```
3. Tarayıcıda `http://127.0.0.1:5000` adresini açın, pencereyi 1280×720 civarına getirin, yakınlaştırmayı %100 yapın.
4. Ekran kaydını başlatın (Windows: `Win + Alt + R`, ya da OBS) ve aşağıdaki sahneleri sırayla uygulayın.
5. Çekimi tekrarlamak için 1. adımı yeniden çalıştırın; demo veri başlangıç haline döner.

Her iki yol da yalnızca `demo/veri` klasörünü kullanır; gerçek kulüp verisine dokunmaz.

## Demo hesapları

| Rol | Kullanıcı adı | Şifre | Not |
|---|---|---|---|
| Dekan | `demo.dekan` | `Demo-Dekan-2026` | |
| Kulüp başkanı | `demo.baskan` | `Demo-Baskan-2026` | Örnek Fotoğrafçılık Kulübü (videodaki başkan) |
| Kulüp başkanı | `demo.baskan2` | `Demo-Baskan-2026` | Örnek Satranç Kulübü (videoda kullanılmaz) |

Demo veride başlangıçta bir bekleyen başvuru (Satranç Kulübü turnuvası), bir onaylanmış ve bir reddedilmiş başvuru bulunur.

## Sahneler

| # | Ekran | Yapılacak | Anlatım metni |
|---|---|---|---|
| 1 | Giriş sayfası | Bir şey yapmayın, ekran görünsün. | “Bu videoda, bir kulüp etkinlik başvurusu gönderdiğinde dekanlığın bu başvuruyu panelden nasıl onayladığını adım adım göreceğiz.” |
| 2 | Giriş sayfası | Kullanıcı adı: `demo.baskan`, şifre: `Demo-Baskan-2026` yazın, **Giriş Yap**’a tıklayın. | “Önce kulüp tarafına bakalım. Kulüp başkanı kendi kullanıcı adı ve şifresiyle panele giriş yapar.” |
| 3 | Kulüp başkanı ana sayfası | Sayfayı gösterin: üstte durum kartları, altında “Başvurularım” tablosu ve “Zorunlu Evraklar”. | “Kulüp başkanı yalnızca kendi kulübünü görür: başvurularının durumu, dekanlığın açıklamaları ve teslim etmesi gereken evraklar bu sayfadadır.” |
| 4 | Kulüp başkanı ana sayfası | Sağ üstteki **+ Yeni Başvuru** düğmesine tıklayın. | “Yeni bir etkinlik için ‘Yeni Başvuru’ya tıklar.” |
| 5 | Yeni Etkinlik Başvurusu formu | Doldurun — Etkinlik adı: `Sokak Fotoğrafçılığı Atölyesi` · Tarih ve saat: iki hafta sonrası, 14:00 · Yer: `Mahmutbey Yerleşkesi, Atölye 2` · Katılımcı: `30` · Açıklama: `Kulüp üyeleriyle yerleşke çevresinde uygulamalı sokak fotoğrafçılığı atölyesi.` · Bütçe: `0` · Ek dosya: `demo/ornek-etkinlik-plani.pdf`. En altta **Başvuruyu Gönder**’e tıklayın. | “Etkinliğin adını, tarihini, yerini ve katılımcı sayısını yazar; varsa etkinlik planını ek dosya olarak ekler.” |
| 6 | Başvuru detayı (kulüp başkanı) | Üstteki sarı “Başvurunuz dekanlığın onayını bekliyor” kutusunu gösterin. Sonra sol menünün altındaki **Çıkış**’a tıklayın. | “Başvuru gönderildi ve durumu ‘Bekliyor’ oldu. Artık sıra dekanlıkta.” |
| 7 | Giriş sayfası | Kullanıcı adı: `demo.dekan`, şifre: `Demo-Dekan-2026`, **Giriş Yap**. | “Şimdi dekan olarak giriş yapalım.” |
| 8 | Dekan Ana Paneli | En üstteki **Onay Bekleyenler** kutusunu gösterin: yanındaki sayı (2), kulüp, başvuru türü, gönderen ve gönderim tarihi sütunları. | “Ana panelin en üstünde ‘Onay Bekleyenler’ yer alır. Kaç başvurunun beklediği, hangi kulüpten geldiği, kimin ne zaman gönderdiği tek bakışta görülür.” |
| 9 | Dekan Ana Paneli | “Sokak Fotoğrafçılığı Atölyesi” satırındaki **İncele** düğmesine tıklayın. | “Başvuruyu incelemek için ‘İncele’ye tıklıyoruz.” |
| 10 | Başvuru detayı (dekan) | Soldaki “Başvuru Bilgileri”ni ve “Ek Dosyalar”daki **İndir** düğmesini gösterin (tıklamanız gerekmez). | “Detay sayfasında başvurunun tüm bilgileri ve ekli belgeler yer alır. Ek dosyayı indirip inceleyebilirsiniz.” |
| 11 | Başvuru detayı → “Karar Ver” kutusu | Açıklamayı boş bırakıp **Reddet**’e tıklayın; kırmızı uyarı çıkar: “Reddetmek veya revizyon istemek için açıklama yazmalısınız.” | “Karar bölümünde Onayla ve Reddet düğmeleri bulunur. Reddetmek için açıklama yazmak zorunludur; boş bırakıp ‘Reddet’e basarsak panel uyarır.” |
| 12 | “Karar Ver” kutusu | Açıklamaya `Uygun görüldü. Atölye 2 sizin adınıza rezerve edildi.` yazın, yeşil **Onayla** düğmesine tıklayın. | “Biz bu başvuruyu uygun buluyoruz. Kulübe iletilecek kısa bir not yazıp ‘Onayla’ya basıyoruz.” |
| 13 | Başvuru detayı (onaylanmış) | Üstteki yeşil “Başvuru onaylandı” kutusunu ve sağdaki “Süreç Geçmişi”ni gösterin. | “Başvuru onaylandı. Kararı kimin, ne zaman verdiği başvurunun süreç geçmişine yazılır.” |
| 14 | İşlem Geçmişi | Sol menüden **İşlem Geçmişi**’ne tıklayın; en üstteki “Karar” satırını gösterin. | “Aynı kayıt, paneldeki tüm işlemlerle birlikte ‘İşlem Geçmişi’ sayfasında da görünür.” |
| 15 | Etkinlik Başvuruları | Sol menüden **Etkinlik Başvuruları**’na tıklayın. Üstteki **Bekliyor** ve **Onaylandı** sekmelerine sırayla tıklayın; kulüp ve tarih filtrelerini gösterin. Sonra **Çıkış**. | “‘Etkinlik Başvuruları’ sayfasında tüm başvuruları duruma, kulübe ve tarihe göre filtreleyebilirsiniz.” |
| 16 | Giriş sayfası | Yeniden `demo.baskan` / `Demo-Baskan-2026` ile giriş yapın. | “Son olarak kulüp başkanı tekrar giriş yaptığında sonucu görür.” |
| 17 | Kulüp başkanı ana sayfası | “Başvurularım” tablosunda “Sokak Fotoğrafçılığı Atölyesi” satırını gösterin: durum **Onaylandı**, yanında dekanlığın notu. | “Başvurusu ‘Onaylandı’ olarak görünür; dekanlığın yazdığı açıklama da yanında yer alır.” |
| 18 | Kulüp başkanı ana sayfası | Ekran sabit kalsın. | “Özetle: ‘Onay Bekleyenler’den başvuruyu açın, inceleyin; onaylayın ya da açıklama yazarak reddedin. Kulüp başkanı sonucu kendi panelinden takip eder.” |

## Çekim notları

- Anlatımı acele etmeden okuyun; her cümleden sonra bir saniye bekleyin.
- Fareyi tıklayacağınız yere önce götürün, bir an bekleyip sonra tıklayın.
- Videoda gerçek öğrenci adı veya numarası görünmez; tüm kayıtlar örnek veridir.
- 11. sahneyi (açıklamasız ret denemesi) atlamak isterseniz 12. sahneye doğrudan geçebilirsiniz; akış bozulmaz.
