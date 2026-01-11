from flask import Flask, render_template, request, redirect, flash, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'radio_app_secret_key'

# ==========================================
# 🔐 セキュリティ設定 (Basic認証)
# ==========================================
# ★ここで好きなIDとパスワードを設定してください
BASIC_AUTH_USER = 'zundarashi'
BASIC_AUTH_PASS = '3351'

def check_auth(username, password):
    """入力されたID/PASSが正しいかチェックする"""
    return username == BASIC_AUTH_USER and password == BASIC_AUTH_PASS

def authenticate():
    """認証画面を出す（間違った時のメッセージ）"""
    return Response(
    'このサイトを見るにはログインが必要です。\n'
    '正しいIDとパスワードを入力してください。', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.before_request
def require_auth():
    """すべてのページアクセス前にここを通す"""
    # 認証情報を取得
    auth = request.authorization
    # 情報がない、または間違っている場合は認証画面を出す
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
# ==========================================


# データベース設定
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'radio.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 番組設定
PROGRAMS = {
    "hybrid": {"name": "ハイブリッドモーニング", "color": "#FFD700"},
    "mimikoi": {"name": "耳恋", "color": "#FF6B6B"},
    "baby": {"name": "濱田兄弟のグンナイベイビー", "color": "#4169E1"}
}

# データモデル
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.String(50))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    type = db.Column(db.String(10))
    name = db.Column(db.String(100))
    title = db.Column(db.String(100))
    group_names = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)

# --- ページ処理 ---

@app.route('/')
def index():
    return render_template('index.html', programs=PROGRAMS)

@app.route('/program/<program_id>')
def program_page(program_id):
    program_info = PROGRAMS.get(program_id)
    all_posts = Post.query.filter_by(program_id=program_id, is_published=True).order_by(Post.date.desc(), Post.time.asc()).all()

    grouped_posts = []
    current_date = None
    current_entry = {}
    for post in all_posts:
        dt = datetime.strptime(post.date, '%Y-%m-%d')
        weekday = ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]
        if post.date != current_date:
            current_date = post.date
            current_entry = {"date": post.date, "weekday": weekday, "entries": []}
            grouped_posts.append(current_entry)
        
        entry_data = {
            "type": post.type, "time": post.time, "name": post.name,
            "title": post.title, "names": post.group_names.split('、') if post.group_names else []
        }
        current_entry["entries"].append(entry_data)

    return render_template('program.html', program=program_info, posts=grouped_posts[:7])

# --- 管理システム ---

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html', programs=PROGRAMS)

@app.route('/admin/<program_id>')
def admin_input(program_id):
    program_info = PROGRAMS.get(program_id)
    drafts = Post.query.filter_by(program_id=program_id, is_published=False).order_by(Post.time.desc()).all()
    history = Post.query.filter_by(program_id=program_id, is_published=True).order_by(Post.date.desc(), Post.time.desc()).limit(30).all()
    return render_template('admin_input.html', program=program_info, program_id=program_id, drafts=drafts, history=history)

@app.route('/admin/add/<program_id>', methods=['POST'])
def add_post(program_id):
    new_post = Post(
        program_id=program_id,
        date=request.form['date'],
        time=request.form['time'],
        type=request.form['type'],
        name=request.form.get('name', ''),
        title=request.form.get('title', ''),
        group_names=request.form.get('group_names', ''),
        is_published=False
    )
    db.session.add(new_post)
    db.session.commit()
    return redirect(url_for('admin_input', program_id=program_id))

@app.route('/admin/publish/<program_id>', methods=['POST'])
def publish_posts(program_id):
    drafts = Post.query.filter_by(program_id=program_id, is_published=False).all()
    for post in drafts:
        post.is_published = True
    db.session.commit()
    flash(f'🚀 {len(drafts)}件のデータをサイトに公開しました！')
    return redirect(url_for('admin_input', program_id=program_id))

@app.route('/delete/<int:id>')
def delete_post(id):
    post = Post.query.get_or_404(id)
    program_id = post.program_id
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('admin_input', program_id=program_id))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_post(id):
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        post.date = request.form['date']
        post.time = request.form['time']
        post.type = request.form['type']
        post.name = request.form.get('name', '')
        post.title = request.form.get('title', '')
        post.group_names = request.form.get('group_names', '')
        db.session.commit()
        flash('✏️ データを修正しました')
        return redirect(url_for('admin_input', program_id=post.program_id))
    
    return render_template('edit.html', programs=PROGRAMS, post=post)

# 検索機能 (今回は削除済みのためルートだけ残してリダイレクトさせるか、完全に消してもOK)
# 今回は完全に削除しました

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, host='0.0.0.0')