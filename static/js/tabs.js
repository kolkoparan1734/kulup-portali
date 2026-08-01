// Bu dosya, kulüp detay sayfasındaki "Yönetim Kurulu", "Etkinlikler" ve
// "Forum" sekmeleri arasında geçiş yapılmasını sağlar.

document.addEventListener("DOMContentLoaded", function () {
    const sekmeButonlari = document.querySelectorAll(".tab-button");
    const sekmePaneller = document.querySelectorAll(".tab-panel");

    sekmeButonlari.forEach(function (buton) {
        buton.addEventListener("click", function () {
            const hedefId = buton.getAttribute("data-tab");

            // Önce tüm butonlardan ve panellerden "active" sınıfını kaldır.
            sekmeButonlari.forEach((b) => b.classList.remove("active"));
            sekmePaneller.forEach((p) => p.classList.remove("active"));

            // Tıklanan butonu ve ona karşılık gelen paneli aktif yap.
            buton.classList.add("active");
            document.getElementById(hedefId).classList.add("active");
        });
    });

    // Sayfa adresinde #forum gibi bir "hash" varsa (örn. forum mesajı
    // gönderdikten sonra buraya yönlendirildiysek), o sekmeyi otomatik açar.
    const hash = window.location.hash.replace("#", "");
    if (hash) {
        const hedefButon = document.querySelector(`.tab-button[data-tab="${hash}"]`);
        if (hedefButon) {
            hedefButon.click();
        }
    }
});