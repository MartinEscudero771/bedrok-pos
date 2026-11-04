(function () {
    "use strict";

    let carrito = [];
    let tasa = window.TASA_USD_COP || null;

    const $id = (i) => document.getElementById(i);

    function refreshTasaLabel(data) {
        if (data && data.tasa) {
            tasa = data.tasa;
            $id("tasaLabel").textContent = Number(tasa).toFixed(2) +
                (data.fuente ? " (" + data.fuente + ")" : "");
            const act = $id("tasaAct");
            if (act) act.textContent = "Tasa actualizada " + new Date().toLocaleTimeString("es-CO");
            pintar();
        }
    }

    /* Tasa en vivo: consulta la API publica cada 60 s */
    async function tickTasa() {
        try {
            const r = await fetch("/api/tasa");
            const j = await r.json();
            if (j.success) refreshTasaLabel(j);
        } catch (e) { /* silencioso */ }
    }
    setInterval(tickTasa, 60000);

    window.refrescarTasa = async function (btn) {
        btn.disabled = true;
        try {
            const r = await fetch("/api/tasa");
            const j = await r.json();
            if (j.success) { refreshTasaLabel(j); showNotice("Tasa actualizada: " + Number(j.tasa).toFixed(2) + " COP/USD", "success"); }
            else { showNotice("No fue posible actualizar la tasa: " + (j.error || "?"), "error"); }
        } catch (e) { showNotice("Error de red al actualizar la tasa.", "error"); }
        btn.disabled = false;
    };

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
        const cant = parseInt(($id("cant-" + id) || {}).value || "1", 10);
        const stock = parseInt(btn.dataset.stock, 10) || 0;
        if (!(cant > 0)) { showNotice("Cantidad invalida.", "error"); return; }
        const ex = carrito.find(p => p.id === String(id));
        const nueva = ex ? ex.cantidad + cant : cant;
        if (nueva > stock) { showNotice("Stock insuficiente (" + stock + ").", "error"); return; }
        if (ex) ex.cantidad = nueva;
        else carrito.push({
            id: String(id), nombre: btn.dataset.nombre, cantidad: cant,
            precio: parseFloat(btn.dataset.precio), iva: parseFloat(btn.dataset.iva),
        });
        pintar();
    });

    window.limpiarPedido = function () {
        carrito = [];
        $id("monto_usd").value = "";
        pintar();
    };

    function totales() {
        let sub = 0, iv = 0;
        carrito.forEach(p => {
            sub += p.cantidad * p.precio;
            iv += (p.cantidad * p.precio) * p.iva / 100;
        });
        return { sub: sub, iv: iv, total: sub + iv };
    }

    function pintar() {
        const tb = $id("carritoBody");
        tb.innerHTML = "";
        if (!carrito.length) {
            tb.innerHTML = '<tr><td colspan="3" class="empty-state">Pedido vacio</td></tr>';
        }
        carrito.forEach(p => {
            const base = p.cantidad * p.precio;
            const imp = base * p.iva / 100;
            const tr = document.createElement("tr");
            const td1 = document.createElement("td");
            td1.innerHTML = p.nombre + "<br><small class=\"text-muted\">" + "$" + formatCOP(p.precio) + " c/u</small>";
            tr.appendChild(td1);
            const td2 = document.createElement("td");
            td2.textContent = String(p.cantidad);
            tr.appendChild(td2);
            const td3 = document.createElement("td");
            td3.textContent = "$" + formatCOP(base + imp);
            tr.appendChild(td3);
            tb.appendChild(tr);
        });
        const t = totales();
        $id("subtotal").textContent = formatCOP(t.sub);
        $id("ivaTotal").textContent = formatCOP(t.iv);
        $id("total").textContent = formatCOP(t.total);
        $id("totalUsd").textContent = tasa ? (t.total / tasa).toFixed(2) : "-";
        actualizarCambio(t.total);
    }

    function actualizarCambio(total) {
        const box = $id("cambioBox"), boxCop = $id("cambioCopBox");
        const entregado = parseFloat($id("monto_usd").value) || 0;
        if (!(tasa > 0) || entregado <= 0) {
            box.style.display = "none";
            boxCop.style.display = "none";
            return;
        }
        const equiv = total / tasa;
        const dif = entregado - equiv;
        box.style.display = ""; boxCop.style.display = "";
        if (dif >= 0) {
            box.classList.remove("is-missing"); box.classList.add("is-ok");
            $id("cambioLabel").textContent = "Cambio en USD";
            $id("cambioVal").textContent = "US$ " + dif.toFixed(2);
            boxCop.classList.remove("is-missing"); boxCop.classList.add("is-ok");
            $id("cambioCopVal").textContent = "$" + formatCOP(dif * tasa);
        } else {
            box.classList.remove("is-ok"); box.classList.add("is-missing");
            $id("cambioLabel").textContent = "Falta en USD";
            $id("cambioVal").textContent = "US$ " + Math.abs(dif).toFixed(2);
            boxCop.classList.remove("is-ok"); boxCop.classList.add("is-missing");
            $id("cambioCopVal").textContent = "$" + formatCOP(Math.abs(dif) * tasa);
        }
    }

    $id("monto_usd").addEventListener("input", () => actualizarCambio(totales().total));

    window.cobrarPedido = async function () {
        if (!(tasa > 0)) { showNotice("La tasa de cambio no esta disponible.", "error"); return; }
        const cliente = $id("cliente").value;
        if (!cliente) { showNotice("Selecciona el cliente del pedido.", "error"); return; }
        if (!carrito.length) { showNotice("Agrega productos al pedido.", "error"); return; }
        const entregado = parseFloat($id("monto_usd").value) || 0;
        if (!(entregado > 0)) {
            showNotice("Ingresa el monto en dolares con el que paga el cliente.", "error");
            return;
        }
        const total = totales().total;
        const equiv = total / tasa;
        if (entregado < equiv) {
            showNotice("El monto entregado (US$ " + entregado.toFixed(2) + ") no cubre el pedido (US$ " + equiv.toFixed(2) + ").", "error");
            return;
        }
        showLoading();
        const fd = new FormData();
        fd.append("cliente", cliente);
        fd.append("productos_json", JSON.stringify(carrito));
        fd.append("monto_usd", String(entregado));
        try {
            const r = await fetch("/guardar-pedido", { method: "POST", body: fd });
            const j = await r.json();
            hideLoading();
            if (!r.ok || !j.success) { showNotice(j.mensaje || "Error al registrar el pedido.", "error"); return; }
            showNotice(
                "Pedido " + j.referencia + " facturado en doble moneda. Total $" + formatCOP(j.total) +
                " = US$ " + j.equivalente_usd.toFixed(2) + ". Cambio: US$ " + j.cambio_usd.toFixed(2) +
                " ($" + formatCOP(j.cambio_cop) + ").",
                "success"
            );
            window.open(j.ticket_url, "_blank");
            carrito = [];
            $id("monto_usd").value = "";
            pintar();
        } catch (err) {
            hideLoading(); console.error(err);
            showNotice("Error de red al facturar el pedido.", "error");
        }
    };

    pintar();
})();
