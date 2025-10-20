import plotly.graph_objects as go
import ipywidgets as widgets

# to show plotly figures in quarto HTML file
import plotly.io as pio

bellevue_color = ['#00C0C0', '#006598', '#FFA500']

# psrc template
pio.templates["bellevue_color"] = go.layout.Template(
    layout_colorway=bellevue_color, layout_font=dict(size=12, family="Poppins")
)

pio.renderers.default = "plotly_mimetype+notebook_connected"
pio.templates.default = "simple_white+bellevue_color" # set plotly template