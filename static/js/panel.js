// Kulüp Paneli ortak davranışları:
//  - mobilde sol menünün açılıp kapanması
//  - silme gibi işlemlerden önce onay sorulması (form[data-onay])
//  - kart/tablo arama ve filtreleri ([data-filtre-kapsam])
//  - tablo sütunlarına tıklayarak sıralama (th[data-sirala])

document.addEventListener("DOMContentLoaded", function () {
    const kucult = (metin) => (metin || "").toLocaleLowerCase("tr");

    // --- Mobil menü -------------------------------------------------------
    const menuDugme = document.querySelector(".menu-dugme");
    const perde = document.querySelector(".menu-perde");
    function menuAyarla(acik) {
        document.body.classList.toggle("menu-acik", acik);
        if (menuDugme) menuDugme.setAttribute("aria-expanded", String(acik));
        if (perde) perde.hidden = !acik;
    }
    if (menuDugme) {
        menuDugme.addEventListener("click", () => menuAyarla(!document.body.classList.contains("menu-acik")));
        perde.addEventListener("click", () => menuAyarla(false));
        document.addEventListener("keydown", (e) => { if (e.key === "Escape") menuAyarla(false); });
    }

    // --- Silme onayı ------------------------------------------------------
    document.querySelectorAll("form[data-onay]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (!window.confirm(form.dataset.onay)) e.preventDefault();
        });
    });

    // --- Arama ve filtreler -----------------------------------------------
    // Kapsam içindeki [data-filtre] alanları, data-filtre-oge seçicisine uyan
    // öğeleri süzer. "metin" alanı öğenin data-metin değerinde arar, diğer
    // alanlar öğenin aynı adlı data-* değeriyle birebir karşılaştırılır.
    document.querySelectorAll("[data-filtre-kapsam]").forEach(function (kapsam) {
        const ogeler = Array.from(kapsam.querySelectorAll(kapsam.dataset.filtreOge));
        const alanlar = Array.from(kapsam.querySelectorAll("[data-filtre]"));
        const sayac = kapsam.querySelector("[data-filtre-sayac]");
        const bos = kapsam.querySelector("[data-filtre-bos]");

        function uygula() {
            let gorunen = 0;
            ogeler.forEach(function (oge) {
                const uygun = alanlar.every(function (alan) {
                    const ad = alan.dataset.filtre;
                    if (alan.type === "checkbox") return !alan.checked || oge.dataset[ad] === "1";
                    if (!alan.value) return true;
                    if (ad === "metin") return kucult(oge.dataset.metin).includes(kucult(alan.value.trim()));
                    return oge.dataset[ad] === alan.value;
                });
                oge.hidden = !uygun;
                if (uygun) gorunen++;
            });
            if (sayac) sayac.textContent = gorunen;
            if (bos) bos.hidden = gorunen !== 0;
        }

        alanlar.forEach((alan) => alan.addEventListener(alan.tagName === "INPUT" && alan.type !== "checkbox" ? "input" : "change", uygula));
        uygula();
    });

    // --- Tablo sıralama ---------------------------------------------------
    document.querySelectorAll("table").forEach(function (tablo) {
        const basliklar = tablo.querySelectorAll("th[data-sirala]");
        basliklar.forEach(function (th) {
            th.tabIndex = 0;
            th.setAttribute("role", "button");
            function sirala() {
                const sutun = Array.from(th.parentNode.children).indexOf(th);
                const artan = th.getAttribute("aria-sort") !== "ascending";
                basliklar.forEach((b) => b.removeAttribute("aria-sort"));
                th.setAttribute("aria-sort", artan ? "ascending" : "descending");

                const govde = tablo.tBodies[0];
                const satirlar = Array.from(govde.rows);
                const deger = (satir) => {
                    const hucre = satir.cells[sutun];
                    return hucre ? (hucre.dataset.deger ?? hucre.textContent.trim()) : "";
                };
                const sayisal = th.dataset.sirala === "sayi";
                satirlar.sort(function (a, b) {
                    let x = deger(a), y = deger(b);
                    // Boş değerler her zaman sona gider.
                    if (!x && y) return 1;
                    if (x && !y) return -1;
                    const sonuc = sayisal ? Number(x) - Number(y) : x.localeCompare(y, "tr", { numeric: true });
                    return artan ? sonuc : -sonuc;
                });
                satirlar.forEach((s) => govde.appendChild(s));
            }
            th.addEventListener("click", sirala);
            th.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sirala(); } });
        });
    });

    // --- Yönetim kurulu satırı ekleme (kulüp formu) ----------------------
    const ykEkle = document.querySelector("[data-yk-ekle]");
    if (ykEkle) {
        ykEkle.addEventListener("click", function () {
            const liste = document.querySelector("[data-yk-liste]");
            const yeni = liste.querySelector(".yk-satir").cloneNode(true);
            yeni.querySelectorAll("input").forEach((i) => (i.value = ""));
            liste.appendChild(yeni);
            yeni.querySelector("input").focus();
        });
        document.addEventListener("click", function (e) {
            const sil = e.target.closest("[data-yk-sil]");
            if (!sil) return;
            const liste = document.querySelector("[data-yk-liste]");
            const satir = sil.closest(".yk-satir");
            if (liste.children.length > 1) satir.remove();
            else satir.querySelectorAll("input").forEach((i) => (i.value = ""));
        });
    }
});
