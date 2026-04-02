# ============================================================================
# 📦 STOCKLINK - Backend API
# Versión: 1.0.0
# ============================================================================

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración de base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ============================================================================
# MODELOS
# ============================================================================

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    codigo_barras = db.Column(db.String(50), unique=True)
    cantidad = db.Column(db.Float, default=0)
    unidad_medida = db.Column(db.String(20), default='unidades')
    stock_minimo = db.Column(db.Float, default=5)
    precio = db.Column(db.Float, default=0)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    categoria = db.Column(db.String(100))
    ubicacion = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'codigo_barras': self.codigo_barras,
            'cantidad': self.cantidad,
            'unidad_medida': self.unidad_medida,
            'stock_minimo': self.stock_minimo,
            'precio': self.precio,
            'fecha_vencimiento': self.fecha_vencimiento.strftime('%Y-%m-%d') if self.fecha_vencimiento else None,
            'categoria': self.categoria,
            'ubicacion': self.ubicacion,
            'activo': self.activo
        }


class Movimiento(db.Model):
    __tablename__ = 'movimientos'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))
    tipo = db.Column(db.String(10), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    cantidad_anterior = db.Column(db.Float)
    cantidad_nueva = db.Column(db.Float)
    motivo = db.Column(db.String(200))
    usuario = db.Column(db.String(50), default='StockLink')
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    producto = db.relationship('Producto', backref='movimientos')

    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto.nombre if self.producto else 'N/A',
            'tipo': self.tipo,
            'cantidad': self.cantidad,
            'fecha': self.fecha.strftime('%Y-%m-%d %H:%M:%S'),
            'motivo': self.motivo
        }


# ============================================================================
# RUTAS API
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'status': 'online',
        'app': 'StockLink API',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/productos', methods=['GET'])
def get_productos():
    productos = Producto.query.filter_by(activo=True).all()
    return jsonify({'success': True, 'productos': [p.to_dict() for p in productos]})


@app.route('/api/productos/buscar/<codigo>', methods=['GET'])
def buscar_producto(codigo):
    producto = Producto.query.filter_by(codigo_barras=codigo, activo=True).first()
    if producto:
        return jsonify({'success': True, 'producto': producto.to_dict()})
    return jsonify({'success': False, 'message': 'No encontrado'}), 404


@app.route('/api/productos', methods=['POST'])
def crear_producto():
    data = request.json
    producto = Producto(
        nombre=data['nombre'],
        codigo_barras=data.get('codigo_barras'),
        cantidad=data.get('cantidad', 0),
        unidad_medida=data.get('unidad_medida', 'unidades'),
        stock_minimo=data.get('stock_minimo', 5),
        precio=data.get('precio', 0),
        categoria=data.get('categoria'),
        ubicacion=data.get('ubicacion')
    )
    db.session.add(producto)
    db.session.commit()
    return jsonify({'success': True, 'producto': producto.to_dict(), 'message': 'Producto creado'})


@app.route('/api/movimientos', methods=['POST'])
def registrar_movimiento():
    data = request.json
    producto = Producto.query.get_or_404(data['producto_id'])

    cantidad_anterior = producto.cantidad

    if data['tipo'] == 'ingreso':
        producto.cantidad += data['cantidad']
    else:
        producto.cantidad -= data['cantidad']

    movimiento = Movimiento(
        producto_id=producto.id,
        tipo=data['tipo'],
        cantidad=data['cantidad'],
        cantidad_anterior=cantidad_anterior,
        cantidad_nueva=producto.cantidad,
        motivo=data.get('motivo', ''),
        usuario=data.get('usuario', 'StockLink')
    )

    db.session.add(movimiento)
    db.session.commit()

    return jsonify({
        'success': True,
        'movimiento': movimiento.to_dict(),
        'stock_actual': producto.cantidad
    })


@app.route('/api/movimientos', methods=['GET'])
def get_movimientos():
    limite = request.args.get('limite', 50, type=int)
    movimientos = Movimiento.query.order_by(Movimiento.fecha.desc()).limit(limite).all()
    return jsonify({'success': True, 'movimientos': [m.to_dict() for m in movimientos]})


@app.route('/api/sync', methods=['POST'])
def sincronizar():
    return jsonify({
        'success': True,
        'app': 'StockLink',
        'timestamp': datetime.utcnow().isoformat(),
        'message': '✅ Sincronización exitosa'
    })


# ============================================================================
# INICIAR
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ StockLink: Base de datos verificada")

    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)