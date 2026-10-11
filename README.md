# Segmentación de Clientes con RFM y K-Means en AWS

## Descripción del proyecto
Este proyecto implementa un pipeline en AWS para limpiar, transformar y analizar datos de clientes.
El objetivo principal es generar una segmentación de clientes basada en el modelo RFM (Recency, Frequency, Monetary Value) y agruparlos con un modelo K-Means.

---

## Arquitectura del proyecto

![Arquitectura](Image/)

El flujo de datos sigue una arquitectura tipo Data Lake:

1. **Analista de negocio**
   Sube el archivo CSV con las transacciones.

2. **Amazon S3 (raw layer)**
   Se almacenan los datos originales en formato CSV sin procesar.

3. **AWS Lambda**
   Se activa al subir el archivo y orquesta el proceso.

4. **AWS Glue (ETL job)**
   Se encarga de:
   - Lectura de datos desde S3
   - Limpieza de datos (valores nulos y duplicados)
   - Transformación de tipos de datos
   - Cálculo de métricas RFM

5. **Amazon S3 (processed layer)**
   Se guardan los datos procesados en formato Parquet.

6. **Amazon SageMaker Training**
   Se entrena un modelo K-Means (ml.m5.large) con las métricas RFM.

7. **Batch Transform**
   Genera las predicciones del cluster (`cluster_id`) de cada cliente.

8. **Amazon DynamoDB**
   Guarda la relación `customer_id → cluster_id` para consultarla rápidamente.

9. **Amazon Athena**
   Se utilizan consultas SQL sobre S3 y un notebook de SageMaker para analizar los datos.

---

## Proceso ETL

### 1. Extracción
Los datos se leen desde el bucket S3 en la ruta:

`s3://<nombre-del-bucket>/raw/transactions/`

---

### 2. Transformación
Durante esta etapa se realizan las siguientes operaciones:
- Eliminación de valores nulos
- Eliminación de registros duplicados
- Filtrado de valores negativos en Quantity y UnitPrice
- Conversión de InvoiceDate a formato timestamp
- Creación de la variable TotalAmount
- Cálculo de métricas RFM:
  - Recency (tiempo desde la última compra)
  - Frequency (número de compras)
  - Monetary Value (total gastado por cliente)

---

### 3. Carga
Los datos finales se almacenan en S3 en formato Parquet en la ruta:

`s3://<nombre-del-bucket>/processed/rfm_data/`

---

## Consultas en Amazon Athena

**Consulta 1: Crear la tabla externa sobre los datos procesados**
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS rfm_data (
    CustomerID string,
    Recency int,
    Frequency int,
    MonetaryValue double
)
STORED AS PARQUET
LOCATION 's3://<nombre-del-bucket>/processed/rfm_data/';
```

**Consulta 2: Ver muestras de datos**
```sql
SELECT * FROM rfm_data LIMIT 10;
```

**Consulta 3: Estadísticas**
```sql
SELECT
    COUNT(*) AS total_clientes,
    AVG(Recency) AS recencia_promedio,
    AVG(Frequency) AS frecuencia_promedio,
    AVG(MonetaryValue) AS valor_monetario_promedio,
    MIN(Recency) AS recencia_minima,
    MAX(Recency) AS recencia_maxima
FROM rfm_data;
```

**Consulta 4: Distribución de clientes por valor**
```sql
SELECT
    CASE
        WHEN MonetaryValue < 100 THEN 'Bajo'
        WHEN MonetaryValue < 500 THEN 'Medio'
        ELSE 'Alto'
    END AS segmento_valor,
    COUNT(*) AS cantidad_clientes
FROM rfm_data
GROUP BY 1;
```
