"""Inline everything into operation-storm-demo.html. Run after editing: python3 demo/build_single.py"""
import pathlib

d = pathlib.Path(__file__).parent
html = (d / "index.html").read_text()
for css in ["vendor/maplibre-gl.css", "styles.css"]:
    html = html.replace(f'<link rel="stylesheet" href="{css}" />', "<style>" + (d / css).read_text() + "</style>")
for js in ["vendor/maplibre-gl.js", "icons.js", "context.js", "data.js", "model.js", "app.js"]:
    html = html.replace(f'<script src="{js}"></script>', "<script>" + (d / js).read_text().replace("</script>", "<\\/script>") + "</script>")
(d / "operation-storm-demo.html").write_text(html)
print("wrote", d / "operation-storm-demo.html")
