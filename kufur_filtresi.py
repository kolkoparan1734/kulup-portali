"""Forum mesajları ve kullanıcı adları için basit bir Türkçe küfür/argo filtresi.

Yaklaşım: metni küçük harfe çevirip Türkçe harfleri sadeleştiriyoruz (ör. "ş" -> "s"),
böylece hem Türkçe klavyeyle hem de sade ASCII ile yazılan küfürler tek bir
kelime listesiyle yakalanabiliyor. "sik" gibi kısa kökler "sikke" gibi masum
kelimeleri de yakalayabildiği için AK_LISTESI ile bu tür istisnalar hariç tutuluyor.
"""

import re

# Kaçırma amaçlı rakam/işaret kullanımını (a5k, s1ktir gibi) normalize eder.
_LEETSPEAK = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "@": "a", "$": "s", "+": "t",
})

# Python'un varsayılan .lower() metodu Türkçe "İ"/"I" harflerini yanlış
# çevirdiği için (İ -> i̇, I -> i) önce elle eşleniyor.
_TR_BUYUK_HARF = str.maketrans({"İ": "i", "I": "ı"})

_TR_SADELESTIR = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
})

# Kökler (sadeleştirilmiş hallerinin bir kelimenin BAŞINDA geçmesi aranır,
# böylece "siktir", "sikik", "sikerim" gibi tüm çekimler tek kökle yakalanır).
KOTU_KOKLER = [
    "siktir", "sikeyim", "sikerim", "sikik", "sikis", "sik",
    "yarra", "yarak", "yarag",
    "amcik", "amina",
    "orospu", "orospi",
    "pic",
    "kahpe", "kaltak",
    "pezevenk",
    "ibne",
    "got",
    "dalyarak",
    "gerizekali",
    "salak", "aptal",
    "serefsiz", "namussuz",
    "pust", "yavsak",
    "surtuk", "fahise",
    "deyyus",
    "anani", "bacini",
]

# Kısa/çok anlamlı kısaltmalar: yalnızca tek başına bir kelime olarak
# geçtiklerinde ("am" gibi) sayılır; başka kelimelerin içinde ("amaç",
# "tamam") arandığında anlamsız eşleşmelere yol açar.
KISA_TAM_KELIMELER = {"am", "amk", "aq", "oc"}

# KOTU_KOKLER içindeki kısa köklerle başlayan ama küfür olmayan kelimeler.
AK_LISTESI = {"sikke", "sikkeler", "sikkesi", "sikkeleri", "sikkelerin", "sikkeye", "sikkeyi"}

_KOTU_KOKLER = [kok.translate(_TR_SADELESTIR) for kok in KOTU_KOKLER]
_KELIME_DESENI = re.compile(r"[a-z]+")


def _normallestir(metin):
    metin = metin.translate(_TR_BUYUK_HARF).lower()
    metin = metin.translate(_LEETSPEAK)
    metin = metin.translate(_TR_SADELESTIR)
    # Harf tekrarlarıyla sansürü atlatma girişimlerini engeller (siktiiir -> siktir).
    metin = re.sub(r"(.)\1{2,}", r"\1", metin)
    return metin


def uygunsuz_icerik_mi(metin):
    """Metinde küfür/argo kelime geçip geçmediğini döndürür (bool)."""
    if not metin:
        return False

    normal_metin = _normallestir(metin)
    kelimeler = _KELIME_DESENI.findall(normal_metin)
    if not kelimeler:
        return False

    for kelime in kelimeler:
        if kelime in AK_LISTESI:
            continue
        if kelime in KISA_TAM_KELIMELER:
            return True
        if any(kelime.startswith(kok) for kok in _KOTU_KOKLER):
            return True

    # Boşluk/noktalama ile aranan kelimeleri bölerek filtreyi atlatma
    # girişimlerini ("s i k t i r", "s.i.k.t.i.r") yakalamak için ayrıca
    # bitişik hâlde de kontrol ediyoruz (yalnızca uzun/ayırt edici kökler).
    bitisik = "".join(kelimeler)
    return any(len(kok) >= 5 and kok in bitisik for kok in _KOTU_KOKLER)
