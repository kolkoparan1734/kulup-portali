// Bu dosya, kulüp detay sayfasındaki "Yönetim Kurulu" ve "Etkinlikler"
// sekmeleri arasında geçiş yapılmasını sağlar.

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
});
