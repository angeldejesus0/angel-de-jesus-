from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tu_clave_secreta_aqui_para_seguridad')  # Usa env var en Render

# Conexión a MongoDB (local o externa via env var)
mongo_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client['proyecto']
usuarios_collection = db['usuarios']
comentarios_collection = db['comentarios']
contactos_collection = db['contactos']
views_collection = db['views']

@app.route('/')
def index():
    """Sirve la página de inicio y muestra el modal si es necesario."""
    user_count = usuarios_collection.count_documents({'accepted_terms': True})
    if 'terms_accepted' not in session or not session['terms_accepted']:
        return render_template('index.html', show_modal=True, user_count=user_count)
    return render_template('index.html', show_modal=False, user_count=user_count)

@app.route('/accept_terms', methods=['POST'])
def accept_terms():
    """Procesa la aceptación de los términos y guarda la IP."""
    ip_address = request.remote_addr
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
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.pop('terms_accepted', None)
    return redirect(url_for('index'))

@app.route('/get_comments/<article_id>')
def get_comments(article_id):
    """Obtiene los comentarios de un artículo específico."""
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

@app.route('/post_comment', methods=['POST'])
def post_comment():
    """Procesa el formulario de comentarios y guarda el comentario."""
    article_id = request.form.get('article_id')
    username = request.form.get('username')
    comment_text = request.form.get('comment_text')
    
    if not article_id or not username or not comment_text:
        return jsonify({'status': 'error', 'message': 'Campos requeridos faltantes'}), 400

    try:
        comentarios_collection.insert_one({
            'article_id': article_id,
            'username': username,
            'comment_text': comment_text,
            'timestamp': datetime.now()
        })
        return jsonify({'status': 'success'})
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
        contactos_collection.insert_one({
            'name': name,
            'email': email,
            'message': message,
            'timestamp': datetime.now()
        })
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/increment_view_count/<article_id>', methods=['POST'])
def increment_view_count(article_id):
    """Incrementa el contador de visitas para un artículo."""
    try:
        views_collection.update_one(
            {'article_id': article_id},
            {'$inc': {'count': 1}},
            upsert=True
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_view_count/<article_id>')
def get_view_count(article_id):
    """Obtiene el contador de visitas para un artículo."""
    view = views_collection.find_one({'article_id': article_id})
    count = view['count'] if view and 'count' in view else 0
    return jsonify({'count': count})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False para producción en Render