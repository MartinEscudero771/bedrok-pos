(function () {
    "use strict";

    // 555555 -> "555.555" ; 14875.5 -> "14.875,50"
    window.formatCOP = function (n) {
        const num = Number(n) || 0;
        const neg = num < 0;
        const s = Math.abs(num);
        let ent = Math.floor(s);
        let dec = Math.round((s - ent) * 100);
        if (dec === 100) { ent += 1; dec = 0; }
        const miles = String(ent).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        return (neg ? "-" : "") + miles + (dec ? "," + String(dec).padStart(2, "0") : "");
    };

    window.money = function (n) {
        return "$" + window.formatCOP(n);
    };

    let locked = false;
    let loadingElement;

    function getLoadingElement() {
        if (loadingElement) return loadingElement;
        loadingElement = document.createElement("div");
        loadingElement.id = "ui-loading";
        loadingElement.hidden = true;
        loadingElement.setAttribute("aria-live", "polite");
        loadingElement.innerHTML =
            '<div class="loading-card"><span class="spinner" aria-hidden="true"></span>' +
            "<span id=\"ui-loading-text\">Procesando, espera un momento...</span>" +
            '<div class="progress-wrap" id="ui-progress" hidden>' +
            '<div class="progress-track"><div class="progress-bar" id="ui-progress-bar"></div></div>' +
            '<div class="progress-info" id="ui-progress-info"></div>' +
            "</div></div>";
        document.body.appendChild(loadingElement);
        return loadingElement;
    }

    window.showLoading = function () {
        locked = true;
        document.body.setAttribute("aria-busy", "true");
        document.querySelectorAll("button, a, input, select, textarea").forEach(function (element) {
            if (element.id !== "ui-loading") element.setAttribute("data-ui-disabled", element.disabled ? "true" : "false");
            if ("disabled" in element) element.disabled = true;
        });
        getLoadingElement().hidden = false;
    };

    /* Barra de progreso con cuenta atras (3-2-1 s) mientras se emite la factura electronica */
    window.showProgress = function (message, seconds) {
        showLoading();
        const wrap = getLoadingElement();
        const text = wrap.querySelector("#ui-loading-text");
        const block = wrap.querySelector("#ui-progress");
        const bar = wrap.querySelector("#ui-progress-bar");
        const info = wrap.querySelector("#ui-progress-info");
        if (message) text.textContent = message;
        let restantes = Math.max(1, parseInt(seconds || 3, 10));
        if (block && bar && info) {
            block.hidden = false;
            bar.style.animation = "none";
            void bar.offsetWidth;
            bar.style.animation = "loadbar " + restantes + "s ease-out forwards";
        }
        if (info) {
            clearInterval(showProgress._timer);
            const pintar = function () {
                info.textContent = (message ? message + " " : "") +
                    "(" + restantes + " s restantes)";
            };
            pintar();
            showProgress._timer = setInterval(function () {
                restantes -= 1;
                if (restantes <= 0) {
                    clearInterval(showProgress._timer);
                    info.textContent = (message ? message + " " : "") + "Finalizando...";
                } else {
                    pintar();
                }
            }, 1000);
        }
    };

    const _hideLoading = window.hideLoading;
    window.hideLoading = function () {
        clearInterval(showProgress._timer);
        if (loadingElement) {
            const block = loadingElement.querySelector("#ui-progress");
            if (block) block.hidden = true;
            const text = loadingElement.querySelector("#ui-loading-text");
            if (text) text.textContent = "Procesando, espera un momento...";
        }
        return _hideLoading();
    };

    window.hideLoading = function () {
        locked = false;
        document.body.removeAttribute("aria-busy");
        document.querySelectorAll("[data-ui-disabled]").forEach(function (element) {
            if (element.dataset.uiDisabled === "false") element.removeAttribute("disabled");
            element.removeAttribute("data-ui-disabled");
        });
        getLoadingElement().hidden = true;
    };

    window.showNotice = function (message, type) {
        const notice = document.createElement("div");
        notice.className = "mensaje " + (type === "error" ? "error" : "success");
        notice.setAttribute("role", "alert");
        notice.textContent = message;
        const container = document.querySelector(".contenedor, .page-shell");
        if (container) container.prepend(notice);
        window.setTimeout(function () { notice.remove(); }, 6000);
    };

    document.addEventListener("click", function (event) {
        const link = event.target.closest("a[href]");
        if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
        if (locked) {
            event.preventDefault();
            return;
        }
        showLoading();
    });

    document.addEventListener("submit", function (event) {
        if (locked) {
            event.preventDefault();
            return;
        }
        // facturas.js maneja su propio envio (fetch) y su propio loading
        if (event.defaultPrevented) return;
        // Se difiere para que el navegador lea los campos antes de deshabilitarlos
        window.setTimeout(showLoading, 0);
    });

    window.addEventListener("pageshow", hideLoading);
})();
