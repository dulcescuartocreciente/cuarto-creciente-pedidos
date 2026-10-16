"""Ejecutar localmente: python generar_hash.py. No subir contraseñas a GitHub."""
import base64
import getpass
import hashlib
import os

password = getpass.getpass('Contraseña para generar hash: ')
if len(password) < 12:
    raise SystemExit('Usá al menos 12 caracteres.')
salt = os.urandom(16)
rounds = 600000
digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, rounds)
print('pbkdf2_sha256$%d$%s$%s' % (rounds, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()))
