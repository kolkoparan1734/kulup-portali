"""Öğrenci Dekanlığı Kulüp Paneli - yapılandırma.

E-posta gönderimi şimdilik sunucu üzerinden yapılmıyor: duyurular panelde
arşivlenir ve alıcı adresleri "mailto" bağlantısıyla kullanıcının e-posta
programında (Outlook) açılır.

İleride bir e-posta sunucusu (SMTP) eklendiğinde aşağıdaki değerler ortam
değişkenleriyle doldurulup EPOSTA_YONTEMI "smtp" yapılabilir. Şifre gibi gizli
bilgiler bu dosyaya yazılmamalı, ortam değişkeninden okunmalıdır.
"""

import os

# "mailto": duyuru, kullanıcının e-posta programında açılır (şu anki yöntem)
# "smtp"  : duyuru, aşağıdaki sunucu üzerinden panelden gönderilir (henüz uygulanmadı)
EPOSTA_YONTEMI = os.environ.get("PANEL_EPOSTA_YONTEMI", "mailto")

SMTP_SUNUCU = os.environ.get("PANEL_SMTP_SUNUCU", "")          # ör. smtp.office365.com
SMTP_PORT = int(os.environ.get("PANEL_SMTP_PORT", "587"))
SMTP_KULLANICI = os.environ.get("PANEL_SMTP_KULLANICI", "")    # ör. ogrencidekanligi@altinbas.edu.tr
SMTP_SIFRE = os.environ.get("PANEL_SMTP_SIFRE", "")
SMTP_TLS = os.environ.get("PANEL_SMTP_TLS", "1") == "1"

# Duyuruların gönderen adresi; mailto yönteminde e-posta programının hesabı kullanılır.
GONDEREN_ADRES = os.environ.get("PANEL_GONDEREN_ADRES", "")
GONDEREN_AD = "Altınbaş Üniversitesi Öğrenci Dekanlığı"

# Alıcılar duyuruda birbirini görmesin diye "Gizli (BCC)" alanına yazılır.
ALICILAR_GIZLI = True

# Çok uzun mailto bağlantılarını bazı e-posta programları kesebilir; bu uzunluğu
# aşan duyurularda kullanıcıya adresleri kopyalayıp yapıştırması önerilir.
MAILTO_UZUNLUK_SINIRI = 1800
