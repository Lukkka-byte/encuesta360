from flask import Flask, render_template, request, redirect, flash, make_response, session, url_for
import sqlite3
import os
from datetime import datetime, timedelta
import statistics
import uuid

app = Flask(__name__)
app.secret_key = 'clave-secreta-para-flash-messages'

DB_FILE = 'respuestas_360.db'

# Crear base de datos si no existe
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS respuestas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                semana INTEGER,
                fecha TEXT,
                p1 INTEGER, p2 INTEGER, p3 INTEGER, p4 INTEGER, p5 INTEGER,
                p6 INTEGER, p7 INTEGER, p8 INTEGER, p9 INTEGER, p10 INTEGER,
                p11 INTEGER, p12 INTEGER, p13 INTEGER,
                comentario TEXT
            )
        ''')
        conn.commit()

init_db()

preguntas_texto = [
    'La comunicación en cocina fue clara y respetuosa.',
    'Los responsables generaron un ambiente positivo y motivador.',
    'Los conflictos fueron gestionados de forma justa y profesional.',
    'Los responsables dieron ejemplo con su actitud y compromiso.',
    'Mostraron interés por el bienestar y desarrollo del equipo.',
    'Los responsables reconocieron el esfuerzo del equipo durante la semana.',
    'Los responsables se mostraron disponibles para resolver dudas o problemas.',
    'Esta semana me sentí motivado/a para dar lo mejor de mí.',
    'Se planificó bien el trabajo antes de los servicios.',
    'La organización y supervisión durante los turnos fue adecuada.',
    'Las instrucciones fueron claras y la coordinación fue eficaz.',
    'Los imprevistos se resolvieron con control y criterio.',
    'Se cumplieron los estándares de calidad y tiempos de salida.'
]

categorias = [
    'Comunicación', 'Clima laboral', 'Conflictos', 'Liderazgo', 'Empatía', 'Reconocimiento',
    'Apoyo', 'Motivación', 'Planificación', 'Supervisión', 'Coordinación', 'Resolución', 'Calidad'
]

@app.route('/')
def index():
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())

    preguntas_a = preguntas_texto[:8]
    preguntas_b = preguntas_texto[8:]

    instrucciones = "Valora del 1 al 5 cada afirmación según lo vivido esta semana, siendo 1 la peor valoración y 5 la mejor."

    resp = make_response(render_template('formulario.html', preguntas_a=preguntas_a, preguntas_b=preguntas_b, instrucciones=instrucciones))
    resp.set_cookie('user_id', user_id, max_age=60*60*24*365)
    return resp

@app.route('/enviar', methods=['POST'])
def enviar():
    user_id = request.cookies.get('user_id')
    fecha_envio = datetime.now().strftime('%Y-%m-%d')

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT fecha FROM respuestas WHERE user_id = ? ORDER BY fecha DESC LIMIT 1", (user_id,))
        fila = cursor.fetchone()

        if fila:
            ultima_fecha = datetime.strptime(fila[0], '%Y-%m-%d')
            if datetime.now() - ultima_fecha < timedelta(days=7):
                flash("Ya has enviado la encuesta en los últimos 7 días. Gracias por tu participación.")
                return redirect('/')

        semana_actual = datetime.now().isocalendar()[1]

        cursor.execute('''
            INSERT INTO respuestas (
                user_id, semana, fecha, p1, p2, p3, p4, p5,
                p6, p7, p8, p9, p10, p11, p12, p13, comentario
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, semana_actual, fecha_envio,
            request.form.get('p1'), request.form.get('p2'), request.form.get('p3'),
            request.form.get('p4'), request.form.get('p5'), request.form.get('p6'),
            request.form.get('p7'), request.form.get('p8'), request.form.get('p9'),
            request.form.get('p10'), request.form.get('p11'), request.form.get('p12'),
            request.form.get('p13'), request.form.get('comentario')
        ))
        conn.commit()

    return render_template('gracias.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'lider360':
            session['admin'] = True
            return redirect('/resultados')
        else:
            flash('Credenciales incorrectas.')
            return redirect('/login')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/resetear', methods=['POST'])
def resetear():
    if not session.get('admin'):
        flash('Debes iniciar sesión como administrador.')
        return redirect('/login')
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM respuestas")
        conn.commit()
    flash("Todos los resultados han sido eliminados correctamente.")
    return redirect('/resultados')

@app.route('/resultados')
def resultados():
    if not session.get('admin'):
        flash('Debes iniciar sesión para acceder a los resultados.')
        return redirect('/login')

    semana_filtrada = request.args.get('semana')
    hoy = datetime.now()
    semana_actual = hoy.isocalendar()[1]

    if semana_filtrada:
        try:
            semana_filtrada = int(semana_filtrada)
        except ValueError:
            semana_filtrada = semana_actual
    else:
        semana_filtrada = semana_actual

    respuestas_detalladas = []
    promedios_semanales = [0] * 13
    total_semanal = 0

    promedios_totales = [0] * 13
    total_global = 0

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fecha, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, comentario
            FROM respuestas
            WHERE semana = ?
            ORDER BY fecha DESC
        """, (semana_filtrada,))
        respuestas_detalladas = cursor.fetchall()

        for fila in respuestas_detalladas:
            for i in range(13):
                promedios_semanales[i] += int(fila[i + 1])
            total_semanal += 1

        cursor.execute("SELECT p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13 FROM respuestas")
        todas = cursor.fetchall()
        for fila in todas:
            for i in range(13):
                promedios_totales[i] += int(fila[i])
            total_global += 1

    if total_semanal > 0:
        promedios_semanales = [round(v / total_semanal, 2) for v in promedios_semanales]
        promedio_general_semanal = round(sum(promedios_semanales) / len(promedios_semanales), 2)
    else:
        promedio_general_semanal = 0

    if total_global > 0:
        promedios_totales = [round(v / total_global, 2) for v in promedios_totales]
        promedio_general_total = round(sum(promedios_totales) / len(promedios_totales), 2)
    else:
        promedio_general_total = 0

    return render_template('resultados.html', categorias=categorias, preguntas=preguntas_texto,
                           respuestas_detalladas=respuestas_detalladas,
                           promedios=promedios_semanales, total=total_semanal,
                           semana=semana_filtrada, promedios_totales=promedios_totales,
                           total_global=total_global,
                           promedio_general_semanal=promedio_general_semanal,
                           promedio_general_total=promedio_general_total)

@app.route('/exportar_csv')
def exportar_csv():
    import csv
    from io import StringIO
    semana = request.args.get('semana', type=int)

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Fecha'] + categorias + ['Comentario'])

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fecha, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, comentario
            FROM respuestas
            WHERE semana = ?
            ORDER BY fecha DESC
        """, (semana,))
        for fila in cursor.fetchall():
            writer.writerow(fila)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=encuesta_semana_{semana}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    app.run(debug=True)
