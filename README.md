# Segmentacion-Clientes

# AWS Glue RFM Customer Segmentation Project

## Descripción del proyecto
Este proyecto implementa un proceso ETL utilizando AWS Glue para realizar limpieza, transformación y análisis de datos de clientes.  
El objetivo principal es generar una segmentación de clientes basada en el modelo RFM (Recency, Frequency, Monetary Value).

---

## Arquitectura del proyecto

El flujo de datos sigue una arquitectura tipo Data Lake:

1. **S3 (raw layer)**  
   Se almacenan los datos originales en formato CSV sin procesar.

2. **AWS Glue (ETL job)**  
   Se encarga de:
   - Lectura de datos desde S3
   - Limpieza de datos (valores nulos y duplicados)
   - Transformación de tipos de datos
   - Cálculo de métricas RFM

3. **S3 (processed layer)**  
   Se guardan los datos procesados en formato Parquet.

4. **Amazon Athena**  
   Se utilizan consultas SQL para analizar los datos procesados.

---

## Proceso ETL

### 1. Extracción
Los datos se leen desde el bucket S3 en la ruta:

s3://customer-segmentation-lake-ppatel/raw/transactions/

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

s3://customer-segmentation-lake-ppatel/processed/rfm_data/

---

## Consultas en Amazon Athena

Se crea una tabla externa sobre los datos procesados:

```sql
Consulta 1
CREATE EXTERNAL TABLE IF NOT EXISTS rfm_data (
    CustomerID string,
    Recency int,
    Frequency int,
    MonetaryValue double
)
STORED AS PARQUET
LOCATION 's3://customer-segmentation-lake-ppatel/processed/rfm_data/';
```
Consulta 2: Ver muestras de datos
```
SELECT * FROM rfm_data LIMIT 10;
```

Consulta 3: Estadísticas
```
SELECT 
    COUNT(*) as total_clientes,
    AVG(Recency) as recencia_promedio,
    AVG(Frequency) as frecuencia_promedio,
    AVG(MonetaryValue) as valor_monetario_promedio,
    MIN(Recency) as recencia_minima,
    MAX(Recency) as recencia_maxima
FROM rfm_data;
```
Consulta 4: Distribución de clientes por valor
```
SELECT CASE
		WHEN MonetaryValue < 100 THEN 'Bajo'
		WHEN MonetaryValue < 500 THEN 'Medio' ELSE 'Alto'
	END as segmento_valor,
	COUNT(*) as cantidad_clientes
FROM rfm_data
GROUP BY CASE
		WHEN MonetaryValue < 100 THEN 'Bajo'
		WHEN MonetaryValue < 500 THEN 'Medio' ELSE 'Alto'
	END;
```
