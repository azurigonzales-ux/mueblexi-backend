from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader
import os

# --- CONFIGURACIÓN CLOUDINARY ---
cloudinary.config( 
    cloud_name = "dftittnxn", 
    api_key = "163411321849394", 
    api_secret = "C0qDZyEs-zZkfn8733vMaWdcrVg" 
)

app = Flask(__name__)
CORS(app) 

# --- CONEXIÓN A MONGO ATLAS ---
# Raúl, recuerda que MONGO_URI es la llave de tu base de datos
MONGO_URI = 'mongodb+srv://admin_mueblexi:RAUL123@cluster0.lqodd.mongodb.net/mueblexi_db?retryWrites=true&w=majority&appName=Cluster0'

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping') 
    print(">>> [CONEXIÓN EXITOSA CON MUEBLEXI_DB] <<<")
    
    db = client['mueblexi_db']
    usuarios = db['usuarios']
    productos = db['productos'] 
    abonos = db['abonos'] 
    
except Exception as e:
    print(f">>> [ERROR CRÍTICO DE CONEXIÓN]: {str(e)} <<<")

# --- 1. SEGURIDAD: LOGIN Y REGISTRO ---

@app.route('/api/login', methods=['POST'])
def login():
    try:
        datos = request.get_json(force=True)
        usuario_recibido = datos.get('username') 
        password_recibida = datos.get('password')
        usuario_encontrado = usuarios.find_one({"username": usuario_recibido})
        
        if not usuario_encontrado:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        if check_password_hash(usuario_encontrado['password'], password_recibida):
            return jsonify({
                "status": "ok", 
                "rol": usuario_encontrado.get('rol', 'cliente'),
                "username": usuario_encontrado.get('username')
            }), 200
        else:
            return jsonify({"error": "Contraseña incorrecta"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register():
    try:
        datos = request.get_json(force=True)
        nombre = datos.get('nombre') 
        username = datos.get('username')
        password = datos.get('password')
        rol = datos.get('rol', 'cliente') 
        
        if usuarios.find_one({"username": username}):
            return jsonify({"error": "El nombre de usuario ya existe"}), 400

        password_encriptada = generate_password_hash(password)
        usuarios.insert_one({
            "nombre": nombre, 
            "username": username,
            "password": password_encriptada,
            "rol": rol
        })
        return jsonify({"mensaje": "Cuenta de Mueblexi creada"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 2. GESTIÓN DE PRODUCTOS ---

@app.route('/api/productos', methods=['POST'])
def agregar_producto():
    try:
        nombre = request.form.get('nombre')
        precio_raw = request.form.get('precio') or request.form.get('precio_total')
        descripcion = request.form.get('descripcion')
        categoria = request.form.get('categoria') or 'General'
        username_cliente = request.form.get('username_cliente') or 'Sin asignar'

        if 'imagen' not in request.files:
            return jsonify({"error": "Falta la imagen del mueble"}), 400
            
        imagen_archivo = request.files['imagen']
        resultado_subida = cloudinary.uploader.upload(
            imagen_archivo, 
            resource_type="auto",
            folder="muebles_proyecto"
        )
        url_imagen = resultado_subida['secure_url']
        
        nuevo_producto = {
            "nombre": nombre,
            "precio_total": float(precio_raw) if precio_raw else 0.0,
            "descripcion": descripcion,
            "categoria": categoria,
            "username_cliente": username_cliente,
            "imagen": url_imagen,
            "vendedor": "Admin_Mueblexi"
        }
        db.productos.insert_one(nuevo_producto)
        return jsonify({"status": "ok", "mensaje": "¡Mueble guardado!", "url": url_imagen}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos', methods=['GET'])
def obtener_catalogo():
    try:
        lista = list(db.productos.find({}, {"_id": 0}))
        return jsonify(lista), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos/<nombre>', methods=['DELETE'])
def eliminar_producto(nombre):
    try:
        resultado = db.productos.delete_one({"nombre": nombre})
        if resultado.deleted_count > 0:
            return jsonify({"status": "ok", "mensaje": "Producto eliminado"}), 200
        return jsonify({"error": "No se encontró el producto"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos/<nombre>', methods=['PUT'])
def editar_producto(nombre):
    try:
        datos = request.get_json(force=True)
        nuevos_valores = {
            "$set": {
                "precio_total": float(datos.get('precio_total')),
                "descripcion": datos.get('descripcion'),
                "username_cliente": datos.get('username_cliente')
            }
        }
        db.productos.update_one({"nombre": nombre}, nuevos_valores)
        return jsonify({"status": "ok", "mensaje": "Producto actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 3. SISTEMA DE ABONOS ---

@app.route('/api/abonos', methods=['POST'])
def registrar_abono():
    try:
        datos = request.get_json(force=True)
        nuevo_abono = {
            "username_cliente": datos.get('username_cliente'),
            "nombre_producto": datos.get('nombre_producto'),
            "monto": float(datos.get('monto', 0)),
            "fecha": datos.get('fecha')
        }
        db.abonos.insert_one(nuevo_abono)
        return jsonify({"status": "ok", "mensaje": "Abono guardado en Atlas"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/abonos/eliminar', methods=['POST'])
def eliminar_abono():
    try:
        datos = request.get_json(force=True)
        db.abonos.delete_one({
            "username_cliente": datos.get('username_cliente'),
            "nombre_producto": datos.get('nombre_producto'),
            "fecha": datos.get('fecha')
        })
        return jsonify({"status": "ok", "mensaje": "Abono eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mis-compras/<username>', methods=['GET'])
def obtener_compras_cliente(username):
    try:
        compras = list(db.productos.find({"username_cliente": username}, {"_id": 0}))
        return jsonify(compras), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/historial-pagos/<username>/<producto>', methods=['GET'])
def obtener_historial(username, producto):
    try:
        historial = list(db.abonos.find({
            "username_cliente": username,
            "nombre_producto": producto
        }, {"_id": 0}))
        return jsonify(historial), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/usuarios/clientes', methods=['GET'])
def obtener_clientes():
    try:
        # Se corrigió la indentación aquí
        lista_clientes = list(db.usuarios.find({"rol": "cliente"}, {"_id": 0, "password": 0}))
        return jsonify(lista_clientes), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos/autorizar-compra', methods=['POST'])
def autorizar_compra():
    try:
        datos = request.get_json(force=True)
        vendedor_user = datos.get('username_vendedor')
        vendedor_pass = datos.get('password_vendedor')
        cliente_user = datos.get('username_cliente')
        nombre_mueble = datos.get('nombre_producto')

        vendedor_db = db.usuarios.find_one({"username": vendedor_user, "rol": "vendedor"})
        
        if not vendedor_db or not check_password_hash(vendedor_db['password'], vendedor_pass):
            return jsonify({"error": "Credenciales de vendedor inválidas"}), 401

        resultado = db.productos.update_one(
            {"nombre": nombre_mueble},
            {"$set": {"username_cliente": cliente_user}}
        )

        if resultado.modified_count > 0:
            return jsonify({"status": "ok", "mensaje": "Compra autorizada y asignada"}), 200
        else:
            return jsonify({"error": "No se pudo asignar el producto"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ARRANQUE ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
