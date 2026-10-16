# Cuarto Creciente Pedidos — Streamlit V1 con acceso de usuarios

## Archivos para GitHub
Subí `app.py`, `requirements.txt`, `generar_hash.py`, `logo.png` y `.gitignore` a la raíz del repositorio. Si tu logo está en `assets/logo.png`, también funciona. No subas `pedidos.db` ni archivos con contraseñas.

## Crear las contraseñas
En tu computadora, con Python instalado, ejecutá `python generar_hash.py`. Ingresá una contraseña de 12 caracteres o más y copiá el hash generado. Repetí el procedimiento para cada usuario.

## Configurar Streamlit Cloud
Abrí tu app > Manage app > Settings > Secrets. Copiá la estructura de `secrets.ejemplo.toml`, reemplazá cada `PEGAR_HASH_GENERADO_AQUI` por su hash y guardá. **No subas el archivo de secrets con contraseñas a GitHub**. Los usuarios se identifican por las secciones `[users.nombredeusuario]` en minúsculas. Roles permitidos: `admin` y `vendedor`.

## Permisos
- Administrador: carga de pedidos, historial completo, edición, importación de clientes/artículos y exportación Excel.
- Vendedor: carga de pedidos y consulta de sus propios pedidos; el vendedor se toma automáticamente de su sesión.
- Los porcentajes de Factura común y Factura X suman 100%. La app no emite comprobantes fiscales.

## Advertencia sobre almacenamiento
La app actual usa SQLite en un archivo local. En Streamlit Community Cloud **no es confiable para pedidos reales**, porque puede reiniciarse o tener instancias independientes. La autenticación se implementó para comenzar las pruebas; **antes de trabajar con vendedores reales** hay que migrar los datos a PostgreSQL/Supabase, implementar copias de seguridad y probar permisos y concurrencia. No cargues información comercial sensible hasta completar esa etapa.

## Exportación
La exportación incluye detalle, matriz, totales y resumen. El formato exacto para Distribución Inteligente se adaptará cuando compartas un Excel de ejemplo.
