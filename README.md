# Segmentacion-Clientes

# 📊 AWS Glue RFM Customer Segmentation Project

## 📌 Descripción del proyecto
Este proyecto implementa un proceso ETL en AWS utilizando **AWS Glue**, con el objetivo de limpiar, transformar y analizar datos de clientes para generar segmentación basada en el modelo **RFM (Recency, Frequency, Monetary Value)**.

---

## ⚙️ Arquitectura del proyecto

El flujo de datos es el siguiente:

1. **S3 (raw layer)**  
   Se sube el dataset original en formato CSV.

2. **AWS Glue (ETL job)**  
   - Limpieza de datos (nulos y duplicados)
   - Transformación de tipos de datos
   - Cálculo de métricas RFM

3. **S3 (processed layer)**  
   Se guardan los datos procesados en formato **Parquet**

4. **Amazon Athena**  
   Se realizan consultas SQL para analizar los resultados

---

## 🧹 Proceso ETL

### 1. Extracción
Los datos se leen desde:
