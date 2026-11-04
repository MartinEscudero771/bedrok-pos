
let productosFactura = [];

function agregarProducto() {
    const selector = document.getElementById("producto");
    const opcion = selector.options[selector.selectedIndex];

    if (!opcion.value) {
        showNotice("Selecciona un producto.", "error");
        return;
    }

    const cantidad = parseInt(
        document.getElementById("cantidad").value
    );

    const precio = parseFloat(opcion.dataset.precio);
    const iva = parseFloat(opcion.dataset.iva);
    const stock = parseInt(opcion.dataset.stock);

    if (!Number.isInteger(cantidad) || cantidad <= 0) {
        showNotice("Ingresa una cantidad válida.", "error");
        return;
    }

    const id = opcion.value;

    const existente = productosFactura.find(p => p.id === id);

    const nuevaCantidad = existente
        ? existente.cantidad + cantidad
        : cantidad;

    if (nuevaCantidad > stock) {
        showNotice("No hay suficiente inventario.", "error");
        return;
    }

    if (existente) {
        existente.cantidad = nuevaCantidad;
    } else {
        productosFactura.push({
            id: id,
            nombre: opcion.dataset.nombre,
            cantidad: cantidad,
            precio: precio,
            iva: iva
        });
    }

    mostrarFactura();
}

function mostrarFactura() {
    const tabla = document.getElementById("detalleFactura");

    tabla.innerHTML = "";

    let subtotal = 0;
    let ivaTotal = 0;

    productosFactura.forEach(producto => {
        const base = producto.cantidad * producto.precio;
        const impuesto = base * producto.iva / 100;
        const totalProducto = base + impuesto;

        subtotal += base;
        ivaTotal += impuesto;

        const fila = document.createElement("tr");

        [
            producto.nombre,
            producto.cantidad,
            "$" + formatCOP(producto.precio),
            "$" + formatCOP(impuesto),
            "$" + formatCOP(totalProducto)
        ].forEach(valor => {
            const celda = document.createElement("td");
            celda.textContent = valor;
            fila.appendChild(celda);
        });

        tabla.appendChild(fila);
    });

    document.getElementById("subtotal").textContent =
        formatCOP(subtotal);

    document.getElementById("ivaTotal").textContent =
        formatCOP(ivaTotal);

    document.getElementById("total").textContent =
        formatCOP(subtotal + ivaTotal);
}

document.getElementById("formularioFactura").addEventListener(
    "submit",
    async function(event) {
        event.preventDefault();

        const cliente = document.getElementById("cliente").value;

        if (!cliente || productosFactura.length === 0) {
            showNotice("Selecciona un cliente y agrega productos.", "error");
            return;
        }

        showLoading();
        showProgress("Emitiendo factura electronica DIAN", 3);
        const datos = new FormData();

        datos.append("cliente", cliente);
        datos.append(
            "productos_json",
            JSON.stringify(productosFactura)
        );
        const metodoSel = document.getElementById("metodo_pago_ui");
        const metodo = metodoSel ? metodoSel.value : "EFECTIVO";
        datos.append("metodo_pago", metodo);
        const expEl = document.getElementById("expiration");
        datos.append("expiration", expEl ? expEl.value : "86400");
        if (metodo === "EFECTIVO") {
            const montoVal = parseFloat(document.getElementById("monto_recibido").value) || 0;
            const totalActual = subtotal + ivaTotal;
            if (!(montoVal > 0)) {
                showNotice("Ingresa el efectivo recibido del cliente.", "error");
                hideLoading();
                return;
            }
            if (montoVal < totalActual) {
                showNotice("El monto recibido no cubre el total de la factura.", "error");
                hideLoading();
                return;
            }
            datos.append("monto_recibido", document.getElementById("monto_recibido").value);
        }

        try {
            const respuesta = await fetch("/guardar-factura", {
                method: "POST",
                body: datos
            });

            const resultado = await respuesta.json();

            if (!respuesta.ok) {
                showNotice(resultado.mensaje || "No fue posible guardar la factura.", "error");
                hideLoading();
                return;
            }

            showNotice(
                resultado.mensaje +
                " Referencia: " + resultado.referencia +
                (resultado.total !== undefined ? " | Total: $" + resultado.total : ""),
                "success"
            );

            productosFactura = [];
            mostrarFactura();

            const box = document.getElementById("payResult");
            if (box) {
                let html = `<p><a class="btn" target="_blank" href="${resultado.ticket_url}">Ver / imprimir ticket</a></p>`;
                if (resultado.pay && resultado.pay.qr) {
                    html += `<p><b>Llave Bre-B:</b> <code>${resultado.pay.breb_key || ""}</code><br>
                             <img src="${resultado.pay.qr}" style="max-width:260px;border:1px solid var(--line);border-radius:6px" alt="QR Bre-B"></p>
                             <p><small>Consulta el estado en <a target="_blank" href="${resultado.ticket_url}">el ticket</a> o con GET /api/recaudo/${resultado.referencia}</small></p>`;
                }
                const pdfUrl = resultado.respuesta_factus && resultado.respuesta_factus.data && resultado.respuesta_factus.data.links
                    ? (resultado.respuesta_factus.data.links.public_url || "") : "";
                if (pdfUrl) html += `<p><b>Verificacion:</b><br><a target="_blank" href="${pdfUrl}">${pdfUrl}</a></p>`;
                box.style.display = "block";
                box.innerHTML = html;
                box.scrollIntoView({behavior: "smooth"});
            }

        } catch (error) {
            console.error(error);
            showNotice("No fue posible guardar la factura.", "error");
        } finally {
            hideLoading();
        }
    }
);
