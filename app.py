from flask import Flask, render_template

from dbsuite.erd import routes as erd_routes
from dbsuite.relational import routes as relational_routes

app = Flask(__name__, template_folder=".", static_folder="dbsuite/relational/static")

app.add_url_rule("/api/generate", "lab1_generate", erd_routes.api_generate, methods=["POST"])
app.add_url_rule("/api/render", "lab1_render", erd_routes.api_render, methods=["POST"])
app.add_url_rule("/api/convert", "lab2_convert", relational_routes.api_convert, methods=["POST"])
app.add_url_rule("/api/query", "lab2_query", relational_routes.api_query, methods=["POST"])


@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
