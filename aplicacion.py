from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import csv
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  

db_config = {
    'user': 'root',
    'password': '',  
    'host': 'localhost',
    'database': 'practicantes_db'
}

# Crear directorio para CSVs 
if not os.path.exists('data'):
    os.makedirs('data')

def get_db_connection():
    return mysql.connector.connect(**db_config)

# Exportar datos a CSV
def export_to_csv(table, filename):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    with open(f'data/{filename}', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if table == 'practicantes':
            writer.writerow(['id', 'nombre', 'programa', 'fecha_inicio', 'estado', 'responsable'])
        elif table == 'avances':
            writer.writerow(['id', 'practicante_id', 'descripcion', 'fecha', 'retroalimentacion'])
        writer.writerows(rows)
    cursor.close()
    conn.close()

# Creación detablas
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre_usuario VARCHAR(50) UNIQUE,
            contrasena VARCHAR(50),
            rol VARCHAR(20)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS practicantes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100),
            programa VARCHAR(100),
            fecha_inicio DATE,
            estado VARCHAR(20),
            responsable VARCHAR(100)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS avances (
            id INT AUTO_INCREMENT PRIMARY KEY,
            practicante_id INT,
            descripcion TEXT,
            fecha DATE,
            retroalimentacion TEXT,
            FOREIGN KEY (practicante_id) REFERENCES practicantes(id)
        )
    ''')
    # Crear usuario admin por defecto
    cursor.execute("INSERT IGNORE INTO usuarios (nombre_usuario, contrasena, rol) VALUES (%s, %s, %s)", 
                   ('admin', 'admin123', 'supervisor'))
    conn.commit()
    cursor.close()
    conn.close()

# Ruta principal
@app.route('/')
def inicio():
    if 'nombre_usuario' in session:
        return redirect(url_for('listar_practicantes'))
    return redirect(url_for('iniciar_sesion'))

# Iniciar sesión
@app.route('/iniciar_sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        contrasena = request.form['contrasena']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE nombre_usuario = %s AND contrasena = %s", (nombre_usuario, contrasena))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        if usuario:
            session['nombre_usuario'] = nombre_usuario
            session['rol'] = usuario[3]  # Rol: practicante o supervisor
            return redirect(url_for('listar_practicantes'))
        flash('Usuario o contraseña incorrectos')
    return render_template('iniciar_sesion.html')

# Cerrar sesión
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.pop('nombre_usuario', None)
    session.pop('rol', None)
    return redirect(url_for('iniciar_sesion'))

# Registro de practicantes
@app.route('/registrar_practicante', methods=['GET', 'POST'])
def registrar_practicante():
    if 'nombre_usuario' not in session or session['rol'] != 'supervisor':
        flash('Acceso denegado. Solo supervisores pueden registrar practicantes.')
        return redirect(url_for('iniciar_sesion'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        programa = request.form['programa']
        fecha_inicio = request.form['fecha_inicio']
        estado = request.form['estado']
        responsable = request.form['responsable']
        nombre_usuario = request.form['nombre_usuario']
        contrasena = request.form['contrasena']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO practicantes (nombre, programa, fecha_inicio, estado, responsable)
            VALUES (%s, %s, %s, %s, %s)
        ''', (nombre, programa, fecha_inicio, estado, responsable))
        practicante_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO usuarios (nombre_usuario, contrasena, rol) VALUES (%s, %s, %s)
        ''', (nombre_usuario, contrasena, 'practicante'))
        conn.commit()
        cursor.close()
        conn.close()
        export_to_csv('practicantes', 'practicantes.csv')
        flash('Practicante registrado exitosamente')
        return redirect(url_for('listar_practicantes'))
    return render_template('registrar_practicante.html')

# Listado de practicantes
@app.route('/practicantes')
def listar_practicantes():
    if 'nombre_usuario' not in session:
        return redirect(url_for('iniciar_sesion'))
    estado_filtro = request.args.get('estado', 'todos')
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM practicantes"
    if estado_filtro != 'todos':
        query += " WHERE estado = %s"
        cursor.execute(query, (estado_filtro,))
    else:
        cursor.execute(query)
    practicantes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('listar_practicantes.html', practicantes=practicantes, estado_filtro=estado_filtro)

# Actualizar practicante
@app.route('/actualizar_practicante/<int:id>', methods=['GET', 'POST'])
def actualizar_practicante(id):
    if 'nombre_usuario' not in session or session['rol'] != 'supervisor':
        flash('Acceso denegado. Solo supervisores pueden actualizar practicantes.')
        return redirect(url_for('iniciar_sesion'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        programa = request.form['programa']
        fecha_inicio = request.form['fecha_inicio']
        estado = request.form['estado']
        responsable = request.form['responsable']
        cursor.execute('''
            UPDATE practicantes SET nombre=%s, programa=%s, fecha_inicio=%s, estado=%s, responsable=%s
            WHERE id=%s
        ''', (nombre, programa, fecha_inicio, estado, responsable, id))
        conn.commit()
        export_to_csv('practicantes', 'practicantes.csv')
        flash('Practicante actualizado exitosamente')
        return redirect(url_for('listar_practicantes'))
    cursor.execute("SELECT * FROM practicantes WHERE id = %s", (id,))
    practicante = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('registrar_practicante.html', practicante=practicante)

# Eliminar practicante
@app.route('/eliminar_practicante/<int:id>')
def eliminar_practicante(id):
    if 'nombre_usuario' not in session or session['rol'] != 'supervisor':
        flash('Acceso denegado. Solo supervisores pueden eliminar practicantes.')
        return redirect(url_for('iniciar_sesion'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM avances WHERE practicante_id = %s", (id,))
    cursor.execute("DELETE FROM practicantes WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    export_to_csv('practicantes', 'practicantes.csv')
    export_to_csv('avances', 'avances.csv')
    flash('Practicante eliminado exitosamente')
    return redirect(url_for('listar_practicantes'))

# Registro de avances
@app.route('/agregar_avance/<int:practicante_id>', methods=['GET', 'POST'])
def agregar_avance(practicante_id):
    if 'nombre_usuario' not in session:
        return redirect(url_for('iniciar_sesion'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM practicantes WHERE id = %s", (practicante_id,))
    practicante = cursor.fetchone()
    if request.method == 'POST':
        descripcion = request.form['descripcion']
        fecha = request.form['fecha']
        retroalimentacion = request.form.get('retroalimentacion', '') if session['rol'] == 'supervisor' else ''
        cursor.execute('''
            INSERT INTO avances (practicante_id, descripcion, fecha, retroalimentacion)
            VALUES (%s, %s, %s, %s)
        ''', (practicante_id, descripcion, fecha, retroalimentacion))
        conn.commit()
        export_to_csv('avances', 'avances.csv')
        flash('Avance registrado exitosamente')
        return redirect(url_for('ver_avances', practicante_id=practicante_id))
    cursor.close()
    conn.close()
    return render_template('agregar_avance.html', practicante=practicante)

# Ver avances
@app.route('/ver_avances/<int:practicante_id>')
def ver_avances(practicante_id):
    if 'nombre_usuario' not in session:
        return redirect(url_for('iniciar_sesion'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM practicantes WHERE id = %s", (practicante_id,))
    practicante = cursor.fetchone()
    cursor.execute("SELECT * FROM avances WHERE practicante_id = %s", (practicante_id,))
    avances = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('ver_avances.html', practicante=practicante, avances=avances)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)