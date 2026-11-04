import mysql.connector

PRODUCTOS = [
    # (codigo, nombre, descripcion, precio, iva, stock)
    ("BED-001", "Cafe molido 500g", "Cafe premium", 12500, "19.00", 50),
    ("BED-002", "Arroz 1kg", "Arroz blanco", 5200, "19.00", 100),
    ("BED-003", "Panela 1kg", "Panela natural", 6800, "19.00", 80),
    ("BED-004", "Leche entera 1L", "Leche larga vida", 4500, "0.00", 120),
    ("BED-005", "Huevo AA cubeta x30", "Huevos frescos tipo AA", 16500, "5.00", 60),
    ("BED-006", "Aceite girasol 1L", "Aceite vegetal", 9200, "19.00", 90),
    ("BED-007", "Azucar blanca 1kg", "Azucar refinada", 4800, "19.00", 110),
    ("BED-008", "Sal marina 500g", "Sal refinada", 2200, "19.00", 150),
    ("BED-009", "Harina de trigo 1kg", "Multiproposito", 3900, "19.00", 95),
    ("BED-010", "Pasta espagueti 500g", "Pasta trigo duro", 3200, "19.00", 130),
    ("BED-011", "Atun en aceite 300g", "Conserva", 6900, "19.00", 85),
    ("BED-012", "Frijol blanco 500g", "Legumbre", 4700, "19.00", 75),
    ("BED-013", "Lentejas 500g", "Legumbre", 4200, "19.00", 75),
    ("BED-014", "Cafe instantaneo 100g", "Soluble", 8900, "19.00", 70),
    ("BED-015", "Galletas saladas 250g", "Snack horneado", 3100, "19.00", 140),
    ("BED-016", "Chocolate en polvo 400g", "Bebible", 7500, "19.00", 65),
    ("BED-017", "Shampoo 400ml", "Cuidado personal", 11800, "19.00", 55),
    ("BED-018", "Jabon corporal 250g", "Cuidado personal", 5200, "19.00", 100),
    ("BED-019", "Crema dental 100ml", "Higiene", 6300, "19.00", 110),
    ("BED-020", "Papel higienico x4", "Higiene hogar", 7400, "19.00", 120),
    ("BED-021", "Detergente 1kg", "Aseo", 9600, "19.00", 80),
    ("BED-022", "Jabon de barra x3", "Aseo", 4100, "19.00", 125),
    ("BED-023", "Agua sin gas 600ml", "Hidratacion", 1900, "19.00", 250),
    ("BED-024", "Gaseosa 1.5L", "Bebida", 5800, "19.00", 150),
    ("BED-025", "Malta 355ml", "Bebida", 3400, "19.00", 140),
    ("BED-026", "Snack de papas 150g", "Snack", 4600, "19.00", 160),
    ("BED-027", "Pan artesanal 500g", "Panaderia", 5300, "5.00", 40),
    ("BED-028", "Queso campesino 400g", "Lacteo fresco", 9900, "5.00", 45),
    ("BED-029", "Mortadela 500g", "Frio", 7800, "5.00", 50),
    ("BED-030", "Avena en hojuelas 500g", "Cereal", 4400, "0.00", 90),
    ("BED-031", "Miel pura 500g", "Endulzante natural", 13800, "0.00", 40),
    ("BED-032", "Quinoa 500g", "Grano andino", 7600, "19.00", 45),
]

c = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur = c.cursor()
for p in PRODUCTOS:
    cur.execute(
        "INSERT IGNORE INTO productos (codigo_referencia,nombre,descripcion,precio,porcentaje_iva,stock)"
        " VALUES (%s,%s,%s,%s,%s,%s)", p
    )
c.commit()
cur.execute("SELECT COUNT(*) FROM productos")
print("productos totales:", cur.fetchone()[0])
c.close()
