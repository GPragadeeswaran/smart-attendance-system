from flask import Flask, render_template, request, redirect, flash, url_for
import psycopg2
from psycopg2.errors import  UniqueViolation
from datetime import date

app = Flask(__name__)

# DATABASE CONNECTION (same as before)
conn = psycopg2.connect(
    host="localhost",
    database="smart_attendance",
    user="postgres",
    password="postgres"
)

@app.route("/", methods=["GET", "POST"])
def register():
    cursor = conn.cursor()  # ✅ cursor per request
    try:
        if request.method == "POST":

            full_name = request.form["full_name"]
            student_id = request.form["student_id"]
            email = request.form["email"]
            phone = request.form["phone"]
            address = request.form["address"]
            course = request.form["course"]

            # GET DATE PARTS
            day = int(request.form["day"])
            month = int(request.form["month"])
            year = int(request.form["year"])

            resume_file = request.files.get("resume")
            resume_data = resume_file.read() if resume_file else None

            # COMBINE INTO DATE
            dob = date(year, month, day)

            query = """
            INSERT INTO students
            (full_name, date_of_birth, student_id, email, phone_number, address, course, resume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                full_name,
                dob,
                student_id,
                email,
                phone,
                address,
                course,
                psycopg2.Binary(resume_data) if resume_data else None
            ))

            conn.commit()  # ✅ commit on success

            return redirect(url_for("register"))  # ✅ correct redirect

    except Exception as e:
        conn.rollback()  # ✅ rollback on failure
        print("Database error:", e)
        return "Registration failed", 500

    finally:
        cursor.close()  # ✅ always close cursor

    return render_template("index.html")


# student list
@app.route("/studentslist")
def studentslist():
    cursor = conn.cursor()

    try:
        query = """
        SELECT full_name, student_id, course, email
        FROM students
        ORDER BY full_name
        """
        cursor.execute(query)
        students = cursor.fetchall()

    except Exception as e:
        print("Error fetching students:", e)
        students = []

    finally:
        cursor.close()

    return render_template("index2.html", students=students)


# attendance

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    cursor = conn.cursor()
    try:
        if request.method == "POST":

            student_id = request.form["student_id"].strip()
            attendance_date = request.form["attendance_date"]
            check_in = request.form["check_in"]
            check_out = request.form.get("check_out") or None

            # Validate student ID (numbers only)
            if not student_id.isdigit():
                return "Invalid Student ID", 400

            # Check student exists
            cursor.execute(
                "SELECT 1 FROM students WHERE student_id = %s",
                (student_id,)
            )
            if cursor.fetchone() is None:
                return "Student ID does not exist", 400

            # Insert attendance
            cursor.execute(
                """
                INSERT INTO attendance
                (student_id, attendance_date, check_in, check_out)
                VALUES (%s, %s, %s, %s)
                """,
                (student_id, attendance_date, check_in, check_out)
            )

            conn.commit()
            return "Attendance saved successfully", 200

    except UniqueViolation:
        conn.rollback()
        return "Attendance already marked for this date", 400

    except Exception as e:
        conn.rollback()
        print("Attendance error:", e)
        return "Attendance failed", 500

    finally:
        cursor.close()

    return render_template("index1.html")


# delete btn

@app.route("/delete-students", methods=["POST"])
def delete_students():
    cursor = conn.cursor()
    try:
        data = request.get_json()
        student_ids = data.get("student_ids", []) #student_ids = list(map(int, data.get("student_ids", [])))

        if not student_ids:
            return {"success": False, "message": "No students selected"}

        # DELETE QUERY (IN clause)
        query = """
        DELETE FROM students
        WHERE student_id = ANY(%s)
        """

        cursor.execute(query, (student_ids,))
        conn.commit()

        return {"success": True}

    except Exception as e:
        conn.rollback()
        print("Delete error:", e)
        return {"success": False}, 500

    finally:
        cursor.close()



@app.route("/attendance-home")
def attendance_home():
    cursor = conn.cursor()
    try:
        query = """
        SELECT 
            a.student_id,
            s.full_name,
            a.attendance_date,
            a.check_in,
            a.check_out
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        ORDER BY a.attendance_date DESC
        """
        cursor.execute(query)
        attendance = cursor.fetchall()

    except Exception as e:
        print("Error fetching attendance:", e)
        attendance = []

    finally:
        cursor.close()

    return render_template("attendance_home.html", attendance=attendance)



if __name__ == "__main__":
    app.run(debug=True)
