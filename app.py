import dash
from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px
import pandas as pd
import random

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
# Estados posibles (puedes extenderlos a MESI/MOESI)
ESTADOS = ["M", "E", "S", "I"]
COLORES = {
    "M": "red",
    "E": "blue",
    "S": "green",
    "I": "gray"
}

# Simulación inicial: 3 procesadores, 4 bloques
procesadores = ["P0", "P1", "P2"]
bloques = ["B0", "B1", "B2", "B3"]

def generar_estado_inicial():
    data = []
    for p in procesadores:
        for b in bloques:
            estado = random.choice(ESTADOS)
            data.append({"Procesador": p, "Bloque": b, "Estado": estado})
    return pd.DataFrame(data)

df_estado = generar_estado_inicial()

# ==============================
# CREACIÓN DE LA APP
# ==============================
app = Dash(__name__)
app.title = "Simulador de Coherencia de Caché"

app.layout = html.Div([
    html.H1("Simulador de Coherencia de Caché", style={'textAlign': 'center'}),

    html.Div([
        html.Button("⏭️ Siguiente paso", id="btn-next", n_clicks=0, style={
            "backgroundColor": "#1f77b4",
            "color": "white",
            "border": "none",
            "padding": "10px 20px",
            "borderRadius": "10px",
            "fontSize": "16px",
            "cursor": "pointer"
        })
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    html.Div([
        dcc.Graph(id="graph-cache", style={'height': '500px'}),
    ], style={'margin': 'auto', 'width': '80%'}),

    html.H3("Tabla de estados", style={'textAlign': 'center'}),
    html.Div(id="table-container", style={'width': '50%', 'margin': 'auto'})
])

# ==============================
# CALLBACKS (lógica interactiva)
# ==============================
@app.callback(
    Output("graph-cache", "figure"),
    Output("table-container", "children"),
    Input("btn-next", "n_clicks"),
    State("graph-cache", "figure")
)
def actualizar_simulacion(n_clicks, current_fig):
    # Generamos nuevos estados aleatorios (aquí luego pondrás tu lógica del protocolo)
    new_df = generar_estado_inicial()

    # Visualización gráfica (scatter plot tipo matriz)
    fig = px.scatter(
        new_df,
        x="Bloque",
        y="Procesador",
        color="Estado",
        color_discrete_map=COLORES,
        size=[30] * len(new_df),
        title=f"Paso {n_clicks}",
    )
    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=bloques),
        yaxis=dict(categoryorder="array", categoryarray=procesadores[::-1]),
        plot_bgcolor="#111",
        paper_bgcolor="#111",
        font_color="white"
    )

    # Tabla de estados
    table = html.Table([
        html.Thead(
            html.Tr([html.Th("Procesador"), html.Th("Bloque"), html.Th("Estado")])
        ),
        html.Tbody([
            html.Tr([
                html.Td(row.Procesador),
                html.Td(row.Bloque),
                html.Td(row.Estado)
            ]) for row in new_df.itertuples()
        ])
    ], style={
        'borderCollapse': 'collapse',
        'width': '100%',
        'textAlign': 'center',
        'border': '1px solid #888',
        'color': 'white'
    })

    return fig, table

# ==============================
# EJECUCIÓN
# ==============================
if __name__ == "__main__":
    app.run(debug=True)

