async function verQR(ref, btn) {
    btn.disabled = true;
    try {
        const r = await fetch("/api/recaudo/" + encodeURIComponent(ref));
        const j = await r.json();
        const box = document.getElementById("qrBox");
        box.style.display = "block";
        document.getElementById("qrRef").textContent = ref;
        document.getElementById("qrImg").src = (j.pay && j.pay.qr) || "";
        document.getElementById("qrSt").textContent = (j.pay && j.pay.status) || "?";
        document.getElementById("qrKey").textContent = (j.pay && j.pay.breb_key) || "";
        document.getElementById("qrExp").textContent = (j.pay && j.pay.qr_expires_at) || "";
        box.scrollIntoView({ behavior: "smooth" });
    } catch (e) {
        alert("No se pudo consultar el recaudo.");
    }
    btn.disabled = false;
}

async function refrescarConciliacion(btn) {
    if (btn) btn.disabled = true;
    try {
        const r = await fetch("/api/conciliacion");
        const j = await r.json();
        pintarStats(j.stats);
    } catch (e) { /* silencioso */ }
    if (btn) btn.disabled = false;
}

async function conciliarAhora(btn) {
    if (btn) btn.disabled = true;
    try {
        const r = await fetch("/api/conciliar", { method: "POST" });
        const j = await r.json();
        pintarStats(j.stats);
        let msg = "Conciliacion: " + (j.pagados || 0) + " pagos confirmados, " +
            (j.emitidas || 0) + " facturas emitidas.";
        if (j.errores && j.errores.length) msg += " Problemas: " + j.errores[0];
        showNotice(msg, "success");
    } catch (e) {
        showNotice("No fue posible conciliar con Factus Pay.", "error");
    }
    if (btn) btn.disabled = false;
}

function pintarStats(s) {
    if (!s) return;
    document.getElementById("st-ventas").textContent = s.ventas_hoy ?? "0";
    document.getElementById("st-validadas").textContent = s.validadas_hoy ?? "0";
    document.getElementById("st-facturado").textContent = "$" + formatCOP(s.monto_facturado_hoy || 0);
    document.getElementById("st-pagos").textContent = s.pagos_hoy ?? "0";
    document.getElementById("st-recaudado").textContent = "$" + formatCOP(s.monto_recaudado_hoy || 0);
    document.getElementById("st-por").textContent = s.por_facturar ?? "0";
}

refrescarConciliacion(null);
setInterval(() => refrescarConciliacion(null), 20000);
