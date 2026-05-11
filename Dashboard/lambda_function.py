import json
import boto3
import joblib
import numpy as np
from io import BytesIO
from datetime import datetime

# Inicializar cliente S3
s3_client = boto3.client('s3')

# Configuración
BUCKET_NAME = 'customer-segmentation-lake-purvishpatel'
MODELS_PREFIX = 'output/models/'

# Variables globales para cachear modelos
kmeans_model = None
scaler = None
pca = None

# ===== TABLA DE DESCUENTOS POR CLUSTER =====
DISCOUNT_TABLE = {
    0: {  # CHAMPIONS
        'name': 'CHAMPIONS',
        'discount_percent': 2,
        'reason': 'Cliente de máxima lealtad - Descuento VIP',
        'color': '#FFD700'
    },
    1: {  # PROMESAS
        'name': 'PROMESAS',
        'discount_percent': 12,
        'reason': 'Potencial medio - Descuento por retención',
        'color': '#87CEEB'
    },
    2: {  # OUTLIERS ALTO VALOR
        'name': 'OUTLIERS ALTO VALOR',
        'discount_percent': 3,
        'reason': 'VIP absoluto - Descuento exclusivo',
        'color': '#FF1493'
    },
    3: {  # OUTLIERS FRECUENCIA
        'name': 'OUTLIERS FRECUENCIA',
        'discount_percent': 5,
        'reason': 'Comprador muy frecuente - Descuento por volumen',
        'color': '#FF8C00'
    },
    4: {  # BUENOS CLIENTES RECIENTES
        'name': 'BUENOS CLIENTES RECIENTES',
        'discount_percent': 10,
        'reason': 'Cliente nuevo prometedor - Descuento bienvenida',
        'color': '#32CD32'
    }
}

def load_models():
    # Carga los modelos entrenados desde S3
    global kmeans_model, scaler, pca

    if kmeans_model is not None:
        return

    try:
        print("Cargando modelos desde S3")

        # Descargar y cargar K-Means
        kmeans_file = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=f'{MODELS_PREFIX}kmeans_final_model.pkl'
        )
        kmeans_model = joblib.load(BytesIO(kmeans_file['Body'].read()))

        # Descargar y cargar Scaler
        scaler_file = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=f'{MODELS_PREFIX}scaler_final.pkl'
        )
        scaler = joblib.load(BytesIO(scaler_file['Body'].read()))

        # Descargar y cargar PCA
        pca_file = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=f'{MODELS_PREFIX}pca_final.pkl'
        )
        pca = joblib.load(BytesIO(pca_file['Body'].read()))

        print("Modelos cargados correctamente")

    except Exception as e:
        print(f"Error al cargar modelos: {str(e)}")
        raise

# Función para aplicar descuento basado en el cluster
def apply_discount(cluster_id, base_price):
    """
    Aplica descuento basado en el cluster
    """
    discount_info = DISCOUNT_TABLE.get(cluster_id)

    if not discount_info:
        return {'error': f'Cluster {cluster_id} no válido'}

    discount_percent = discount_info['discount_percent']
    discount_amount = base_price * (discount_percent / 100)
    final_price = base_price - discount_amount

    return {
        'cluster': cluster_id,
        'cluster_name': discount_info['name'],
        'base_price': round(base_price, 2),
        'discount_percent': discount_percent,
        'discount_amount': round(discount_amount, 2),
        'final_price': round(final_price, 2),
        'savings_percentage': round((discount_amount / base_price * 100), 2) if base_price > 0 else 0,
        'reason': discount_info['reason'],
        'color': discount_info['color']
    }


def lambda_handler(event, context):
    """
    Endpoint de inferencia para predecir cluster + aplicar descuento
    """

    try:
        load_models()

        # Parsear body del request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        print(f"Request recibido: {json.dumps(body)}")

        # Validar inputs requeridos
        required_fields = ['Recency', 'Frequency', 'MonetaryValue']
        if not all(field in body for field in required_fields):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Campos requeridos: {required_fields}',
                    'received': list(body.keys())
                })
            }

        # Extraer datos
        recency = float(body['Recency'])
        frequency = float(body['Frequency'])
        monetary_value = float(body['MonetaryValue'])
        customer_id = body.get('customer_id', 'UNKNOWN')

        print(f"Input: CustomerID={customer_id}, R={recency}, F={frequency}, M={monetary_value}")

        # Validaciones
        if recency < 1 or recency > 50:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Recency inválido'})}

        if frequency < 1 or frequency > 700:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Frequency inválido'})}

        if monetary_value < 0:
            return {'statusCode': 400, 'body': json.dumps({'error': 'MonetaryValue inválido'})}

        # Predicción de cluster
        X_input = np.array([[recency, frequency, monetary_value]])
        X_scaled = scaler.transform(X_input)
        cluster = int(kmeans_model.predict(X_scaled)[0])

        # Confianza
        distances = kmeans_model.transform(X_scaled)[0]
        min_distance = distances[cluster]
        max_distance = np.max(distances)
        confidence = 1 - (min_distance / (max_distance + 1e-6))

        # Aplicar descuento
        discount_result = apply_discount(cluster, monetary_value)

        cluster_names = {
            0: "CHAMPIONS",
            1: "PROMESAS",
            2: "OUTLIERS ALTO VALOR",
            3: "OUTLIERS FRECUENCIA",
            4: "BUENOS CLIENTES RECIENTES"
        }

        interpretation = cluster_names.get(cluster, "DESCONOCIDO")

        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Predicción y descuento aplicado exitosamente',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'customer_id': customer_id,
                'cluster': cluster,
                'cluster_name': discount_result['cluster_name'],
                'interpretation': interpretation,
                'confidence': round(float(confidence), 4),
                'rfm_input': {
                    'Recency': recency,
                    'Frequency': frequency,
                    'MonetaryValue': monetary_value
                },
                'discount': {
                    'discount_percent': discount_result['discount_percent'],
                    'discount_amount': discount_result['discount_amount'],
                    'final_price': discount_result['final_price'],
                    'savings_percentage': discount_result['savings_percentage'],
                    'reason': discount_result['reason']
                },
                'model_version': '1.0'
            })
        }

        print("Request completado exitosamente")
        return response

    except json.JSONDecodeError as e:
        print(f"JSON inválido: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'JSON inválido'})
        }

    except Exception as e:
        print(f"Error en lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }