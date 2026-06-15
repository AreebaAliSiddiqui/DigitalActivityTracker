from flask import Flask, request, jsonify, send_from_directory, send_file
import os
from flask_cors import CORS
from db import get_connection, list_installed_drivers
from datetime import datetime
import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins="*")

# Disable Jinja2 delimiters so {{ }} in JavaScript never conflicts
app.jinja_env.variable_start_string = '[[['
app.jinja_env.variable_end_string   = ']]]'
app.jinja_env.block_start_string    = '[%'
app.jinja_env.block_end_string      = '%]'


# ── Datetime helper ───────────────────────────────────────────────────────────
def parse_dt(raw):
    if not raw:
        return None
    raw = raw.strip().replace("Z", "").replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised datetime format: '{raw}'")


def db_error(e):
    logger.error(traceback.format_exc())
    return jsonify({"error": str(e), "type": type(e).__name__}), 500


# ── Health ────────────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"status": "ok", "drivers": list_installed_drivers()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/favicon.ico")
def favicon():
    return "", 204  # No content — silences the 404

@app.route("/")
def home():
    # Serves the HTML file sitting right next to app.py
    html_path = os.path.join(os.path.dirname(__file__), "ProjectDashboard.html")
    return send_file(html_path, mimetype="text/html")


# ══════════════════════════════════════════════════════════════════════════════
#  USERS  (full CRUD)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/users", methods=["GET"])
def get_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                u.UserID,
                u.FullName,
                u.Email,
                u.Age,
                u.City,
                u.JoinDate,
                COALESCE(u.DailyGoalMin, 120) AS DailyGoalMin,
                COUNT(s.SessionID) AS SessionCount,
                COALESCE(SUM(s.DurationMinutes), 0) AS TotalMinutes,
                COALESCE(
                    SUM(
                        CASE
                            WHEN CAST(s.StartTime AS DATE) = CAST(GETDATE() AS DATE)
                            THEN s.DurationMinutes
                            ELSE 0
                        END
                    ),
                    0
                ) AS TodayMinutes

            FROM Users u
            LEFT JOIN Sessions s ON u.UserID = s.UserID

            GROUP BY
                u.UserID,
                u.FullName,
                u.Email,
                u.Age,
                u.City,
                u.JoinDate,
                u.DailyGoalMin

            ORDER BY u.UserID
        """)

        rows = cursor.fetchall()
        conn.close()

        return jsonify([{
            "id": r[0],
            "fullName": r[1],
            "email": r[2] or "",
            "age": r[3] or "",
            "city": r[4] or "",
            "createdAt": str(r[5]) if r[5] else "",
            "dailyGoalMin": r[6],
            "sessions": r[7],
            "totalMinutes": r[8],
            "todayMinutes": r[9]
        } for r in rows])

    except Exception as e:
        return db_error(e)

@app.route("/api/users", methods=["POST"])
def add_user():
    try:
        data = request.get_json(silent=True) or {}
        full_name = (data.get("fullName") or "").strip()
        if not full_name:
            return jsonify({"error": "fullName is required"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(MAX(UserID), 0) + 1 FROM Users")
        new_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Users (UserID, FullName, Email, Username, JoinDate, DailyGoalMin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            new_id,
            full_name,
            data.get("email", ""),
            data.get("username", ""),
            datetime.now(),
            data.get("dailyGoalMin", 120)
        ))

        conn.commit()
        conn.close()
        return jsonify({"message": "User created", "userID": new_id}), 201
    except Exception as e:
        return db_error(e)


@app.route("/api/users/<int:uid>", methods=["PUT"])
def update_user(uid):
    try:
        data = request.json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Users
            SET FullName = ?, Email = ?, Username = ?
            WHERE UserID = ?
        """, (data["fullName"], data.get("email", ""), data.get("username", ""), uid))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        conn.commit()
        conn.close()
        return jsonify({"message": "User updated"})
    except Exception as e:
        return db_error(e)


@app.route("/api/users/<int:uid>", methods=["DELETE"])
def delete_user(uid):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Check for linked sessions first
        cursor.execute("SELECT COUNT(*) FROM Sessions WHERE UserID = ?", (uid,))
        count = cursor.fetchone()[0]
        if count > 0:
            conn.close()
            return jsonify({"error": f"Cannot delete: user has {count} session(s). Delete their sessions first."}), 409
        cursor.execute("DELETE FROM Users WHERE UserID = ?", (uid,))
        conn.commit()
        conn.close()
        return jsonify({"message": "User deleted"})
    except Exception as e:
        return db_error(e)


# ── Lookup lists (for dropdowns) ──────────────────────────────────────────────
@app.route("/api/users/next-id")
def next_user_id():
    """Returns what the next auto-assigned UserID will be, for the UI preview."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(UserID), 0) + 1 FROM Users")
        nid = cursor.fetchone()[0]
        conn.close()
        return jsonify({"nextId": nid})
    except Exception as e:
        return db_error(e)


@app.route("/api/users/list")
def users_list():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT UserID, FullName FROM Users ORDER BY FullName")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "name": r[1]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/apps/list")
def apps_list():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT AppID, AppName FROM Apps ORDER BY AppName")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "name": r[1]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/devices/list")
def devices_list():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DeviceID, DeviceName FROM Devices ORDER BY DeviceName")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "name": r[1]} for r in rows])
    except Exception as e:
        return db_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSIONS  (full CRUD)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                s.SessionID,
                u.FullName,
                a.AppName,
                COALESCE(c.CategoryName, 'Unknown') AS CategoryName,
                COALESCE(d.DeviceName,  'N/A')      AS DeviceName,
                s.DurationMinutes,
                s.StartTime,
                s.UserID,
                s.AppID,
                COALESCE(s.DeviceID, 0)             AS DeviceID,
                COALESCE(s.Notes, '')               AS Notes
            FROM Sessions s
            JOIN  Users  u  ON s.UserID    = u.UserID
            JOIN  Apps   a  ON s.AppID     = a.AppID
            LEFT JOIN AppCategory ac ON a.AppID      = ac.AppID
            LEFT JOIN Categories  c  ON ac.CategoryID = c.CategoryID
            LEFT JOIN Devices     d  ON s.DeviceID   = d.DeviceID
            ORDER BY s.StartTime DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{
            "id":       r[0], "user":     r[1], "app":      r[2],
            "category": r[3], "device":   r[4], "duration": r[5],
            "time":     str(r[6]),
            "userID":   r[7], "appID":    r[8], "deviceID": r[9],
            "notes":    r[10]
        } for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/sessions", methods=["POST"])
def add_session():
    try:
        data = request.json
        start = parse_dt(data.get("startTime"))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Sessions (UserID, AppID, DeviceID, StartTime, DurationMinutes, Notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["userID"], data["appID"], data.get("deviceID"),
            start, data["duration"], data.get("notes", "")
        ))
        conn.commit()
        conn.close()
        return jsonify({"message": "Session added"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return db_error(e)


@app.route("/api/sessions/<int:sid>", methods=["PUT"])
def update_session(sid):
    try:
        data = request.json
        start = parse_dt(data.get("startTime"))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Sessions
            SET UserID=?, AppID=?, DeviceID=?, StartTime=?, DurationMinutes=?, Notes=?
            WHERE SessionID=?
        """, (
            data["userID"], data["appID"], data.get("deviceID"),
            start, data["duration"], data.get("notes", ""), sid
        ))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Session not found"}), 404
        conn.commit()
        conn.close()
        return jsonify({"message": "Session updated"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return db_error(e)


@app.route("/api/sessions/<int:sid>", methods=["DELETE"])
def delete_session(sid):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Sessions WHERE SessionID=?", (sid,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Deleted"})
    except Exception as e:
        return db_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/analytics/by-category")
def by_category():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(c.CategoryName,'Unknown'), SUM(s.DurationMinutes)
            FROM Sessions s
            JOIN Apps a ON s.AppID=a.AppID
            LEFT JOIN AppCategory ac ON a.AppID=ac.AppID
            LEFT JOIN Categories c ON ac.CategoryID=c.CategoryID
            GROUP BY c.CategoryName ORDER BY 2 DESC
        """)
        rows = cursor.fetchall(); conn.close()
        return jsonify([{"category": r[0], "minutes": r[1]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/analytics/by-app")
def by_app():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 10 a.AppName, SUM(s.DurationMinutes)
            FROM Sessions s JOIN Apps a ON s.AppID=a.AppID
            GROUP BY a.AppName ORDER BY 2 DESC
        """)
        rows = cursor.fetchall(); conn.close()
        return jsonify([{"app": r[0], "minutes": r[1]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/analytics/by-user")
def by_user():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.FullName, SUM(s.DurationMinutes)
            FROM Sessions s JOIN Users u ON s.UserID=u.UserID
            GROUP BY u.FullName ORDER BY 2 DESC
        """)
        rows = cursor.fetchall(); conn.close()
        return jsonify([{"user": r[0], "minutes": r[1]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/analytics/daily-trend")
def daily_trend():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT CAST(s.StartTime AS DATE), COUNT(*), SUM(s.DurationMinutes)
            FROM Sessions s
            WHERE s.StartTime >= DATEADD(DAY,-30,GETDATE())
            GROUP BY CAST(s.StartTime AS DATE) ORDER BY 1
        """)
        rows = cursor.fetchall(); conn.close()
        return jsonify([{"day": str(r[0]), "sessions": r[1], "minutes": r[2]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/analytics/goal-comparison")
def goal_comparison():
    """Today's usage vs each user's daily goal — FR-05."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.FullName,
                   COALESCE(u.DailyGoalMin, 120) AS GoalMin,
                   COALESCE(SUM(CASE WHEN CAST(s.StartTime AS DATE)=CAST(GETDATE() AS DATE)
                                THEN s.DurationMinutes ELSE 0 END), 0) AS TodayMin
            FROM Users u
            LEFT JOIN Sessions s ON u.UserID=s.UserID
            GROUP BY u.UserID, u.FullName, u.DailyGoalMin
            ORDER BY u.FullName
        """)
        rows = cursor.fetchall(); conn.close()
        return jsonify([{"user": r[0], "goal": r[1], "today": r[2]} for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/analytics/usage-summary")
def usage_summary():
    """Daily / weekly / monthly breakdown per user — FR-04."""
    try:
        period = request.args.get("period", "weekly")
        days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 7)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.FullName,
                   SUM(s.DurationMinutes)  AS TotalMin,
                   COUNT(s.SessionID)      AS Sessions,
                   COUNT(DISTINCT s.AppID) AS UniqueApps
            FROM Sessions s
            JOIN Users u ON s.UserID=u.UserID
            WHERE s.StartTime >= DATEADD(DAY, ?, GETDATE())
            GROUP BY u.UserID, u.FullName
            ORDER BY TotalMin DESC
        """, (-days,))
        rows = cursor.fetchall(); conn.close()
        return jsonify([{
            "user": r[0], "minutes": r[1],
            "sessions": r[2], "uniqueApps": r[3]
        } for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/sessions/filtered")
def sessions_filtered():
    """Filter sessions by date range, app, user, category — FR-06."""
    try:
        user_id  = request.args.get("userID", "")
        app_name = request.args.get("app", "")
        category = request.args.get("category", "")
        date_from= request.args.get("from", "")
        date_to  = request.args.get("to", "")

        sql = """
            SELECT s.SessionID, u.FullName, a.AppName,
                   COALESCE(c.CategoryName,'Unknown') AS Cat,
                   COALESCE(d.DeviceName,'N/A')       AS Dev,
                   s.DurationMinutes, s.StartTime,
                   s.UserID, s.AppID,
                   COALESCE(s.DeviceID,0), COALESCE(s.Notes,'')
            FROM Sessions s
            JOIN Users u ON s.UserID=u.UserID
            JOIN Apps  a ON s.AppID=a.AppID
            LEFT JOIN AppCategory ac ON a.AppID=ac.AppID
            LEFT JOIN Categories  c  ON ac.CategoryID=c.CategoryID
            LEFT JOIN Devices     d  ON s.DeviceID=d.DeviceID
            WHERE 1=1
        """
        params = []
        if user_id:  sql += " AND s.UserID=?";               params.append(int(user_id))
        if app_name: sql += " AND a.AppName LIKE ?";          params.append(f"%{app_name}%")
        if category: sql += " AND c.CategoryName LIKE ?";     params.append(f"%{category}%")
        if date_from:sql += " AND CAST(s.StartTime AS DATE)>=?"; params.append(date_from)
        if date_to:  sql += " AND CAST(s.StartTime AS DATE)<=?"; params.append(date_to)
        sql += " ORDER BY s.StartTime DESC"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall(); conn.close()
        return jsonify([{
            "id": r[0], "user": r[1], "app": r[2], "category": r[3],
            "device": r[4], "duration": r[5], "time": str(r[6]),
            "userID": r[7], "appID": r[8], "deviceID": r[9], "notes": r[10]
        } for r in rows])
    except Exception as e:
        return db_error(e)


@app.route("/api/sessions/export-csv")
def export_csv():
    """Export all sessions to CSV — FR-10."""
    try:
        import csv, io
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.SessionID, u.FullName, a.AppName,
                   COALESCE(c.CategoryName,'Unknown'),
                   COALESCE(d.DeviceName,'N/A'),
                   s.DurationMinutes, s.StartTime,
                   COALESCE(s.Notes,'')
            FROM Sessions s
            JOIN Users u ON s.UserID=u.UserID
            JOIN Apps  a ON s.AppID=a.AppID
            LEFT JOIN AppCategory ac ON a.AppID=ac.AppID
            LEFT JOIN Categories  c  ON ac.CategoryID=c.CategoryID
            LEFT JOIN Devices     d  ON s.DeviceID=d.DeviceID
            ORDER BY s.StartTime DESC
        """)
        rows = cursor.fetchall(); conn.close()
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["SessionID","User","App","Category","Device","DurationMinutes","StartTime","Notes"])
        for r in rows:
            w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], str(r[6]), r[7]])
        from flask import Response
        return Response(
            out.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=sessions_export.csv"}
        )
    except Exception as e:
        return db_error(e)


@app.route("/api/analytics/kpis")
def kpis():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Sessions")
        ts = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(DurationMinutes),0) FROM Sessions")
        tm = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Users")
        tu = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT AppID) FROM Sessions")
        ap = cursor.fetchone()[0]
        conn.close()
        return jsonify({"totalSessions": ts, "totalMinutes": tm, "activeUsers": tu, "appsUsed": ap})
    except Exception as e:
        return db_error(e)


if __name__ == "__main__":
    app.run(debug=True, port=5000)