document.addEventListener("DOMContentLoaded", function () {
    const slaytlar = document.querySelectorAll(".hero-slide");
    const noktalar = document.querySelectorAll(".hero-dot");

    if (slaytlar.length === 0) return;

    let aktifIndex = 0;
    const SURE = 7000; // 7 saniye

    function slaydiGoster(index) {
        slaytlar.forEach((s) => s.classList.remove("active"));
        noktalar.forEach((n) => n.classList.remove("active"));
        slaytlar[index].classList.add("active");
        if (noktalar[index]) noktalar[index].classList.add("active");
        aktifIndex = index;
    }

    function sonrakiSlayt() {
        const yeniIndex = (aktifIndex + 1) % slaytlar.length;
        slaydiGoster(yeniIndex);
    }

    let zamanlayici = setInterval(sonrakiSlayt, SURE);

    noktalar.forEach((nokta, index) => {
        nokta.addEventListener("click", function () {
            slaydiGoster(index);
            clearInterval(zamanlayici);
            zamanlayici = setInterval(sonrakiSlayt, SURE);
        });
    });
});