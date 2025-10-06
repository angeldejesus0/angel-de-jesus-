from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)
# Es VITAL configurar SECRET_KEY como una variable de entorno en Render para seguridad.
app.secret_key = os.environ.get('SECRET_KEY', 'tu_clave_secreta_aqui_para_seguridad')  # Cambia por una segura

# --- CONEXIÓN A MONGODB CORREGIDA PARA RENDER ---
# NOTA: NO USES CÓDIGOS REALES CON CREDENCIALES EN EL CÓDIGO FUENTE (GitHub).
# Esta línea usa la variable de entorno MONGO_URI, que DEBES configurar en Render.
# Si la variable no existe, usará la URL de desarrollo local (como fallback).
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/') 

try:
    # La conexión usará la URL que configures en Render (tu URI de Atlas)
    client = MongoClient(MONGO_URI)
    db = client['abigail0'] # El nombre de tu BD es 'abigail0' según la URI
    
    # Definición de Colecciones
    usuarios_collection = db['usuarios']
    comentarios_collection = db['comentarios']
    contactos_collection = db['contactos']
    views_collection = db['views']
    print("Conexión a MongoDB Atlas establecida con éxito.")
except Exception as e:
    print(f"ERROR: No se pudo conectar a MongoDB. Asegúrate de que la variable MONGO_URI esté configurada. Detalles: {e}")
    # Si la conexión falla, las variables de colección se inicializan como None para evitar errores.
    client, db = None, None
    usuarios_collection, comentarios_collection, contactos_collection, views_collection = None, None, None, None


# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    """Sirve la página de inicio y muestra el modal si es necesario."""
    user_count = 0
    try:
        if usuarios_collection:
            user_count = usuarios_collection.count_documents({'accepted_terms': True})
    except Exception:
        pass 
        
    if 'terms_accepted' not in session or not session['terms_accepted']:
        return render_template('index.html', show_modal=True, user_count=user_count)
    return render_template('index.html', show_modal=False, user_count=user_count)

@app.route('/accept_terms', methods=['POST'])
def accept_terms():
    """Procesa la aceptación de los términos y guarda la IP."""
    ip_address = request.remote_addr
    try:
        if usuarios_collection:
            usuarios_collection.update_one(
                {'ip_address': ip_address},
                {
                    '$set': {
                        'ip_address': ip_address,
                        'accepted_terms': True,
                        'timestamp': datetime.now()
                    }
                },
                upsert=True
            )
        session['terms_accepted'] = True
    except Exception as e:
        print(f"Error al guardar aceptación de términos: {e}")
        session['terms_accepted'] = True # Asume éxito en sesión aunque falle la BD
        
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.pop('terms_accepted', None)
    return redirect(url_for('index'))

@app.route('/get_comments/<article_id>')
def get_comments(article_id):
    """Obtiene los comentarios de un artículo específico."""
    try:
        if comentarios_collection:
            comments = comentarios_collection.find({'article_id': article_id}).sort('timestamp', -1)
            comments_list = [
                {
                    'username': comment['username'],
                    'comment_text': comment['comment_text'],
                    'timestamp': comment['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                }
                for comment in comments
            ]
            return jsonify(comments_list)
        return jsonify({'status': 'error', 'message': 'Base de datos no disponible'}), 503
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/post_comment', methods=['POST'])
def post_comment():
    """Procesa el formulario de comentarios y guarda el comentario."""
    article_id = request.form.get('article_id')
    username = request.form.get('username')
    comment_text = request.form.get('comment_text')
    
    if not article_id or not username or not comment_text:
        return jsonify({'status': 'error', 'message': 'Campos requeridos faltantes'}), 400

    try:
        if comentarios_collection:
            comentarios_collection.insert_one({
                'article_id': article_id,
                'username': username,
                'comment_text': comment_text,
                'timestamp': datetime.now()
            })
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Base de datos no disponible'}), 503
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/send_contact', methods=['POST'])
def send_contact():
    """Procesa el formulario de contacto y guarda los datos."""
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    if not name or not email or not message:
        return jsonify({'status': 'error', 'message': 'Campos requeridos faltantes'}), 400

    try:
        if contactos_collection:
            contactos_collection.insert_one({
                'name': name,
                'email': email,
                'message': message,
                'timestamp': datetime.now()
            })
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Base de datos no disponible'}), 503
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/increment_view_count/<article_id>', methods=['POST'])
def increment_view_count(article_id):
    """Incrementa el contador de visitas para un artículo."""
    try:
        if views_collection:
            views_collection.update_one(
                {'article_id': article_id},
                {'$inc': {'count': 1}},
                upsert=True
            )
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Base de datos no disponible'}), 503
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_view_count/<article_id>')
def get_view_count(article_id):
    """Obtiene el contador de visitas para un artículo."""
    try:
        count = 0
        if views_collection:
            view = views_collection.find_one({'article_id': article_id})
            count = view['count'] if view and 'count' in view else 0
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)