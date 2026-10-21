from flask import Flask, render_template, redirect, request, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    from_time = db.Column(db.String(5), nullable=True)
    to_time = db.Column(db.String(5), nullable=True)
    reminder_time = db.Column(db.DateTime, nullable=True)


@app.context_processor
def inject_time():
    return {"now": datetime.now()}


def _get_sorted_tasks(sort_key: str):
    if sort_key == "az":
        return Task.query.order_by(Task.title.asc()).all()
    
    if sort_key == "za":
        return Task.query.order_by(Task.title.desc()).all()
    
    return Task.query.order_by(
        Task.reminder_time.is_(None),
        Task.reminder_time.asc(),
        Task.title.asc()
    ).all()


@app.route("/")
def index():
    sort = request.args.get("sort", "date")
    tasks = _get_sorted_tasks(sort)
    
    now = datetime.now()
    thirty_min_later = now + timedelta(minutes=30)
    upcoming_tasks = Task.query.filter(
        Task.reminder_time.isnot(None),
        Task.reminder_time > now,
        Task.reminder_time <= thirty_min_later,
        Task.completed == False
    ).order_by(Task.reminder_time.asc()).all()
    
    return render_template("index.html", tasks=tasks, upcoming_tasks=upcoming_tasks, sort=sort)


@app.route("/edit/<int:id>")
def edit(id):
    task = Task.query.get_or_404(id)
    sort = request.args.get("sort", "date")
    tasks = _get_sorted_tasks(sort)
    
    now = datetime.now()
    thirty_min_later = now + timedelta(minutes=30)
    upcoming_tasks = Task.query.filter(
        Task.reminder_time.isnot(None),
        Task.reminder_time > now,
        Task.reminder_time <= thirty_min_later,
        Task.completed == False
    ).order_by(Task.reminder_time.asc()).all()
    
    return render_template("index.html", tasks=tasks, edit_task=task, upcoming_tasks=upcoming_tasks, sort=sort)


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    
    if not title:
        return redirect(url_for("index"))
    
    from_time = request.form.get("from_time") or None
    to_time = request.form.get("to_time") or None
    reminder_raw = request.form.get("reminder_time") or None
    
    reminder_time = None
    if reminder_raw:
        try:
            reminder_time = datetime.strptime(reminder_raw, "%Y-%m-%dT%H:%M")
        except ValueError:
            reminder_time = None
    
    new_task = Task(
        title=title,
        from_time=from_time,
        to_time=to_time,
        reminder_time=reminder_time,
    )
    db.session.add(new_task)
    db.session.commit()
    
    return redirect(url_for("index"))


@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    task = Task.query.get_or_404(id)
    
    task.title = request.form.get("title")
    task.from_time = request.form.get("from_time") or None
    task.to_time = request.form.get("to_time") or None
    
    reminder_raw = request.form.get("reminder_time") or None
    if reminder_raw:
        try:
            task.reminder_time = datetime.strptime(reminder_raw, "%Y-%m-%dT%H:%M")
        except ValueError:
            task.reminder_time = None
    else:
        task.reminder_time = None
    
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:id>")
def toggle(id):
    task = Task.query.get_or_404(id)
    task.completed = not task.completed
    db.session.commit()
    
    sort = request.args.get("sort", "date")
    return redirect(url_for("index", sort=sort))


@app.route("/delete/<int:id>")
def delete(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/api/tasks/<date>")
def get_tasks_by_date(date):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        start_of_day = datetime.combine(date_obj, datetime.min.time())
        end_of_day = datetime.combine(date_obj, datetime.max.time())
        
        tasks = Task.query.filter(
            Task.reminder_time >= start_of_day,
            Task.reminder_time <= end_of_day
        ).order_by(Task.reminder_time.asc()).all()
        
        tasks_data = []
        for task in tasks:
            if task.reminder_time:
                formatted_time = task.reminder_time.strftime("%I:%M %p")
            else:
                formatted_time = None
            
            tasks_data.append({
                "id": task.id,
                "title": task.title,
                "completed": task.completed,
                "from_time": task.from_time,
                "to_time": task.to_time,
                "reminder_time": formatted_time
            })
        
        return jsonify(tasks_data)
    
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400


if __name__ == "__main__":
    app.run(debug=True)
