import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json

# Configuracion de la pagina
st.set_page_config(page_title="Descuentos y Impacto", layout="wide")

# Titulo principal
st.title("Dashboard 2: Descuentos y Analisis de Impacto")
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

# Numero de clientes por cluster del modelo K-Means Reto 4
num_clientes = [109, 643, 7, 8, 333]
colores = ['#FFD700', '#87CEEB', '#FF1493', '#FF8C00', '#32CD32']

# LLAMADA A LA API PARA OBTENER DESCUENTOS DE CADA CLUSTER
st.subheader("Consultando API para obtener descuentos por segmento...")

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
    st.success("Descuentos obtenidos correctamente desde la API")

    # Construir dataframe con los datos de descuento que devuelve la API
    df_discounts = pd.DataFrame({
        'cluster_name': [r['cluster_name'] for r in resultados],
        'num_clientes': num_clientes,
        'avg_monetary': [r['rfm_input']['MonetaryValue'] for r in resultados],
        'discount_percent': [r['discount']['discount_percent'] for r in resultados],
        'discount_amount': [r['discount']['discount_amount'] for r in resultados],
        'final_price': [r['discount']['final_price'] for r in resultados],
        'reason': [r['discount']['reason'] for r in resultados],
        'color': colores
    })

    # Calcular el impacto financiero total por cluster
    df_discounts['total_valor'] = df_discounts['num_clientes'] * df_discounts['avg_monetary']
    df_discounts['total_descuento'] = df_discounts['total_valor'] * (df_discounts['discount_percent'] / 100)
    df_discounts['valor_final'] = df_discounts['total_valor'] - df_discounts['total_descuento']

    # Calcular totales globales (necesarios para los KPIs)
    total_clientes = sum(num_clientes)
    total_valor_sin_desc = df_discounts['total_valor'].sum()
    total_descuentos = df_discounts['total_descuento'].sum()
    total_valor_con_desc = df_discounts['valor_final'].sum()
    avg_discount_percent = (total_descuentos / total_valor_sin_desc * 100) if total_valor_sin_desc > 0 else 0

    st.markdown("---")

    # PARTE 1: KPIs GLOBALES
    st.subheader("Resumen Global")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Numero total de segmentos analizados
        st.metric("Clusters Analizados", len(df_discounts))

    with col2:
        # Total de clientes en todos los segmentos
        st.metric("Total Clientes", f"{total_clientes:,}")

    with col3:
        # Descuento medio ponderado sobre el valor total
        st.metric("Descuento Medio", f"{avg_discount_percent:.2f}%")

    with col4:
        # Impacto economico total de los descuentos aplicados
        st.metric("Impacto Total Descuentos", f"{total_descuentos:,.2f} euros")

    st.markdown("---")

    # PARTE 2: EXPLICACION DE NEGOCIO
    st.info("""
    Los descuentos no se aplican de forma aleatoria.
    Cada segmento recibe una estrategia distinta segun su comportamiento RFM:

    - Clientes Champions: descuentos bajos (2%) para mantener su fidelidad sin reducir margen.
    - Clientes Promesas: descuentos medios (12%) para aumentar su recurrencia de compra.
    - Clientes Buenos Recientes: descuentos altos (10%) para fidelizacion inicial.
    - Outliers Alto Valor: descuento exclusivo (3%) por su extraordinario valor economico.
    - Outliers Frecuencia: descuento por volumen (5%) para reconocer su lealtad de compra.
    """)

    st.markdown("---")

    # PARTE 3: TABLA RESUMEN DE DESCUENTOS
    st.subheader("Tabla de Descuentos por Cluster (datos desde API)")

    # Tabla con el descuento aplicado a cada segmento y su impacto financiero
    discount_table = pd.DataFrame({
        'Cluster': df_discounts['cluster_name'],
        'Clientes': df_discounts['num_clientes'],
        'Descuento %': df_discounts['discount_percent'].astype(str) + '%',
        'Valor Medio (euros)': df_discounts['avg_monetary'].apply(lambda x: f"{x:,.2f}"),
        'Valor Total (euros)': df_discounts['total_valor'].apply(lambda x: f"{x:,.2f}"),
        'Descuento Total (euros)': df_discounts['total_descuento'].apply(lambda x: f"{x:,.2f}"),
        'Valor con Descuento (euros)': df_discounts['valor_final'].apply(lambda x: f"{x:,.2f}"),
        'Razon': df_discounts['reason']
    })

    st.dataframe(discount_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # PARTE 4: GRAFICOS DE DESCUENTOS
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Porcentaje de Descuento por Cluster")

        # Grafico de barras con el porcentaje de descuento asignado a cada segmento
        fig_discount_percent = go.Figure(data=[go.Bar(
            x=df_discounts['cluster_name'],
            y=df_discounts['discount_percent'],
            marker=dict(color=df_discounts['color']),
            text=df_discounts['discount_percent'].astype(str) + '%',
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Descuento: %{y}%<extra></extra>'
        )])
        fig_discount_percent.update_layout(
            height=450,
            xaxis_title="Cluster",
            yaxis_title="Descuento (%)",
            xaxis_tickangle=-45,
            showlegend=False
        )
        st.plotly_chart(fig_discount_percent, use_container_width=True)

    with col2:
        st.subheader("Distribucion del Impacto de Descuentos")

        # Grafico donut que muestra que cluster consume mas descuento economicamente
        fig_donut = go.Figure(data=[go.Pie(
            labels=df_discounts['cluster_name'],
            values=df_discounts['total_descuento'],
            hole=0.5,
            marker=dict(colors=df_discounts['color']),
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Descuento total: %{value:,.2f} euros<extra></extra>'
        )])
        fig_donut.update_layout(height=450)
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")

    # Grafico comparativo valor sin descuento vs valor con descuento por cluster
    st.subheader("Comparativa: Valor Sin Descuento vs Valor Con Descuento por Cluster")

    fig_comparison = go.Figure(data=[
        go.Bar(
            name='Sin Descuento',
            x=df_discounts['cluster_name'],
            y=df_discounts['total_valor'],
            marker=dict(color='#FF6B6B'),
            hovertemplate='<b>%{x}</b><br>Valor: %{y:,.2f} euros<extra></extra>'
        ),
        go.Bar(
            name='Con Descuento',
            x=df_discounts['cluster_name'],
            y=df_discounts['valor_final'],
            marker=dict(color='#51CF66'),
            hovertemplate='<b>%{x}</b><br>Valor con Descuento: %{y:,.2f} euros<extra></extra>'
        )
    ])
    fig_comparison.update_layout(
        barmode='group',
        height=450,
        xaxis_tickangle=-45,
        legend=dict(x=0.7, y=0.95),
        yaxis_title="Euros"
    )
    st.plotly_chart(fig_comparison, use_container_width=True)

    st.markdown("---")

   # PARTE 5: ANALISIS DE RETORNO DE INVERSION (ROI)
    st.subheader("Analisis de Retorno de Inversion (ROI)")

    st.write("""
    Si los descuentos generan un incremento del 15% en las compras,
    el costo de los descuentos queda compensado y se obtiene beneficio neto.
    """)

    # Simulacion con un incremento estimado del 15% en compras
    incremento_compras = 0.15
    incremento_valor = total_valor_con_desc * incremento_compras
    beneficio_neto = incremento_valor - total_descuentos

    col1, col2, col3 = st.columns(3)

    with col1:
        # Incremento de ingresos estimado si los clientes compran un 15% mas
        st.metric("Incremento Estimado de Compras (15%)", f"{incremento_valor:,.2f} euros")

    with col2:
        # Costo total que suponen los descuentos aplicados
        st.metric("Costo Total de Descuentos", f"{total_descuentos:,.2f} euros")

    with col3:
        # Beneficio neto resultante de restar el costo al incremento estimado
        st.metric("Beneficio Neto Estimado", f"{beneficio_neto:,.2f} euros")
else:
    st.error("No se pudieron obtener los datos de la API. Verifica la URL.")

st.markdown("---")
st.caption("Dashboard conectado a API Gateway - Lambda - Modelo K-Means Reto 4")