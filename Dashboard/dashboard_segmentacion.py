import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json

# Configuracion de la pagina
st.set_page_config(page_title="Segmentacion de Clientes RFM", layout="wide")

# Titulo principal
st.title("Dashboard 1: Segmentacion de Clientes RFM")
st.markdown("---")

# URL de la API Gateway
API_URL = "https://vegs9ffk1h.execute-api.us-east-1.amazonaws.com/prod/predict"

# Un cliente representativo por cada cluster para llamar a la API
clientes_ejemplo = [
    {"Recency": 15, "Frequency": 98,  "MonetaryValue": 1904.48, "customer_id": "C_CHAMPIONS_001"},
    {"Recency": 38, "Frequency": 22,  "MonetaryValue": 401.93,  "customer_id": "C_PROMESAS_001"},
    {"Recency": 10, "Frequency": 67,  "MonetaryValue": 20392.79,"customer_id": "C_OUTLIER_VALOR_001"},
    {"Recency": 9,  "Frequency": 372, "MonetaryValue": 5607.05, "customer_id": "C_OUTLIER_FREQ_001"},
    {"Recency": 7,  "Frequency": 24,  "MonetaryValue": 607.50,  "customer_id": "C_BUENOS_RECIENTES_001"},
]

# Numero de clientes por cluster obtenido del modelo K-Means en Reto 4
num_clientes = [109, 643, 7, 8, 333]
porcentajes = [9.9, 58.5, 0.6, 0.7, 30.3]
colores = ['#FFD700', '#87CEEB', '#FF1493', '#FF8C00', '#32CD32']

# ============================================================
# LLAMADA A LA API PARA OBTENER EL CLUSTER DE CADA CLIENTE
# ============================================================
st.subheader("Consultando API para obtener la segmentacion de cada cliente...")

resultados = []
errores = False

for cliente in clientes_ejemplo:
    try:
        response = requests.post(API_URL, json=cliente, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data.get('body'), str):
                data = json.loads(data['body'])
            resultados.append(data)
        else:
            errores = True
            st.error(f"Error en API para {cliente['customer_id']}: {response.status_code}")
    except Exception as e:
        errores = True
        st.error(f"Error de conexion: {str(e)}")

