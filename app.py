import io
import hashlib
import hmac
import base64
import sqlite3
import secrets
import requests
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
DB = BASE / 'pedidos.db'
TZ = ZoneInfo('America/Argentina/Buenos_Aires')

st.set_page_config(page_title='Cuarto Creciente | Pedidos', page_icon='📦', layout='wide')
st.markdown('''<style>.block-container{padding-top:1.1rem;max-width:1250px} [data-testid="stMetric"]{background:#f2f6fa;padding:12px;border-radius:12px} </style>''', unsafe_allow_html=True)
def show_logo():
    for path in (BASE / 'logo.png', BASE / 'assets' / 'logo.png'):
        if path.is_file():
            st.image(str(path), width=480)
            return
    st.title('Cuarto Creciente')


def check_password(password, stored):
    try:
        method, rounds, salt64, hash64 = stored.split('$')
        if method != 'pbkdf2_sha256':
            return False
        derived = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt64), int(rounds))
        return hmac.compare_digest(derived, base64.b64decode(hash64))
    except (ValueError, TypeError):
        return False


def hash_password(password):
    salt = secrets.token_bytes(16)
    rounds = 600000
    derived = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${base64.b64encode(salt).decode()}${base64.b64encode(derived).decode()}"


def remote_config():
    try:
        url = str(st.secrets.get('SUPABASE_URL', '')).rstrip('/')
        key = str(st.secrets.get('SUPABASE_SERVICE_ROLE_KEY', ''))
    except (KeyError, FileNotFoundError):
        return None
    return (url, key) if url.startswith('https://') and key else None


def remote_users(method='GET', username=None, data=None):
    cfg = remote_config()
    if not cfg:
        raise RuntimeError('Falta configurar SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en Streamlit Secrets.')
    url, key = cfg
    endpoint = f'{url}/rest/v1/app_users'
    params = {'select':'username,name,role,active,password_hash'} if method == 'GET' else {}
    if username is not None:
        params['username'] = f'eq.{username}'
    headers = {'apikey':key,'Authorization':f'Bearer {key}', 'Content-Type':'application/json', 'Prefer':'return=minimal'}
    response = requests.request(method, endpoint, params=params, json=data, headers=headers, timeout=12)
    if not response.ok:
        raise RuntimeError(f'No se pudo consultar o actualizar usuarios (HTTP {response.status_code}). Revisá la tabla y los Secrets.')
    return response.json() if method == 'GET' else None


def login():
    if st.session_state.get('authenticated'):
        return True
    # Diseño compacto en dos columnas: imagen a la izquierda, formulario a la derecha.
    st.markdown("""<style>
      .block-container {padding-top: .55rem !important; padding-bottom: .5rem !important; max-width: 1100px !important;}
      [data-testid="stVerticalBlock"] {gap: .55rem;}
      [data-testid="stForm"] {padding: .75rem 1rem; border-radius: 14px;}
      [data-testid="stForm"] [data-testid="stVerticalBlock"] {gap: .45rem;}
      @media (max-width: 767px) {.block-container {padding-top: .35rem !important;}}
    </style>""", unsafe_allow_html=True)
    left, right = st.columns([1.12, 1], gap='large', vertical_alignment='center')
    with left:
        imagen_ingreso = BASE / 'imagen_ingreso.jpg'
        if imagen_ingreso.is_file():
            st.image(str(imagen_ingreso), use_container_width=True)
    with right:
        logo = BASE / 'logo.png'
        if not logo.is_file():
            logo = BASE / 'assets' / 'logo.png'
        if logo.is_file():
            st.image(str(logo), width=340)
        else:
            st.title('Cuarto Creciente')
        st.subheader('Acceso al sistema de pedidos')
        st.caption('Ingresá con tu usuario y contraseña')
        st.caption(datetime.now(TZ).strftime('Fecha: %d/%m/%Y · Hora: %H:%M (Argentina)'))
        try:
            users = st.secrets['users']
        except (KeyError, FileNotFoundError):
            st.error('Falta configurar los usuarios en los Secrets de Streamlit Cloud. Consultá el README.')
            return False
        with st.form('login_form'):
            username = st.text_input('Usuario').strip().lower()
            password = st.text_input('Contraseña', type='password')
            submitted = st.form_submit_button('Ingresar', use_container_width=True, type='primary')
        if submitted:
            user = None
            if remote_config():
                try:
                    found = remote_users(username=username)
                    if found:
                        user = found[0] if found[0].get('active') else None
                except RuntimeError as exc:
                    st.error(str(exc))
                    return False
            if user is None and username == 'admin':
                user = users.get('admin')
            if user and check_password(password, user.get('password_hash', '')) and user.get('role') in ('admin', 'vendedor'):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = user['role']
                st.session_state.display_name = user.get('name', username)
                st.rerun()
            else:
                st.error('Usuario o contraseña incorrectos.')
    return False


if not login():
    st.stop()

show_logo()
st.caption('Sistema de pedidos · Cuarto Creciente S.A.')
with st.sidebar:
    st.write(f"**{st.session_state.display_name}**")
    st.caption('Administrador' if st.session_state.role == 'admin' else 'Vendedor')
    if st.button('Cerrar sesión'):
        st.session_state.clear()
        st.rerun()


def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA journal_mode=WAL')
    return con


def init_db():
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS clientes (codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, lista TEXT NOT NULL DEFAULT 'Lista 1');
        CREATE TABLE IF NOT EXISTS articulos (codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, precio_1 REAL NOT NULL DEFAULT 0, precio_2 REAL NOT NULL DEFAULT 0, precio_3 REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, cliente_codigo TEXT NOT NULL, cliente_nombre TEXT NOT NULL, lista TEXT NOT NULL, vendedor TEXT NOT NULL, pct_comun REAL NOT NULL, pct_x REAL NOT NULL, estado TEXT NOT NULL DEFAULT 'Pendiente');
        CREATE TABLE IF NOT EXISTS renglones (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER NOT NULL REFERENCES pedidos(id), articulo_codigo TEXT NOT NULL, articulo_nombre TEXT NOT NULL, cantidad INTEGER NOT NULL, precio REAL NOT NULL);
        ''')


def query(sql, params=()):
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def excel_bytes(sheets):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions
            from openpyxl.styles import Font, PatternFill
            for cell in ws[1]:
                cell.fill = PatternFill('solid', fgColor='214A70')
                cell.font = Font(color='FFFFFF', bold=True)
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max((len(str(c.value or '')) for c in list(col)[:300]), default=10)
                ws.column_dimensions[letter].width = min(max(14, max_len + 3), 44)
    return buf.getvalue()


def read_upload(file):
    if file.name.lower().endswith('.csv'):
        try:
            return pd.read_csv(file, dtype=str, sep=None, engine='python').fillna('')
        except UnicodeDecodeError:
            file.seek(0)
            return pd.read_csv(file, dtype=str, sep=None, engine='python', encoding='latin1').fillna('')
    return pd.read_excel(file, dtype=str).fillna('')


def import_catalog(kind, file):
    df = read_upload(file)
    df.columns = [str(x).strip().lower() for x in df.columns]
    required = ['codigo', 'nombre']
    if not set(required).issubset(df.columns):
        raise ValueError('Se necesitan columnas llamadas codigo y nombre.')
    if kind == 'clientes':
        if 'lista' not in df: df['lista'] = 'Lista 1'
        df['lista'] = df['lista'].replace('', 'Lista 1')
        if not df['lista'].isin(['Lista 1','Lista 2','Lista 3']).all():
            raise ValueError('La columna lista debe ser Lista 1, Lista 2 o Lista 3.')
        cols = ['codigo','nombre','lista']
    else:
        for col in ['precio_1','precio_2','precio_3']:
            if col not in df: df[col] = '0'
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',','.', regex=False), errors='raise').fillna(0)
            if (df[col] < 0).any(): raise ValueError('Los precios no pueden ser negativos.')
        cols = ['codigo','nombre','precio_1','precio_2','precio_3']
    df = df[cols].copy()
    df['codigo'] = df['codigo'].astype(str).str.strip()
    df['nombre'] = df['nombre'].astype(str).str.strip()
    if (df['codigo']=='').any() or (df['nombre']=='').any() or df['codigo'].duplicated().any():
        raise ValueError('Hay códigos duplicados, códigos vacíos o nombres vacíos.')
    with connect() as con:
        for row in df.itertuples(index=False, name=None):
            marks = ','.join('?' for _ in cols)
            updates = ','.join(f'{c}=excluded.{c}' for c in cols if c!='codigo')
            con.execute(f'INSERT INTO {kind} ({",".join(cols)}) VALUES ({marks}) ON CONFLICT(codigo) DO UPDATE SET {updates}', row)
    return len(df)

init_db()
now = datetime.now(TZ)
st.caption(f'Fecha y hora (Argentina): {now:%d/%m/%Y %H:%M:%S} · Se actualiza al interactuar o recargar la página')
page = st.sidebar.radio('Menú', ['Nuevo pedido','Pedidos guardados','Exportar Excel','Administración','Usuarios'] if st.session_state.role == 'admin' else ['Nuevo pedido','Mis pedidos'])

if page == 'Nuevo pedido':
    st.header('Nuevo pedido')
    clientes = query('SELECT * FROM clientes ORDER BY nombre')
    articulos = query('SELECT * FROM articulos ORDER BY nombre')
    if clientes.empty or articulos.empty:
        st.warning('Primero importá los clientes y artículos desde Administración. No se cargaron datos ficticios.')
    else:
        lookup_c = {r.codigo: r for r in clientes.itertuples(index=False)}
        lookup_a = {r.codigo: r for r in articulos.itertuples(index=False)}
        c1,c2 = st.columns([2,1])
        with c1:
            cliente = st.selectbox('Cliente: escribí código o nombre', clientes['codigo'].tolist(), format_func=lambda c: f'{c} · {lookup_c[c].nombre}')
        with c2:
            vendedor = st.session_state.username
            st.text_input('Vendedor', value=st.session_state.display_name, disabled=True)
        c = lookup_c[cliente]
        lista = c.lista
        st.info(f'Cliente: {c.nombre} · Código: {cliente} · Lista asignada: {lista}')
        st.subheader('Facturación')
        if 'pct_comun' not in st.session_state: st.session_state.pct_comun = 100.0
        if 'pct_x' not in st.session_state: st.session_state.pct_x = 0.0
        def update_comun():
            v = st.session_state.pct_comun
            if 0 <= v <= 100: st.session_state.pct_x = round(100-v,2)
        def update_x():
            v = st.session_state.pct_x
            if 0 <= v <= 100: st.session_state.pct_comun = round(100-v,2)
        a,b = st.columns(2)
        a.number_input('Factura común (%)', min_value=0.0, max_value=100.0, step=5.0, key='pct_comun', on_change=update_comun)
        b.number_input('Factura X (%)', min_value=0.0, max_value=100.0, step=5.0, key='pct_x', on_change=update_x)
        st.caption('Ambos porcentajes se guardan como información administrativa. No se generan comprobantes fiscales.')
        st.subheader('Artículos')
        pcol,qcol = st.columns([3,1])
        with pcol:
            articulo = st.selectbox('Código o nombre del artículo', articulos['codigo'].tolist(), format_func=lambda k: f'{k} · {lookup_a[k].nombre}')
        with qcol:
            cantidad = st.number_input('Bultos', min_value=1, step=1, value=1)
        art = lookup_a[articulo]
        precio = float(getattr(art, 'precio_'+lista[-1]))
        st.caption(f'Precio por bulto ({lista}): $ {precio:,.2f}')
        if 'carrito' not in st.session_state: st.session_state.carrito = {}
        if st.button('➕ Agregar artículo', type='secondary'):
            st.session_state.carrito[articulo] = st.session_state.carrito.get(articulo,0) + int(cantidad)
            st.rerun()
        rows = []
        for code, qty in st.session_state.carrito.items():
            if code in lookup_a:
                item = lookup_a[code]
                price = float(getattr(item,'precio_'+lista[-1]))
                rows.append({'Código artículo':code,'Artículo':item.nombre,'Bultos':qty,'Precio/bulto':price,'Importe':qty*price})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.metric('Total bultos', sum(r['Bultos'] for r in rows))
            st.metric('Importe total', f"$ {sum(r['Importe'] for r in rows):,.2f}")
            to_remove = st.selectbox('Quitar artículo', ['—']+[r['Código artículo'] for r in rows])
            if st.button('Quitar seleccionado', disabled=to_remove=='—'):
                st.session_state.carrito.pop(to_remove,None)
                st.rerun()
        else: st.caption('Agregá artículos para armar el pedido.')
        if st.button('💾 Guardar pedido', type='primary', disabled=not rows):
            if not vendedor.strip(): st.error('Indicá el vendedor.')
            elif round(st.session_state.pct_comun+st.session_state.pct_x,2)!=100:
                st.error('Los porcentajes deben sumar 100%.')
            else:
                with connect() as con:
                    cur=con.execute('INSERT INTO pedidos (fecha,cliente_codigo,cliente_nombre,lista,vendedor,pct_comun,pct_x) VALUES (?,?,?,?,?,?,?)', (datetime.now(TZ).isoformat(timespec='seconds'),cliente,c.nombre,lista,vendedor.strip(),st.session_state.pct_comun,st.session_state.pct_x))
                    pid=cur.lastrowid
                    con.executemany('INSERT INTO renglones (pedido_id,articulo_codigo,articulo_nombre,cantidad,precio) VALUES (?,?,?,?,?)', [(pid,r['Código artículo'],r['Artículo'],r['Bultos'],r['Precio/bulto']) for r in rows])
                st.session_state.carrito={}
                st.success(f'Pedido #{pid} guardado correctamente.')
                st.caption('No se descuenta stock: la asignación se realizará en Distribución Inteligente.')

elif page in ('Pedidos guardados', 'Mis pedidos'):
    st.header('Pedidos guardados')
    pedidos=query('SELECT p.id,p.fecha,p.cliente_codigo,p.cliente_nombre,p.lista,p.vendedor,p.pct_comun,p.pct_x,p.estado,COALESCE(SUM(r.cantidad),0) AS bultos FROM pedidos p LEFT JOIN renglones r ON r.pedido_id=p.id WHERE (? = \'admin\' OR p.vendedor = ?) GROUP BY p.id ORDER BY p.id DESC', (st.session_state.role, st.session_state.username))
    st.dataframe(pedidos, use_container_width=True, hide_index=True)
    if not pedidos.empty:
        pid=st.selectbox('Ver o editar pedido', pedidos['id'].tolist())
        detalle=query('SELECT articulo_codigo,articulo_nombre,cantidad,precio FROM renglones WHERE pedido_id=?',(int(pid),))
        st.dataframe(detalle, hide_index=True, use_container_width=True)
        if st.session_state.role == 'admin':
          with st.expander('Editar cantidades / estado'):
            cambios={}
            for r in detalle.itertuples(index=False):
                cambios[r.articulo_codigo]=st.number_input(f'{r.articulo_codigo} · {r.articulo_nombre}',min_value=0,value=int(r.cantidad),step=1,key=f'edit_{pid}_{r.articulo_codigo}')
            estado_actual=pedidos.loc[pedidos['id']==pid,'estado'].iloc[0]
            estados=['Pendiente','Revisado','Exportado','Cancelado']
            estado=st.selectbox('Estado',estados,index=estados.index(estado_actual) if estado_actual in estados else 0)
            if st.button('Guardar cambios'):
                with connect() as con:
                    for code,qty in cambios.items():
                        if qty==0: con.execute('DELETE FROM renglones WHERE pedido_id=? AND articulo_codigo=?',(int(pid),code))
                        else: con.execute('UPDATE renglones SET cantidad=? WHERE pedido_id=? AND articulo_codigo=?',(int(qty),int(pid),code))
                    con.execute('UPDATE pedidos SET estado=? WHERE id=?',(estado,int(pid)))
                st.success('Pedido actualizado.')
                st.rerun()

elif page == 'Exportar Excel':
    st.header('Exportación para Distribución Inteligente')
    st.caption('Se exporta la demanda total, sin separar los artículos por tipo de facturación.')
    df=query('''SELECT p.id AS pedido,p.fecha,p.cliente_codigo,p.cliente_nombre,p.lista,p.vendedor,p.pct_comun,p.pct_x,p.estado,r.articulo_codigo,r.articulo_nombre,r.cantidad AS bultos,r.precio,(r.cantidad*r.precio) AS importe FROM pedidos p JOIN renglones r ON p.id=r.pedido_id ORDER BY p.id,r.articulo_codigo''')
    if df.empty: st.info('No hay pedidos para exportar todavía.')
    else:
        estados=st.multiselect('Estados incluidos',sorted(df.estado.unique()),default=['Pendiente','Revisado'])
        dff=df[df.estado.isin(estados)].copy()
        if dff.empty: st.warning('No hay renglones con los estados seleccionados.')
        else:
            matriz=dff.pivot_table(index=['cliente_codigo','cliente_nombre'],columns='articulo_codigo',values='bultos',aggfunc='sum',fill_value=0).reset_index()
            matriz.columns.name=None
            totales=dff.groupby(['articulo_codigo','articulo_nombre'],as_index=False)['bultos'].sum()
            resumen=dff.groupby(['cliente_codigo','cliente_nombre'],as_index=False).agg(bultos=('bultos','sum'),importe=('importe','sum'))
            st.dataframe(dff,use_container_width=True,hide_index=True)
            data=excel_bytes({'Detalle pedidos':dff,'Matriz distribucion':matriz,'Totales articulos':totales,'Resumen clientes':resumen})
            st.download_button('⬇️ Descargar Excel de pedidos',data=data,file_name=f'pedidos_cuarto_creciente_{datetime.now(TZ):%Y%m%d_%H%M}.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary')
            st.warning('La estructura definitiva de la matriz se ajustará al archivo real que utiliza Distribución Inteligente.')

elif page == 'Usuarios':
    st.header('Administración de usuarios')
    st.caption('Solo administradores pueden crear, desactivar y cambiar contraseñas de vendedores.')
    if not remote_config():
        st.warning('Para activar esta sección primero hay que conectar una base compartida. Seguí las instrucciones de INSTALACION_USUARIOS.md. El administrador actual sigue entrando por Secrets.')
    else:
        try:
            registered = remote_users()
            st.dataframe(pd.DataFrame([{'Usuario':u['username'],'Nombre':u['name'],'Rol':u['role'],'Activo':u['active']} for u in registered]), hide_index=True, use_container_width=True)
            with st.form('create_user', clear_on_submit=True):
                st.subheader('Crear vendedor')
                new_name = st.text_input('Nombre y apellido')
                new_username = st.text_input('Usuario (sin espacios)')
                new_password = st.text_input('Contraseña inicial', type='password')
                create = st.form_submit_button('Crear vendedor', type='primary')
            if create:
                un = new_username.strip().lower()
                if not un or not un.replace('_','').isalnum() or not new_name.strip():
                    st.error('Completá nombre y usuario. Usá letras, números o guion bajo.')
                elif len(new_password) < 12:
                    st.error('La contraseña debe tener al menos 12 caracteres.')
                elif any(u['username'] == un for u in registered) or un == 'admin':
                    st.error('Ese usuario ya existe.')
                else:
                    remote_users('POST', data={'username':un,'name':new_name.strip(),'role':'vendedor','active':True,'password_hash':hash_password(new_password)})
                    st.success('Vendedor creado. Ya puede ingresar desde la pantalla principal.')
                    st.rerun()
            st.divider()
            sellers = [u for u in registered if u['role'] == 'vendedor']
            if sellers:
                chosen = st.selectbox('Administrar vendedor', [u['username'] for u in sellers])
                current = next(u for u in sellers if u['username'] == chosen)
                if st.button('Desactivar usuario' if current['active'] else 'Reactivar usuario'):
                    remote_users('PATCH', chosen, {'active':not current['active']})
                    st.rerun()
                with st.form('reset_password'):
                    new_pass = st.text_input('Nueva contraseña para este vendedor',type='password')
                    change = st.form_submit_button('Cambiar contraseña')
                if change:
                    if len(new_pass)<12:
                        st.error('La contraseña debe tener al menos 12 caracteres.')
                    else:
                        remote_users('PATCH', chosen, {'password_hash':hash_password(new_pass)})
                        st.success('Contraseña actualizada.')
        except RuntimeError as exc:
            st.error(str(exc))

else:
    st.header('Administración de catálogos')
    st.warning('Acceso restringido a administradores. SQLite local NO es almacenamiento persistente para Streamlit Community Cloud: usar PostgreSQL antes de operar con pedidos reales.')
    for kind, title, cols in [('clientes','Clientes',['codigo','nombre','lista']),('articulos','Artículos',['codigo','nombre','precio_1','precio_2','precio_3'])]:
        st.subheader(title)
        current=query(f'SELECT * FROM {kind} ORDER BY codigo')
        st.dataframe(current,use_container_width=True,hide_index=True)
        example=pd.DataFrame(columns=cols)
        st.download_button(f'Descargar plantilla de {kind}',excel_bytes({title:example}),file_name=f'plantilla_{kind}.xlsx',key=f'template_{kind}')
        file=st.file_uploader(f'Importar {title.lower()} (Excel o CSV)',type=['xlsx','csv'],key=f'upload_{kind}')
        if file and st.button(f'Importar {title.lower()}',key=f'btn_{kind}'):
            try:
                n=import_catalog(kind,file)
                st.success(f'{n} registros importados o actualizados.')
                st.rerun()
            except Exception as e:
                st.error(f'No se pudo importar: {e}')
    st.divider()
    st.subheader('Copia de seguridad')
    st.download_button('Descargar base de datos SQLite',data=DB.read_bytes(),file_name='pedidos_backup.db',mime='application/octet-stream')
    st.caption('Los códigos deben conservarse como texto para no perder ceros iniciales. Importar actualiza registros existentes por código sin borrar los demás.')
