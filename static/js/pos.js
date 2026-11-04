(function () {
    "use strict";

    let carrito = [];
    let pollTimer = null;
    let currentRef = null;
    let currentFlujo = null;
    let currentQr = null;

    const $id = (i) => document.getElementById(i);

    function ico(name) {
        return '<svg class="icon"><use href="/static/img/icons.svg#' + name + '"></use></svg>';
    }

    /* ---- Catalogo: filtrar y agregar (delegado, sin onclick inline fragil) ---- */
    window.filtrarProductos = function (q) {
        q = (q || "").toLowerCase();
        document.querySelectorAll("#gridProductos .prod-card").forEach(function (card) {
            card.style.display = card.dataset.search.includes(q) ? "" : "none";
        });
    };

    document.addEventListener("click", function (e) {
        const btn = e.target.closest("[data-add]");
        if (!btn) return;
        const id = btn.dataset.id;
        const nombre = btn.dataset.nombre;
        const precio = parseFloat(btn.dataset.precio);
        const iva = parseFloat(btn.dataset.iva);
        const stock = parseInt(btn.dataset.stock, 10) || 0;
        const cant = parseInt(($id("cant-" + id) || {}).value || "1", 10);
        if (!(cant > 0)) { showNotice("Cantidad invalida.", "error"); return; }
        const existente = carrito.find(function (p) { return p.id === String(id); });
        const nueva = existente ? existente.cantidad + cant : cant;
        if (nueva > stock) { showNotice("Stock insuficiente (" + stock + " disponible).", "error"); return; }
        if (existente) existente.cantidad = nueva;
        else carrito.push({ id: String(id), nombre: nombre, cantidad: cant, precio: precio, iva: iva });
        pintarPOS();
    });

    /* ---- Carrito ---- */
    window.quitarPOS = function (id) {
        carrito = carrito.filter(function (p) { return p.id !== String(id); });
        pintarPOS();
    };

    window.limpiarPOS = function () {
        carrito = [];
        pintarPOS();
    };

    function totales() {
        let sub = 0, iv = 0;
        carrito.forEach(function (p) {
            const base = p.cantidad * p.precio;
            const imp = base * p.iva / 100;
            sub += base; iv += imp;
        });
        return { sub: sub, iv: iv, total: sub + iv };
    }

    function pintarPOS() {
        const tb = $id("carritoBody");
        const fmt = (n) => "$" + formatCOP(n);
        tb.innerHTML = "";
        if (!carrito.length) {
            tb.innerHTML = '<tr><td colspan="4" class="empty-state">Carrito vacio</td></tr>';
        }
        carrito.forEach(function (p) {
            const base = p.cantidad * p.precio;
            const imp = base * p.iva / 100;
            const tr = document.createElement("tr");
            const td1 = document.createElement("td");
            td1.innerHTML = p.nombre + "<br><small class=\"text-muted\">" + fmt(p.precio) + " c/u</small>";
            tr.appendChild(td1);
            [String(p.cantidad), fmt(base + imp)].forEach(function (v) {
                const td = document.createElement("td");
                td.textContent = v;
                tr.appendChild(td);
            });
            const tdBtn = document.createElement("td");
            const del = document.createElement("button");
            del.type = "button";
            del.className = "btn btn-sm btn-ghost icon-btn";
            del.title = "Quitar";
            del.setAttribute("aria-label", "Quitar " + p.nombre);
            del.innerHTML = ico("i-trash");
            del.addEventListener("click", function () { quitarPOS(p.id); });
            tdBtn.appendChild(del);
            tr.appendChild(tdBtn);
            tb.appendChild(tr);
        });
        const t = totales();
        $id("subtotal").textContent = formatCOP(t.sub);
        $id("ivaTotal").textContent = formatCOP(t.iv);
        $id("total").textContent = formatCOP(t.total);
        actualizarCambio(t.total);
    }

    /* ---- Metodos de pago: efectivo con cambio / Bre-B (A y B) con vigencia ---- */
    document.querySelectorAll('input[name="metodo"]').forEach(function (r) {
        r.addEventListener("change", function () {
            const metodo = document.querySelector('input[name="metodo"]:checked').value;
            $id("expWrap").style.display = metodo === "BREB" || metodo === "PREVIO" ? "" : "none";
            $id("cashWrap").style.display = metodo === "EFECTIVO" ? "" : "none";
            actualizarCambio(totales().total);
        });
    });

    function actualizarCambio(total) {
        const box = $id("cambioBox");
        const ingresado = parseFloat($id("monto_recibido").value) || 0;
        if ($id("cashWrap").style.display === "none" || ingresado <= 0) {
            box.style.display = "none";
            return;
        }
        box.style.display = "";
        const dif = ingresado - total;
        if (dif >= 0) {
            box.classList.remove("is-missing");
            box.classList.add("is-ok");
            $id("cambioLabel").textContent = "Cambio a devolver";
            $id("cambioVal").textContent = "$" + formatCOP(dif);
        } else {
            box.classList.remove("is-ok");
            box.classList.add("is-missing");
            $id("cambioLabel").textContent = "Falta por recibir";
            $id("cambioVal").textContent = "$" + formatCOP(Math.abs(dif));
        }
    }

    $id("monto_recibido").addEventListener("input", function () {
        actualizarCambio(totales().total);
    });

    /* ---- Cobrar: flujo B (factura->QR), flujo A (QR->factura al confirmar) o efectivo ---- */
    window.cobrarPOS = async function () {
        const cliente = $id("cliente").value;
        const metodo = document.querySelector('input[name="metodo"]:checked').value;
        if (!cliente) { showNotice("Selecciona el cliente de la venta.", "error"); return; }
        if (!carrito.length) { showNotice("Agrega productos al carrito.", "error"); return; }
        const total = totales().total;
        let cambio = null;
        if (metodo === "EFECTIVO") {
            const ingresado = parseFloat($id("monto_recibido").value);
            if (!(ingresado > 0)) {
                showNotice("Ingresa el monto con el que paga el cliente.", "error");
                $id("monto_recibido").focus();
                return;
            }
            if (ingresado < total) {
                showNotice("El monto recibido ($" + formatCOP(ingresado) + ") no cubre el total ($" + formatCOP(total) + "). Faltan $" + formatCOP(total - ingresado) + ".", "error");
                $id("monto_recibido").focus();
                return;
            }
            cambio = ingresado - total;
        }
        if (metodo !== "EFECTIVO" && total < 10000) {
            showNotice("Factus Pay exige minimo $" + formatCOP(10000) + " para el QR Bre-B. Usa Efectivo.", "error");
            return;
        }
        const fd = new FormData();
        fd.append("cliente", cliente);
        fd.append("productos_json", JSON.stringify(carrito));
        fd.append("metodo_pago", metodo === "PREVIO" ? "PREVIO" : metodo);
        fd.append("expiration", $id("expiration").value);
        if (metodo === "EFECTIVO") fd.append("monto_recibido", $id("monto_recibido").value);
        try {
            if (metodo === "PREVIO") {
                showProgress("Generando recaudo Bre-B (cobro previo)...", 3);
            } else {
                showProgress("Emitiendo factura electronica DIAN", 3);
            }
            const endpoint = metodo === "PREVIO" ? "/crear-cobro-previo" : "/guardar-factura";
            const r = await fetch(endpoint, { method: "POST", body: fd });
            const j = await r.json();
            hideLoading();
            if (!r.ok || !j.success) { showNotice(j.mensaje || "Error al facturar.", "error"); return; }
            showNotice(j.mensaje + " Referencia: " + j.referencia + " / Total: $" + formatCOP(j.total) + (cambio !== null ? " / Cambio: $" + formatCOP(cambio) : ""), "success");
            $id("btnTicket").href = j.ticket_url;
            const pdfBtn = $id("btnPdf");
            const pdfUrl = j.respuesta_factus && j.respuesta_factus.data && j.respuesta_factus.data.links
                ? (j.respuesta_factus.data.links.public_url || "") : "";
            if (pdfUrl) { pdfBtn.href = pdfUrl; pdfBtn.style.display = ""; } else { pdfBtn.style.display = "none"; }
            if (j.pay && j.pay.qr) {
                currentRef = j.referencia;
                currentFlujo = j.flujo || (metodo === "PREVIO" ? "A" : "B");
                currentQr = j.pay.qr;
                $id("qrImg").src = j.pay.qr;
                const dl = $id("btnQrDl");
                dl.href = j.pay.qr;
                dl.setAttribute("download", "QR-Bre-B-" + j.referencia + ".png");
                $id("qrKey").textContent = j.pay.breb_key || "";
                $id("qrTotal").textContent = formatCOP(j.total);
                $id("qrRef").textContent = "Referencia: " + j.referencia;
                $id("qrExp").textContent = "Vence: " + (j.pay.qr_expires_at || "");
                const badge = $id("qrEstado");
                badge.textContent = "Esperando pago";
                badge.className = "qr-status qs-pend";
                $id("qrModal").classList.add("open");
                iniciarPolling();
            } else {
                window.open(j.ticket_url, "_blank");
            }
            carrito = [];
            $id("monto_recibido").value = "";
            pintarPOS();
        } catch (err) {
            hideLoading();
            console.error(err);
            showNotice("Error de red al facturar.", "error");
        }
    };

    /* ---- Polling del recaudo Bre-B (flujo A emite la factura al confirmar) ---- */
    function iniciarPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async function () {
            if (!currentRef) return;
            try {
                const r = await fetch("/api/recaudo/" + encodeURIComponent(currentRef));
                const j = await r.json();
                const st = ((j.pay && j.pay.status) || "").toLowerCase();
                const badge = $id("qrEstado");
                if (st === "paid") {
                    if (currentFlujo === "A") {
                        const fi = j.factura || {};
                        if (fi.emitida) {
                            badge.textContent = "Pagado - factura " + (fi.numero_factura || "emitida");
                            badge.className = "qr-status qs-paid";
                            clearInterval(pollTimer);
                            showNotice("Pago Bre-B confirmado y factura DIAN emitida: " + (fi.numero_factura || ""), "success");
                            const tk = $id("btnTicket");
                            tk.href = "/ticket/" + fi.id_factura;
                        } else {
                            badge.textContent = "Pagado - emitiendo factura DIAN...";
                            badge.className = "qr-status qs-pend";
                        }
                    } else {
                        badge.textContent = "Pagado";
                        badge.className = "qr-status qs-paid";
                        clearInterval(pollTimer);
                        showNotice("Pago Bre-B recibido y confirmado.", "success");
                    }
                } else if (st === "error") {
                    badge.textContent = "Error Pay";
                    badge.className = "qr-status qs-err";
                }
            } catch (e) { /* silencioso */ }
        }, 4000);
    }

    /* ---- Imprimir solo el QR Bre-B (ventana del cajero) ---- */
    window.imprimirQR = function () {
        if (!currentQr) return;
        const w = window.open("", "printqr", "width=420,height=640");
        if (!w) return;
        w.document.write(
            "<html><head><title>QR Bre-B - Bedrok</title>" +
            "<style>body{font-family:monospace;text-align:center;margin:10mm}" +
            "img{width:78mm}h3{margin:4px 0}small{color:#333;line-height:1.5}" +
            "@page{size:80mm auto;margin:3mm}@media print{button{display:none}}</style></head><body>" +
            "<h3>TIENDA BEDROK</h3><p>PAGA CON BRE-B</p>" +
            '<img src="' + currentQr + '" alt="QR">' +
            '<small>' + document.getElementById("qrRef").textContent + "<br>" +
            "Total: $" + document.getElementById("qrTotal").textContent + "<br>" +
            "Llave: " + document.getElementById("qrKey").textContent + "<br>" +
            document.getElementById("qrExp").textContent + "</small>" +
            "<p><button onclick=\"window.print()\">Imprimir</button></p>" +
            '<script>window.onload=function(){setTimeout(function(){window.print()},250)}<' + '/script>' +
            "</body></html>"
        );
        w.document.close();
    };

    window.cerrarQR = function () {
        $id("qrModal").classList.remove("open");
        if (pollTimer) clearInterval(pollTimer);
    };

    $id("qrModal").addEventListener("click", function (e) {
        if (e.target === this) cerrarQR();
    });

    pintarPOS();
})();