if not errores and len(resultados) == 5:
    st.success("Segmentacion obtenida correctamente desde la API")

    # Construir dataframe solo con datos de segmentacion, sin descuentos
    df_clusters = pd.DataFrame({
        'cluster': [r['cluster'] for r in resultados],
        'cluster_name': [r['cluster_name'] for r in resultados],
        'clientes': num_clientes,
        'porcentaje': porcentajes,
        'recency_media': [r['rfm_input']['Recency'] for r in resultados],
        'frequency_media': [r['rfm_input']['Frequency'] for r in resultados],
        'monetaryvalue_media': [r['rfm_input']['MonetaryValue'] for r in resultados],
        'confidence': [r['confidence'] for r in resultados],
        'color': colores
    })

    st.markdown("---")

    # SECCION 1: DISTRIBUCION DE CLIENTES POR CLUSTER
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribucion de Clientes por Cluster")

        # Grafico de pastel con el porcentaje de clientes en cada segmento
        fig_pie = go.Figure(data=[go.Pie(
            labels=df_clusters['cluster_name'],
            values=df_clusters['clientes'],
            marker=dict(colors=df_clusters['color']),
            textposition='inside',
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Clientes: %{value}<br>%{percent}<extra></extra>'
        )])
        fig_pie.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Resumen por Segmento")

        # Tabla con numero de clientes y porcentaje por cluster
        summary_table = pd.DataFrame({
            'Cluster': df_clusters['cluster_name'],
            'Clientes': df_clusters['clientes'],
            'Porcentaje': df_clusters['porcentaje'].astype(str) + '%'
        })
        st.dataframe(summary_table, use_container_width=True, hide_index=True)
        st.metric("Total Clientes", sum(num_clientes))

    st.markdown("---")

    # SECCION 2: TABLA RFM POR CLUSTER (DATOS DESDE API)
    st.subheader("Caracteristicas RFM por Segmento (datos obtenidos desde API)")

    # Tabla con los valores RFM medios de cada cluster
    rfm_table = pd.DataFrame({
        'Cluster': df_clusters['cluster_name'],
        'Clientes': df_clusters['clientes'],
        'Recency (dias)': df_clusters['recency_media'],
        'Frequency (compras)': df_clusters['frequency_media'],
        'Monetary Value (euros)': df_clusters['monetaryvalue_media'],
        'Confianza del modelo (%)': (df_clusters['confidence'] * 100).round(1)
    })
    st.dataframe(rfm_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # SECCION 3: GRAFICOS DE BARRAS POR METRICA RFM
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Recencia Media por Cluster")

        # Dias desde la ultima compra por segmento
        fig_recency = go.Figure(data=[go.Bar(
            x=df_clusters['cluster_name'],
            y=df_clusters['recency_media'],
            marker=dict(color=df_clusters['color']),
            text=df_clusters['recency_media'],
            textposition='outside'
        )])
        fig_recency.update_layout(
            height=500,
            xaxis_tickangle=-45,
            showlegend=False,
            yaxis_title="Dias"
        )
        st.plotly_chart(fig_recency, use_container_width=True)

    with col2:
        st.subheader("Frecuencia Media por Cluster")

        # Numero de compras por segmento
        fig_frequency = go.Figure(data=[go.Bar(
            x=df_clusters['cluster_name'],
            y=df_clusters['frequency_media'],
            marker=dict(color=df_clusters['color']),
            text=df_clusters['frequency_media'],
            textposition='outside'
        )])
        fig_frequency.update_layout(
            height=500,
            xaxis_tickangle=-45,
            showlegend=False,
            yaxis_title="Numero de compras"
        )
        st.plotly_chart(fig_frequency, use_container_width=True)

    with col3:
        st.subheader("Valor Monetario Medio por Cluster")

        # Gasto medio en euros por segmento
        fig_monetary = go.Figure(data=[go.Bar(
            x=df_clusters['cluster_name'],
            y=df_clusters['monetaryvalue_media'],
            marker=dict(color=df_clusters['color']),
            text=df_clusters['monetaryvalue_media'],
            textposition='outside'
        )])
        fig_monetary.update_layout(
            height=500,
            xaxis_tickangle=-45,
            showlegend=False,
            yaxis_title="Euros"
        )
        st.plotly_chart(fig_monetary, use_container_width=True)

    st.markdown("---")

    # SECCION 4: DETALLE DE SEGMENTACION POR CLUSTER (SIN DESCUENTOS)
    st.subheader("Detalle de segmentacion por cluster")

    # Descripcion de cada segmento basada en el analisis del modelo
    descripcion = {
        'CHAMPIONS': 'Clientes de maxima lealtad. Compran frecuentemente, han comprado recientemente y gastan cantidades significativas.',
        'PROMESAS': 'Clientes con potencial. Siguen activos pero con menor frecuencia que champions.',
        'OUTLIERS ALTO VALOR': 'VIP absoluto. Pocos clientes pero gastan cantidades extraordinarias.',
        'OUTLIERS FRECUENCIA': 'Compradores muy frecuentes. Frecuencia extremadamente alta.',
        'BUENOS CLIENTES RECIENTES': 'Nuevos clientes prometedores. Acaban de empezar pero muestran potencial.'
    }
    
    for r in resultados:
        with st.expander(f"Segmento: {r['cluster_name']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Customer ID:** {r['customer_id']}")
                st.write(f"**Cluster asignado:** {r['cluster']} - {r['cluster_name']}")
                st.write(f"**Confianza del modelo:** {round(r['confidence']*100, 1)}%")
                st.write(f"**Descripcion del segmento:** {descripcion.get(r['cluster_name'], 'No disponible')}")
            with col2:
                st.write(f"**Recency:** {r['rfm_input']['Recency']} dias")
                st.write(f"**Frequency:** {r['rfm_input']['Frequency']} compras")
                st.write(f"**Monetary Value:** {r['rfm_input']['MonetaryValue']} euros")

else:
    st.error("No se pudieron obtener los datos de la API. Verifica la URL.")

st.markdown("---")
st.caption("Dashboard conectado a API Gateway - Lambda - Modelo K-Means Reto 4")