# Öğrenci Dekanlığı Kulüp Paneli

Altınbaş Üniversitesi Öğrenci Dekanlığı'nın kulüpleri, üyeleri, kulüp evraklarını ve etkinlik başvurularını yönettiği panel. Flask ile çalışır; veriyi `data/` klasöründeki JSON dosyalarında tutar.

## Çalıştırma

```
pip install -r requirements.txt
python app.py
```

Tarayıcıda `http://127.0.0.1:5000` adresini açın.

İlk kurulumda veya dekan şifresi unutulduğunda dekan hesabı şu komutla oluşturulur ya da şifresi yenilenir:

```
python app.py dekan-olustur
```

## Roller

| Rol | Yapabildikleri |
|---|---|
| **Dekan** | Her şey: tüm kulüpler, üyeler, belgeler, başvurular ve işlem geçmişi; başvuruları onaylar veya reddeder; arşivler ve siler; kullanıcıları ve ayarları yönetir. |
| **Dekanlık personeli** | Kulüp, üye, belge ve başvuru kayıtlarını görür ve düzenler. Karar veremez, silemez, kullanıcı ve ayar sayfalarını açamaz. |
| **Kulüp başkanı** | Yalnızca kendi kulübü: başvuru ve belge gönderir, sonucu ve dekanlığın açıklamasını takip eder. |

Kulüp başkanlarının girebilmesi için dekanın **Panel Ayarları**'ndan “Kulüp başkanı girişi”ni açması ve **Kullanıcılar** sayfasından her başkana bir hesap oluşturması gerekir.

İzinler her istekte sunucuda kontrol edilir: her sayfanın rolleri `app.py` içinde route'un üstündeki `@rol_gerekli(...)` ile belirlenir, bu satırı taşımayan sayfa kimseye açılmaz. Kulüp başkanı adresi elle yazarak başka bir kulübün kaydına ulaşmaya çalışırsa 403 sayfası görür.

## Ortam değişkenleri

Hepsi isteğe bağlıdır.

| Değişken | Açıklama |
|---|---|
| `PANEL_SECRET_KEY` | Oturum anahtarı. Verilmezse ilk çalıştırmada rastgele üretilip `instance/gizli_anahtar` dosyasında saklanır. |
| `PANEL_HTTPS=1` | Panel HTTPS üzerinden yayınlanıyorsa açın; oturum çerezi yalnızca HTTPS ile gönderilir. |
| `PANEL_KURTARMA_KODU` | “Şifremi unuttum” sayfasında istenen kod. Verilmezse bu sayfa kapalıdır. |
| `PANEL_DEBUG=1` | Geliştirme modu. Gerçek kullanımda açmayın. |
| `PANEL_VERI_KLASORU` | `data/` yerine kullanılacak veri klasörü. |
| `PANEL_YUKLEME_KLASORU` | `uploads/` yerine kullanılacak yükleme klasörü. |

## Veri ve yedek

`data/*.json`, `data/yedek/` ve `uploads/` kişisel bilgi içerir ve `.gitignore`'dadır; depoya gönderilmemelidir. Yedeği ayrıca alın.

## Demo ve tanıtım videosu

`demo/` klasörü gerçek veriye dokunmadan denemek ve tanıtım videosu çekmek içindir:

```
python demo/veri_olustur.py     # örnek kulüp, hesaplar ve başvurular (demo/veri)
python demo/kayit.py            # onay akışını oynatıp demo/video/ altına kaydeder
```

Çekim senaryosu ve demo hesapları: [demo/senaryo.md](demo/senaryo.md).
