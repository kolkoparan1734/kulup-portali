"""Öğrenci numarası doğrulama ve üretim yardımcıları.

Öğrenci numarası 9 haneli olup ilk iki hanesi öğrencinin giriş yılının son
iki hanesidir (ör. 2025 girişli bir öğrenci "25" ile başlayan bir numaraya
sahiptir, "250200782" gibi). Portalda yalnızca 2020-2026 yılları arasında
kayıt olmuş öğrenciler bulunduğu için geçerli yıl önekleri bu aralıkla
sınırlıdır; "19..." veya "27..." ile başlayan bir numara geçersiz sayılır.
"""

import random

GECERLI_YILLAR = range(2020, 2027)
GECERLI_YIL_ONEKLERI = {str(yil)[-2:] for yil in GECERLI_YILLAR}


def gecerli_mi(numara):
    """Öğrenci numarasının 9 haneli olup olmadığını ve geçerli bir yıl önekiyle
    başlayıp başlamadığını döndürür."""
    return (
        isinstance(numara, str)
        and numara.isdigit()
        and len(numara) == 9
        and numara[:2] in GECERLI_YIL_ONEKLERI
    )


def rastgele_ogrenci_no(kullanilmis=None):
    """Geçerli aralıkta, verilen kümede henüz olmayan rastgele bir öğrenci numarası üretir."""
    kullanilmis = kullanilmis if kullanilmis is not None else set()
    while True:
        onek = random.choice(sorted(GECERLI_YIL_ONEKLERI))
        kalan = f"{random.randint(0, 9_999_999):07d}"
        numara = onek + kalan
        if numara not in kullanilmis:
            return numara
