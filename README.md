# Cuarto Creciente · Pedidos Streamlit V1

## Ejecutar localmente

1. Instalar Python 3.10 o superior.
2. Abrir una terminal en esta carpeta.
3. Ejecutar `pip install -r requirements.txt`.
4. Ejecutar `streamlit run app.py`.
5. Abrir la dirección local indicada (normalmente http://localhost:8501).

## Primer uso

1. Ir a **Administración** y descargar las plantillas de clientes y artículos.
2. Completar los códigos como texto. `lista` debe decir `Lista 1`, `Lista 2` o `Lista 3`.
3. Importar ambos Excel. Los registros se actualizan por código sin borrar otros registros.
4. Ir a **Nuevo pedido**, seleccionar cliente, ingresar vendedor, cargar artículos y guardar.
5. En **Exportar Excel**, elegir estados y descargar un archivo con detalle, matriz, totales y resumen.

## Notas importantes

- La fecha y hora corresponden a Argentina y se actualizan cuando Streamlit vuelve a ejecutar la página.
- Los porcentajes de Factura común y Factura X son campos administrativos; la aplicación **no emite comprobantes**.
- Un pedido puede tener múltiples artículos. Las cantidades son bultos enteros.
- Los pedidos NO reservan ni descuentan stock. La distribución inteligente se hace después con el Excel exportado.
- Los datos se guardan en `pedidos.db` (SQLite), dentro de esta carpeta. Guardar copias de seguridad.
- **Versión local para pruebas:** no incluye autenticación ni aislamiento de vendedores. No publicarla como multiusuario en Streamlit Cloud tal como está. Para producción se requiere autenticación, roles, auditoría, y una base de datos externa persistente (p. ej. PostgreSQL). El disco de Streamlit Community Cloud no es adecuado para guardar estos pedidos de manera duradera.
- El Excel de exportación incluye una matriz preliminar. Se ajustará cuando se disponga del formato exacto de Distribución Inteligente.
