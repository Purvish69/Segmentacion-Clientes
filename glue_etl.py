import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime

# 1. CONFIGURACIÓN INICIAL
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_INPUT', 'S3_OUTPUT'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("[LOG] ✓ Job iniciado")

# 2. LECTURA DE DATOS CRUDOS
print("[LOG] Leyendo datos de:", args['S3_INPUT'])

df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(args['S3_INPUT'])

print(f"[LOG] Registros cargados: {df.count()}")
print("[LOG] Esquema:")
df.printSchema()

# 3. LIMPIEZA DE DATOS
print("\n[LOG] === INICIANDO LIMPIEZA ===")

# Eliminar nulos en columnas clave
df_clean = df.dropna(subset=['CustomerID', 'InvoiceNo', 'Quantity', 'UnitPrice'])
print(f"[LOG] Registros tras eliminar nulos: {df_clean.count()}")

# Eliminar duplicados exactos
df_clean = df_clean.dropDuplicates()
print(f"[LOG] Registros tras eliminar duplicados: {df_clean.count()}")

# Filtrar cantidades negativas (devoluciones, no las queremos para RFM)
df_clean = df_clean.filter(col('Quantity') > 0)
df_clean = df_clean.filter(col('UnitPrice') > 0)
print(f"[LOG] Registros tras filtrar negativas: {df_clean.count()}")

# 4. NORMALIZACIÓN DE DATOS
print("\n[LOG] === INICIANDO NORMALIZACIÓN ===")

# Convertir InvoiceDate a timestamp
df_norm = df_clean.withColumn(
    'InvoiceDate',
    to_timestamp(col('InvoiceDate'), 'M/d/yyyy H:mm')
)

# Crear columna de monto total (Quantity * UnitPrice)
df_norm = df_norm.withColumn(
    'TotalAmount',
    col('Quantity') * col('UnitPrice')
)

# Asegurarse de que CustomerID es string sin espacios
df_norm = df_norm.withColumn(
    'CustomerID',
    trim(col('CustomerID')).cast('string')
)

print("[LOG] Normalización completada")
df_norm.printSchema()

# 5. CÁLCULO RFM
print("\n[LOG] === CALCULANDO RFM ===")

# Fecha de referencia: la máxima fecha en el dataset + 1 día
max_date = df_norm.agg(max('InvoiceDate')).collect()[0][0]

reference_date = date_add(to_date(lit(max_date)), 1)

print(f"[LOG] Fecha de referencia para Recencia: {reference_date}")

# Crear tabla RFM
rfm = df_norm.groupBy('CustomerID').agg(
    # Recencia: días desde última compra
    datediff(lit(reference_date), max('InvoiceDate')).alias('Recency'),
    # Frecuencia: número de transacciones
    count('InvoiceNo').alias('Frequency'),
    # Valor Monetario: suma total gastado
    sum('TotalAmount').alias('MonetaryValue')
).filter(col('CustomerID').isNotNull())

print(f"[LOG] Clientes únicos con RFM: {rfm.count()}")
rfm.show(10)

# 6. ESTADÍSTICAS DE CONTROL
print("\n[LOG] === ESTADÍSTICAS RFM ===")
rfm.describe(['Recency', 'Frequency', 'MonetaryValue']).show()

# 7. ESCRITURA DE DATOS PROCESADOS
print("\n[LOG] === ESCRIBIENDO DATOS PROCESADOS ===")
print(f"[LOG] Destino: {args['S3_OUTPUT']}")

rfm.coalesce(1).write \
    .mode('overwrite') \
    .parquet(args['S3_OUTPUT'])

print("[LOG] ✓ Datos guardados en Parquet")

# FINALIZACIÓN
job.commit()
print("[LOG] ✓ Job completado exitosamente")