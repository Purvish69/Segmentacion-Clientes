import json
from datetime import datetime
import math

# Valores extraídos del scaler entrenado en Reto 4
# Se usan para normalizar los datos de entrada antes de predecir
SCALER_MEAN = [26.59727273, 33.13636364, 778.11948182]   # Media de Recency, Frequency, MonetaryValue
SCALER_SCALE = [15.99978954, 43.59042373, 1883.59317308]  # Desviación estándar de cada variable

# Centroides del modelo K-Means entrenado en Reto 4 (ya escalados)
# Cada fila es un cluster: [Recency_scaled, Frequency_scaled, MonetaryValue_scaled]
CENTROIDS = [
    [-0.68068712,  1.50633547,  0.59798722],  # Cluster 0: CHAMPIONS
    [ 0.76069757, -0.25437129, -0.19972137],  # Cluster 1: PROMESAS
    [-1.01055712,  0.79324584, 10.41343334],  # Cluster 2: OUTLIERS ALTO VALOR
    [-1.0764062,   7.7910148,   2.56367887],  # Cluster 3: OUTLIERS FRECUENCIA
    [-1.19894442, -0.20573774, -0.09058028],  # Cluster 4: BUENOS CLIENTES RECIENTES
]

# Descuentos asignados a cada cluster según estrategia de negocio
DISCOUNT_TABLE = {
    0: {'name': 'CHAMPIONS',                 'discount_percent': 2,  'reason': 'Cliente de máxima lealtad - Descuento VIP'},
    1: {'name': 'PROMESAS',                  'discount_percent': 12, 'reason': 'Potencial medio - Descuento por retención'},
    2: {'name': 'OUTLIERS ALTO VALOR',       'discount_percent': 3,  'reason': 'VIP absoluto - Descuento exclusivo'},
    3: {'name': 'OUTLIERS FRECUENCIA',       'discount_percent': 5,  'reason': 'Comprador muy frecuente - Descuento por volumen'},
    4: {'name': 'BUENOS CLIENTES RECIENTES', 'discount_percent': 10, 'reason': 'Cliente nuevo prometedor - Descuento bienvenida'},
}

def scale(values):
    """
    Normaliza los valores RFM usando la media y desviación estándar del scaler.
    Fórmula: (valor - media) / desviacion_estandar
    """
    return [(values[i] - SCALER_MEAN[i]) / SCALER_SCALE[i] for i in range(3)]

def euclidean(a, b):
    """
    Calcula la distancia euclidiana entre dos puntos.
    Se usa para medir qué tan cerca está un cliente de cada centroide.
    """
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

def predict_cluster(recency, frequency, monetary):
    """
    Predice el cluster de un cliente basándose en sus valores RFM.
    1. Escala los datos
    2. Calcula distancia a cada centroide
    3. El cluster más cercano es el predicho
    4. La confianza indica qué tan claro es el cluster (0 a 1)
    """
    scaled = scale([recency, frequency, monetary])
    distances = [euclidean(scaled, c) for c in CENTROIDS]
    cluster = distances.index(min(distances))
    min_d = distances[cluster]
    max_d = max(distances)
    confidence = 1 - (min_d / (max_d + 1e-6))  # 1e-6 evita división por cero
    return cluster, confidence

def apply_discount(cluster, base_price):
    """
    Calcula el descuento a aplicar según el cluster del cliente.
    Devuelve el porcentaje, el ahorro en euros y el precio final.
    """
    info = DISCOUNT_TABLE[cluster]
    pct = info['discount_percent']
    amount = round(base_price * pct / 100, 2)
    return {
        'discount_percent': pct,
        'discount_amount': amount,
        'final_price': round(base_price - amount, 2),
        'savings_percentage': round(pct, 2),
        'reason': info['reason']
    }

def lambda_handler(event, context):
    """
    Punto de entrada de la Lambda. Recibe una petición HTTP con datos RFM,
    predice el cluster del cliente y devuelve el descuento correspondiente.
    
    Input esperado:
    {
        "Recency": 15,
        "Frequency": 98,
        "MonetaryValue": 1904.48,
        "customer_id": "C001"  (opcional)
    }
    """
    try:
        # Parsear el body del request (viene como string desde API Gateway)
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        # Validar que estén los campos obligatorios
        required = ['Recency', 'Frequency', 'MonetaryValue']
        if not all(f in body for f in required):
            return {'statusCode': 400, 'body': json.dumps({'error': f'Campos requeridos: {required}'})}

        # Extraer y convertir valores
        recency = float(body['Recency'])
        frequency = float(body['Frequency'])
        monetary = float(body['MonetaryValue'])
        customer_id = body.get('customer_id', 'UNKNOWN')

        # Validar rangos según los datos de entrenamiento del Reto 4
        if not (1 <= recency <= 50):
            return {'statusCode': 400, 'body': json.dumps({'error': 'Recency debe estar entre 1 y 50'})}
        if not (1 <= frequency <= 700):
            return {'statusCode': 400, 'body': json.dumps({'error': 'Frequency debe estar entre 1 y 700'})}
        if monetary < 0:
            return {'statusCode': 400, 'body': json.dumps({'error': 'MonetaryValue no puede ser negativo'})}

        # Predecir cluster y calcular descuento
        cluster, confidence = predict_cluster(recency, frequency, monetary)
        discount = apply_discount(cluster, monetary)

        # Logs para CloudWatch
        print(f"[LOG] CustomerID={customer_id} R={recency} F={frequency} M={monetary}")
        print(f"[LOG] Cluster={cluster} ({DISCOUNT_TABLE[cluster]['name']}) Confidence={confidence:.4f}")
        print(f"[LOG] Descuento={discount['discount_percent']}% Ahorro=€{discount['discount_amount']}")

        # Respuesta exitosa
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Predicción y descuento aplicado exitosamente',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'customer_id': customer_id,
                'cluster': cluster,
                'cluster_name': DISCOUNT_TABLE[cluster]['name'],
                'interpretation': DISCOUNT_TABLE[cluster]['name'],
                'confidence': round(confidence, 4),
                'rfm_input': {'Recency': recency, 'Frequency': frequency, 'MonetaryValue': monetary},
                'discount': discount,
                'model_version': '1.0'
            })
        }

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}