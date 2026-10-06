from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "trustnova_secret_2026"

DATABASE = "database.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            category TEXT,

            risk_score INTEGER,

            status TEXT,

            result TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            title TEXT,

            message TEXT,

            severity TEXT,

            is_read INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# LOGIN CHECK
# =========================================================

def logged_in():

    return "user_id" in session


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if logged_in():

        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()

        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        email = request.form.get("email", "").strip()

        password = request.form.get("password", "")

        if not name or not email or not password:

            return render_template(
                "signup.html",
                error="Please fill all fields."
            )

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (name, email, password)

                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password)
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "signup.html",
                error="Email already registered."
            )

        conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():

        return redirect(url_for("login"))

    conn = get_db()

    user_id = session["user_id"]

    # Total analyses
    total = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM analyses
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()["total"]


    # High risk cases
    high_risk = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM analyses
        WHERE user_id = ?
        AND risk_score >= 70
        """,
        (user_id,)
    ).fetchone()["total"]


    # Latest Finance score
    finance = conn.execute(
        """
        SELECT risk_score
        FROM analyses
        WHERE user_id = ?
        AND category = 'Finance'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()


    # Latest Cybersecurity score
    cyber = conn.execute(
        """
        SELECT risk_score
        FROM analyses
        WHERE user_id = ?
        AND category = 'Cybersecurity'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()


    # Latest Agriculture score
    agriculture = conn.execute(
        """
        SELECT risk_score
        FROM analyses
        WHERE user_id = ?
        AND category = 'Agriculture'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()


    # Latest overall analysis
    latest = conn.execute(
        """
        SELECT *
        FROM analyses
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()


    conn.close()


    finance_score = (
        finance["risk_score"]
        if finance else 0
    )

    cyber_score = (
        cyber["risk_score"]
        if cyber else 0
    )

    agriculture_score = (
        agriculture["risk_score"]
        if agriculture else 0
    )


    # Calculate overall score
    scores = [
        score for score in
        [
            finance_score,
            cyber_score,
            agriculture_score
        ]
        if score > 0
    ]


    if scores:

        overall_score = round(
            sum(scores) / len(scores)
        )

    else:

        overall_score = 0


    return render_template(
        "dashboard.html",

        total_analyses=total,

        high_risk=high_risk,

        finance_score=finance_score,

        cyber_score=cyber_score,

        agriculture_score=agriculture_score,

        overall_score=overall_score,

        latest=latest
    )
# =========================================================
# FINANCE
# =========================================================

@app.route("/finance")
def finance():

    if not logged_in():

        return redirect(url_for("login"))

    return render_template("finance.html")


# =========================================================
# CYBERSECURITY
# =========================================================

@app.route("/cybersecurity")
def cybersecurity():

    if not logged_in():

        return redirect(url_for("login"))

    return render_template("cybersecurity.html")


# =========================================================
# AGRICULTURE
# =========================================================

@app.route("/agriculture")
def agriculture():

    if not logged_in():

        return redirect(url_for("login"))

    return render_template("agriculture.html")


# =========================================================
# AI ANALYSIS - RISK ENGINE
# =========================================================

@app.route("/analysis", methods=["GET", "POST"])
def analysis():

    if not logged_in():

        return redirect(url_for("login"))


    if request.method == "POST":

        category = request.form.get(
            "category",
            ""
        ).strip()


        # ---------------------------------------------
        # GET RISK FACTORS
        # ---------------------------------------------

        try:

            financial = int(
                request.form.get(
                    "financial",
                    0
                )
            )

            cybersecurity = int(
                request.form.get(
                    "cybersecurity",
                    0
                )
            )

            agriculture = int(
                request.form.get(
                    "agriculture",
                    0
                )
            )

        except ValueError:

            return render_template(
                "analysis.html",
                error="Please enter valid risk values."
            )


        # ---------------------------------------------
        # KEEP SCORES BETWEEN 0 AND 100
        # ---------------------------------------------

        financial = max(
            0,
            min(financial, 100)
        )

        cybersecurity = max(
            0,
            min(cybersecurity, 100)
        )

        agriculture = max(
            0,
            min(agriculture, 100)
        )


        # ---------------------------------------------
        # CALCULATE OVERALL RISK
        # ---------------------------------------------

        if category == "Finance":

            risk_score = financial


        elif category == "Cybersecurity":

            risk_score = cybersecurity


        elif category == "Agriculture":

            risk_score = agriculture


        else:

            risk_score = round(
                (
                    financial
                    + cybersecurity
                    + agriculture
                ) / 3
            )


        # ---------------------------------------------
        # DETERMINE RISK LEVEL
        # ---------------------------------------------

        if risk_score >= 70:

            status = "High Risk"

        elif risk_score >= 40:

            status = "Medium Risk"

        else:

            status = "Low Risk"


        # ---------------------------------------------
        # GENERATE EXPLANATION
        # ---------------------------------------------

        if status == "High Risk":

            result = (
                f"{category} shows a high risk level "
                f"with a score of {risk_score}/100. "
                f"Immediate attention and risk mitigation "
                f"are recommended."
            )


        elif status == "Medium Risk":

            result = (
                f"{category} shows a moderate risk level "
                f"with a score of {risk_score}/100. "
                f"Monitoring and preventive actions "
                f"are recommended."
            )


        else:

            result = (
                f"{category} shows a low risk level "
                f"with a score of {risk_score}/100. "
                f"Current conditions appear relatively stable."
            )


        # ---------------------------------------------
        # SAVE ANALYSIS
        # ---------------------------------------------

        conn = get_db()

        conn.execute(
            """
            INSERT INTO analyses

            (
                user_id,
                category,
                risk_score,
                status,
                result
            )

            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                category,
                risk_score,
                status,
                result
            )
        )


        # ---------------------------------------------
        # AUTOMATIC HIGH-RISK ALERT
        # ---------------------------------------------

        if risk_score >= 70:

            conn.execute(
                """
                INSERT INTO alerts

                (
                    user_id,
                    title,
                    message,
                    severity
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    f"High {category} Risk Detected",
                    (
                        f"TrustNova detected a "
                        f"{risk_score}/100 risk score "
                        f"in {category}. "
                        f"Immediate attention is recommended."
                    ),
                    "High"
                )
            )


        # ---------------------------------------------
        # AUTOMATIC MEDIUM-RISK ALERT
        # ---------------------------------------------

        elif risk_score >= 40:

            conn.execute(
                """
                INSERT INTO alerts

                (
                    user_id,
                    title,
                    message,
                    severity
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    f"Medium {category} Risk Detected",
                    (
                        f"TrustNova detected a "
                        f"{risk_score}/100 risk score "
                        f"in {category}. "
                        f"Continue monitoring the situation."
                    ),
                    "Medium"
                )
            )


        conn.commit()

        conn.close()


        return render_template(

            "analysis.html",

            result=result,

            status=status,

            risk_score=risk_score,

            category=category

        )


    return render_template("analysis.html")


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    if not logged_in():

        return redirect(url_for("login"))

    conn = get_db()

    analyses = conn.execute(
        """
        SELECT *

        FROM analyses

        WHERE user_id = ?

        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "history.html",
        analyses=analyses
    )


# =========================================================
# ALERTS
# =========================================================

@app.route("/alerts")
def alerts():

    if not logged_in():

        return redirect(url_for("login"))

    conn = get_db()

    alerts_data = conn.execute(
        """
        SELECT *

        FROM alerts

        WHERE user_id = ?

        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "alerts.html",
        alerts=alerts_data
    )


# =========================================================
# AI ASSISTANT
# =========================================================

@app.route("/ai-assistant")
def ai_assistant():

    if not logged_in():

        return redirect(url_for("login"))

    return render_template(
        "ai-assistant.html"
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    if not logged_in():

        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        name=session["user_name"],
        email=session["user_email"]
    )


# =========================================================
# SETTINGS
# =========================================================

@app.route("/settings")
def settings():

    if not logged_in():

        return redirect(url_for("login"))

    return render_template(
        "settings.html"
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    print("TrustNova database ready.")

    print("TrustNova server starting...")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )