from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
import pymysql
from functools import wraps

# ================= CONFIG =================
DB_HOST = "localhost"
DB_USER = "esp32_app"
DB_PASS = "esp32pass"
DB_NAME = "esp32_db"

SECRET_KEY = "CHANGE_THIS_SECRET"

# =========================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ----------- DB CONNECTION ---------------
def db():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

# =========================================
#               AUTH ROUTES
# =========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        con = db()
        with con.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM users WHERE username=%s",
                (username,)
            )
            user = cur.fetchone()
        con.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Neispravno korisničko ime ili lozinka")
            return render_template("login.html")

        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================================
#              PUBLIC PAGE
# =========================================
@app.route("/")
def index():
    return render_template("public_index.html")

# =========================================
#              DASHBOARD
# =========================================
@app.route("/dashboard")
def dashboard():
    con = db()
    cur = con.cursor()

    # 1️⃣ Zadnje mjerenje
    cur.execute("""
        SELECT temperature, humidity, created_at
        FROM sensor_data
        ORDER BY created_at DESC
        LIMIT 1
    """)
    latest = cur.fetchone()

    # 2️⃣ Povijest senzora
    cur.execute("""
        SELECT temperature, humidity, created_at
        FROM sensor_data
        ORDER BY created_at DESC
        LIMIT 50
    """)
    sensor_history = cur.fetchall()

    # Pragovi (ZA BOJE)
    cur.execute("""
        SELECT
            temp_low,
            temp_high,
            hum_low,
            hum_high,
            auto_control,
            fan_manual,
            heater_manual
        FROM settings
        WHERE id = 1
    """)
    settings = cur.fetchone()

    if settings is None:
        settings = {
        "temp_low": 0,
        "temp_high": 100,
        "hum_low": 0,
        "hum_high": 100,
        "auto_control": 1,
        "fan_manual": 0,
        "heater_manual": 0
    }

    settings["temp_low"] = float(settings["temp_low"])
    settings["temp_high"] = float(settings["temp_high"])
    settings["hum_low"] = float(settings["hum_low"])
    settings["hum_high"] = float(settings["hum_high"])

    cur.execute("""
        SELECT timestamp, temperature, humidity, alarm_type
        FROM alarm_log
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    alarm_history = cur.fetchall()
    # 🔒 ZATVORI TEK NA KRAJU
    cur.close()
    con.close()

    return render_template(
        "dashboard.html",
        latest=latest,
        sensor_history=sensor_history,
        alarm_history=alarm_history,
        settings=settings
    )

# =========================================
#            ESP32 SENSOR API
# =========================================
@app.route("/api/sensor", methods=["POST", "GET"])
def api_sensor():
    data = request.json

    temperature = data["temperature"]
    humidity = data["humidity"]

    con = db()
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO sensor_data (temperature, humidity) VALUES (%s, %s)",
            (temperature, humidity)
        )
        con.commit()
    con.close()

    return jsonify({"status": "ok"})

# =========================================
#            REAL TIME UPDATE
# =========================================
@app.route("/sensor-fragment")
def sensor_fragment():
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT temperature, humidity, created_at
        FROM sensor_data
        ORDER BY created_at DESC
        LIMIT 1
    """)
    latest = cur.fetchone()

    con.close()
    return render_template("sensor_fragment.html", latest=latest)

@app.route("/sensor-history-fragment")
def sensor_history_fragment():
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT temperature, humidity, created_at
        FROM sensor_data
        ORDER BY created_at DESC
        LIMIT 50
    """)
    sensor_history = cur.fetchall()

    # Pragovi za bojanje
    cur.execute("""
        SELECT temp_low, temp_high
        FROM settings
        WHERE id = 1
    """)
    thresholds = cur.fetchone()

    cur.close()
    con.close()

    return render_template(
        "sensor_history_fragment.html",
        sensor_history=sensor_history,
        thresholds=thresholds
    )

@app.route("/alarm-history-fragment")
def alarm_history_fragment():
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT timestamp, temperature, humidity, alarm_type
        FROM alarm_log
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    alarm_history = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        "alarm_history_fragment.html",
        alarm_history=alarm_history
    )
# =========================================
#          ESP32 ACTUATOR API
# =========================================
@app.route("/api/actuator", methods=["POST"])
def api_actuator():
    d = request.json

    con = db()
    with con.cursor() as cur:
        cur.execute("""
            INSERT INTO actuator_log
            (device, state, temperature, humidity)
            VALUES (%s, %s, %s, %s)
        """, (
            d["device"],
            d["state"],
            d["temperature"],
            d["humidity"]
        ))
        con.commit()
    con.close()

    return jsonify({"status": "logged"})

@app.route("/api/alarm", methods=["POST"])
def api_alarm():
    data = request.json

    con = db()
    with con.cursor() as cur:
        cur.execute("""
            INSERT INTO alarm_log
            (temperature, humidity, alarm_type)
            VALUES (%s, %s, %s)
        """, (
            data["temperature"],
            data["humidity"],
            data["alarm_type"]
        ))
        con.commit()
    con.close()

    return jsonify({"status": "alarm logged"})

# =========================================
#               ALARM UPDATE
# =========================================
@app.route("/update-settings", methods=["POST"])
def update_thresholds():
    temp_low  = float(request.form["temp_low"])
    temp_high = float(request.form["temp_high"])
    hum_low   = float(request.form["hum_low"])
    hum_high  = float(request.form["hum_high"])

    con = db()
    with con.cursor() as cur:
        cur.execute("""
            UPDATE settings
            SET
                temp_low  = %s,
                temp_high = %s,
                hum_low   = %s,
                hum_high  = %s
            WHERE id = 1
        """, (temp_low, temp_high, hum_low, hum_high))
        con.commit()
    con.close()
    return redirect(url_for("dashboard"))

# =========================================
#               KONTROLA
# =========================================
@app.route("/manual-control", methods=["POST"])
def manual_control():
    fan = 1 if request.form.get("fan_manual") == "1" else 0
    heater = 1 if request.form.get("heater_manual") == "1" else 0

    con = db()
    with con.cursor() as cur:
        cur.execute("""
            UPDATE settings
            SET fan_manual=%s,
                heater_manual=%s,
                auto_control=0
            WHERE id=1
        """, (fan, heater))
        con.commit()
    con.close()

    return redirect(url_for("dashboard"))

@app.route("/api/control", methods=["GET"])
def api_control():
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            SELECT temp_low, temp_high, hum_low, hum_high,
                   auto_control, fan_manual, heater_manual
            FROM settings WHERE id=1
        """)
        row = cur.fetchone()
    con.close()
    return jsonify(row)

@app.route("/auto-control", methods=["POST"])
def auto_control():
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            UPDATE settings
            SET auto_control = 1
            WHERE id = 1
        """)
        con.commit()
    con.close()
    return redirect(url_for("dashboard"))
# =========================================
#               RUN SERVER
# =========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

@app.before_request
def require_login():
    # dopuštene rute bez prijave
    allowed_routes = ["/login"]
    
    if request.path.startswith("/static"):
        return
    
    if request.path in allowed_routes:
        return

    if session.get("user_id") is None:
        return redirect(url_for("login"))