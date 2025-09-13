from flask import Flask, render_template, request, redirect, url_for, session
import os
import uuid
import hashlib
from models.json_handler import JSONHandler
from models.course import Course

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# ------------------ Utility Functions ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def has_time_conflict(new_course, current_courses):
    new_slots = new_course.get('time_slots', [])
    for course in current_courses:
        for slot in course.get('time_slots', []):
            if slot in new_slots:
                return True
    return False

# ------------------ Routes ------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']   
        password = request.form['password']

        users = JSONHandler.load_data('data/users.json')
        for user in users:
            if user['email'] == email and user['password'] == hash_password(password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                return redirect(url_for('dashboard'))

        return "ایمیل یا رمز عبور نادرست است."
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        users = JSONHandler.load_data('data/users.json')
        for user in users:
            if user['email'] == email:
                return "کاربری با این ایمیل وجود دارد."

        new_user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "password": hash_password(password),
            "role": role
        }

        users.append(new_user)
        JSONHandler.save_data('data/users.json', users)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/unregister_course/<course_id>', methods=['POST'])
def unregister_course(course_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return "فقط دانشجویان می‌توانند انصراف دهند."

    user_id = session['user_id']
    courses = JSONHandler.load_data('data/courses.json')
    selected_course = next((c for c in courses if c['id'] == course_id), None)

    if not selected_course:
        return "دوره پیدا نشد."

    if user_id not in selected_course.get('enrolled', []):
        return "شما در این دوره ثبت‌نام نکرده‌اید."

    selected_course['enrolled'].remove(user_id)
    JSONHandler.save_data('data/courses.json', courses)

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    name = session.get('user_name')
    role = session.get('user_role')
    user_id = session.get('user_id')

    courses = JSONHandler.load_data('data/courses.json')
    # برای دانشجو: همه دوره‌ها را پاس بده، بعد در template بررسی کن ثبت‌نام شده یا نه
    # برای مدیر: می‌توان همه دوره‌ها یا فقط دوره‌های مدیریتی را نمایش داد
    return render_template(
        'dashboard.html',
        name=name,
        role=role,
        registered_courses=courses,  # همه دوره‌ها
        user_id=user_id
    )


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_role' not in session or session['user_role'] != 'admin':
        return "فقط مدیر سیستم می‌تواند دوره اضافه کند."

    if request.method == 'POST':
        name = request.form['name']
        instructor = request.form['instructor']
        capacity = int(request.form['capacity'])
        content = request.form['content']
        day = request.form['day']
        time = request.form['time']
        time_slots = [(day, time)]

        course_id = str(uuid.uuid4())
        course = Course(course_id, name, instructor, time_slots, capacity, content)

        courses = JSONHandler.load_data('data/courses.json')
        courses.append(course.to_dict())
        JSONHandler.save_data('data/courses.json', courses)

        return redirect(url_for('list_courses'))

    return render_template('add_course.html')

@app.route('/courses')
def list_courses():
    courses = JSONHandler.load_data('data/courses.json')
    return render_template('courses.html', courses=courses)

@app.route('/register_course/<course_id>', methods=['POST'])
def register_course(course_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return "فقط دانشجویان می‌توانند ثبت‌نام کنند."

    user_id = session['user_id']
    courses = JSONHandler.load_data('data/courses.json')
    selected_course = next((c for c in courses if c['id'] == course_id), None)

    if not selected_course:
        return "دوره پیدا نشد."
    if user_id in selected_course.get('enrolled', []):
        return "قبلاً ثبت‌نام کرده‌اید."
    if len(selected_course.get('enrolled', [])) >= selected_course['capacity']:
        return "ظرفیت دوره تکمیل شده است."

    student_courses = [c for c in courses if user_id in c.get('enrolled', [])]
    if has_time_conflict(selected_course, student_courses):
        return "تداخل زمانی با دوره‌های قبلی دارید!"

    selected_course.setdefault('enrolled', []).append(user_id)
    JSONHandler.save_data('data/courses.json', courses)

    return redirect(url_for('list_courses'))

@app.route('/edit_course/<course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return "دسترسی غیرمجاز."

    courses = JSONHandler.load_data('data/courses.json')
    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        return "دوره پیدا نشد."

    if request.method == 'POST':
        course['name'] = request.form['name']
        course['instructor'] = request.form['instructor']
        course['capacity'] = int(request.form['capacity'])
        course['content'] = request.form['content']
        course['time_slots'] = [(request.form['day'], request.form['time'])]

        JSONHandler.save_data('data/courses.json', courses)
        return redirect(url_for('list_courses'))

    return render_template('edit_course.html', course=course)

@app.route('/delete_course/<course_id>', methods=['POST'])
def delete_course(course_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return "دسترسی غیرمجاز."

    courses = JSONHandler.load_data('data/courses.json')
    courses = [c for c in courses if c['id'] != course_id]
    JSONHandler.save_data('data/courses.json', courses)

    return redirect(url_for('list_courses'))

@app.route('/payment_result/<course_id>/<status>', methods=['POST'])
def payment_result(course_id, status):
    if 'user_id' not in session or session['user_role'] != 'student':
        return "فقط دانشجویان می‌توانند پرداخت کنند."

    courses = JSONHandler.load_data('data/courses.json')
    selected_course = next((c for c in courses if c['id'] == course_id), None)
    if not selected_course:
        return "دوره پیدا نشد."

    user_id = session['user_id']

    if status == 'success':
        if user_id in selected_course.get('enrolled', []):
            return "شما قبلاً در این دوره ثبت‌نام کرده‌اید."
        if len(selected_course.get('enrolled', [])) >= selected_course['capacity']:
            return "ظرفیت دوره تکمیل شده است."
        student_courses = [c for c in courses if user_id in c.get('enrolled', [])]
        if has_time_conflict(selected_course, student_courses):
            return "❌ تداخل زمانی با دروس قبلی دارید!"
        selected_course.setdefault('enrolled', []).append(user_id)
        JSONHandler.save_data('data/courses.json', courses)
        return f"✅ پرداخت موفق بود! شما در دوره {selected_course['name']} ثبت‌نام شدید."
    else:
        return "❌ پرداخت ناموفق بود. لطفاً دوباره تلاش کنید."
    
@app.route('/checkout/<course_id>', methods=['GET', 'POST'])
def checkout(course_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return "فقط دانشجویان می‌توانند پرداخت کنند."

    courses = JSONHandler.load_data('data/courses.json')
    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        return "دوره پیدا نشد."

    user_id = session['user_id']

    if request.method == 'POST':
        # شبیه‌سازی پرداخت موفق
        if user_id not in course.get('enrolled', []):
            course.setdefault('enrolled', []).append(user_id)
            JSONHandler.save_data('data/courses.json', courses)
        return redirect(url_for('dashboard'))

    # GET نمایش اطلاعات دوره قبل از پرداخت
    return render_template('checkout.html', course=course)



@app.route('/exams/<course_id>')
def list_exams(course_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return "فقط دانشجویان می‌توانند آزمون‌ها را ببینند."

    exams = JSONHandler.load_data('data/exams.json')
    course_exams = [e for e in exams if e['course_id'] == course_id]

    return render_template('exams.html', exams=course_exams)

@app.route('/add_exam', methods=['GET', 'POST'])
def add_exam():
    if 'user_role' not in session or session['user_role'] != 'admin':
        return "فقط مدیر سیستم می‌تواند آزمون اضافه کند."

    courses = JSONHandler.load_data('data/courses.json')

    if request.method == 'POST':
        course_id = request.form['course_id']
        title = request.form['title']
        
        questions = []
        for i in range(1, 6):  # مثلا ۵ سوال
            q_text = request.form.get(f'q{i}')
            q_options = request.form.get(f'options{i}')  # مثلا "گزینه1,گزینه2,گزینه3,گزینه4"
            q_answer = request.form.get(f'answer{i}')
            if q_text and q_options and q_answer:
                questions.append({
                    "question": q_text,
                    "options": [opt.strip() for opt in q_options.split(',')],
                    "answer": q_answer
                })

        exams = JSONHandler.load_data('data/exams.json')
        new_exam = {
            "id": str(uuid.uuid4()),
            "course_id": course_id,
            "title": title,
            "questions": questions
        }
        exams.append(new_exam)
        JSONHandler.save_data('data/exams.json', exams)

        return redirect(url_for('dashboard'))

    return render_template('add_exam.html', courses=courses)

@app.route('/take_exam/<exam_id>', methods=['GET', 'POST'])
def take_exam(exam_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return "فقط دانشجویان می‌توانند آزمون دهند."

    exams = JSONHandler.load_data('data/exams.json')
    exam = next((e for e in exams if e['id'] == exam_id), None)
    if not exam:
        return "آزمون پیدا نشد."

    if request.method == 'POST':
        score = 0
        for i, q in enumerate(exam['questions']):
            selected = request.form.get(f"q{i}")
            if selected == q['answer']:
                score += 1
        total = len(exam['questions'])
        return f"امتیاز شما: {score}/{total}"   

    return render_template('take_exam.html', exam=exam)

# ------------------ Run App ------------------
if __name__ == '__main__':
    app.run(debug=True)
