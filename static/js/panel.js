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

    // --- Oturum zaman aşımı -------------------------------------------------
    // Sunucu, belirlenen süre boyunca istek gelmezse oturumu kapatır. Sayfa
    // açık bırakıldıysa süre dolmadan önce uyarı verilir, dolunca sayfa yenilenir
    // ve sunucu kullanıcıyı giriş sayfasına yönlendirir.
    const dakika = Number(document.body.dataset.oturumSuresi || 0);
    if (dakika > 0) {
        const sureMs = dakika * 60 * 1000;
        if (sureMs > 3 * 60 * 1000) {
            setTimeout(function () {
                const uyari = document.createElement("div");
                uyari.className = "bildirim bildirim-hata oturum-uyarisi";
                uyari.setAttribute("role", "alert");
                uyari.textContent = "İşlem yapılmadığı için oturumunuz 2 dakika içinde kapanacak. Devam etmek için sayfayı yenileyin veya bir işlem yapın.";
                document.querySelector(".icerik").prepend(uyari);
            }, sureMs - 2 * 60 * 1000);
        }
        setTimeout(() => window.location.reload(), sureMs + 5000);
    }

    // --- Genel arama (üst çubuk) -------------------------------------------
    const arama = document.querySelector("[data-genel-arama]");
    if (arama) {
        const kutu = arama.querySelector("input");
        const liste = arama.querySelector(".arama-sonuclari");
        let zamanlayici = null, secili = -1, istekNo = 0;

        const ogeler = () => Array.from(liste.querySelectorAll(".arama-sonuc"));
        function kapat() {
            liste.hidden = true;
            kutu.setAttribute("aria-expanded", "false");
            secili = -1;
        }
        function sec(i) {
            const tum = ogeler();
            if (!tum.length) return;
            secili = (i + tum.length) % tum.length;
            tum.forEach((o, j) => o.setAttribute("aria-selected", String(j === secili)));
            tum[secili].scrollIntoView({ block: "nearest" });
            kutu.setAttribute("aria-activedescendant", tum[secili].id);
        }
        function goster(veri) {
            liste.replaceChildren();
            if (!veri.sonuclar.length) {
                const bos = document.createElement("div");
                bos.className = "arama-bos";
                bos.textContent = "Sonuç bulunamadı.";
                liste.appendChild(bos);
            }
            veri.sonuclar.forEach(function (s, i) {
                const a = document.createElement("a");
                a.className = "arama-sonuc";
                a.href = s.link;
                a.id = "arama-sonuc-" + i;
                a.setAttribute("role", "option");
                const tur = document.createElement("span");
                tur.className = "arama-tur";
                tur.textContent = s.tur;
                const baslik = document.createElement("span");
                baslik.className = "arama-baslik";
                baslik.textContent = s.baslik;
                const alt = document.createElement("span");
                alt.className = "arama-alt";
                alt.textContent = s.alt;
                a.append(tur, baslik, alt);
                liste.appendChild(a);
            });
            liste.hidden = false;
            kutu.setAttribute("aria-expanded", "true");
            secili = -1;
        }
        kutu.addEventListener("input", function () {
            clearTimeout(zamanlayici);
            const q = kutu.value.trim();
            if (q.length < 2) { kapat(); return; }
            zamanlayici = setTimeout(function () {
                const bu = ++istekNo;
                fetch(arama.dataset.adres + "?q=" + encodeURIComponent(q), { headers: { Accept: "application/json" } })
                    .then((r) => r.json())
                    .then((veri) => { if (bu === istekNo) goster(veri); })
                    .catch(kapat);
            }, 200);
        });
        kutu.addEventListener("keydown", function (e) {
            if (e.key === "ArrowDown") { e.preventDefault(); sec(secili + 1); }
            else if (e.key === "ArrowUp") { e.preventDefault(); sec(secili - 1); }
            else if (e.key === "Enter" && secili >= 0) { e.preventDefault(); ogeler()[secili].click(); }
            else if (e.key === "Escape") { kapat(); arama.classList.remove("acik"); }
        });
        document.addEventListener("click", function (e) {
            if (!arama.contains(e.target)) { kapat(); arama.classList.remove("acik"); }
        });
        arama.querySelector("[data-arama-ac]").addEventListener("click", function () {
            arama.classList.toggle("acik");
            if (arama.classList.contains("acik")) kutu.focus();
        });
    }

    // --- Panoya kopyala ----------------------------------------------------
    document.querySelectorAll("[data-kopyala]").forEach(function (dugme) {
        dugme.addEventListener("click", function () {
            const hedef = document.querySelector(dugme.dataset.kopyala);
            const metin = hedef.value !== undefined ? hedef.value : hedef.textContent;
            const tamam = () => {
                const eski = dugme.textContent;
                dugme.textContent = "Kopyalandı ✓";
                setTimeout(() => (dugme.textContent = eski), 1800);
            };
            if (navigator.clipboard) {
                navigator.clipboard.writeText(metin).then(tamam, () => { hedef.select && hedef.select(); });
            } else if (hedef.select) {
                hedef.select();
                document.execCommand("copy");
                tamam();
            }
        });
    });

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

    // --- Sekme düğmeleri: kapsamdaki gizli filtre alanının değerini ayarlar --
    document.querySelectorAll("[data-sekme]").forEach(function (sekme) {
        sekme.addEventListener("click", function () {
            const grup = sekme.parentElement;
            const alan = grup.querySelector("[data-filtre]");
            alan.value = sekme.dataset.sekme;
            alan.dispatchEvent(new Event("input"));
            grup.querySelectorAll("[data-sekme]").forEach((s) => s.setAttribute("aria-pressed", String(s === sekme)));
        });
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
