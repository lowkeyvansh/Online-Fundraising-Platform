from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import stripe

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fundraising_platform.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Stripe API keys
stripe.api_key = 'your_stripe_secret_key'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    campaigns = db.relationship('Campaign', backref='creator', lazy=True)

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    goal_amount = db.Column(db.Float, nullable=False)
    amount_raised = db.Column(db.Float, default=0.0)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    campaigns = Campaign.query.all()
    return render_template('index.html', campaigns=campaigns)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/campaign/new', methods=['GET', 'POST'])
@login_required
def new_campaign():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        goal_amount = request.form['goal_amount']
        new_campaign = Campaign(title=title, description=description, goal_amount=goal_amount, creator_id=current_user.id)
        db.session.add(new_campaign)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_campaign.html')

@app.route('/campaign/<int:campaign_id>', methods=['GET', 'POST'])
def campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if request.method == 'POST':
        amount = float(request.form['amount'])
        stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency='usd',
            payment_method_types=['card'],
        )
        donation = Donation(amount=amount, campaign_id=campaign.id, user_id=current_user.id)
        campaign.amount_raised += amount
        db.session.add(donation)
        db.session.commit()
        return jsonify({'status': 'success'})
    return render_template('campaign_detail.html', campaign=campaign)

@app.route('/campaign/<int:campaign_id>/update', methods=['POST'])
@login_required
def update_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if request.form['title']:
        campaign.title = request.form['title']
    if request.form['description']:
        campaign.description = request.form['description']
    if request.form['goal_amount']:
        campaign.goal_amount = request.form['goal_amount']
    db.session.commit()
    return redirect(url_for('campaign_detail', campaign_id=campaign.id))

@app.route('/admin')
@login_required
def admin_dashboard():
    users = User.query.all()
    campaigns = Campaign.query.all()
    return render_template('admin_dashboard.html', users=users, campaigns=campaigns)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
