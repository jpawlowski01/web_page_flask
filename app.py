from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from celery import Celery

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shopping_list.db'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['result_backend'] = 'redis://localhost:6379/0'  

db = SQLAlchemy(app)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
celery.conf.broker_connection_retry_on_startup = True  

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date_added = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return '<Product %r>' % self.id

with app.app_context():
    db.create_all()

@celery.task
def add_product_to_db(name):
    new_product = Product(name=name)
    db.session.add(new_product)
    db.session.commit()

@app.route('/', methods=['POST', 'GET'])
def shopping_list():
    if request.method == 'POST':
        product_name = request.form['name']
        new_product = Product(name=product_name)
        db.session.add(new_product)
        db.session.commit()
        return redirect('/')
    else:
        products = Product.query.order_by(Product.date_added).all()
        return render_template('index.html', products=products)

@app.route('/async', methods=['POST', 'GET'])
def async_shopping_list():
    if request.method == 'POST':
        product_name = request.form['name'] 
        add_product_to_db.delay(product_name)
        return redirect('/async')
    else:
        products = Product.query.order_by(Product.date_added).all()
        return render_template('async_index.html', products=products)

@app.route('/delete/<int:id>')
def delete_product(id):
    product_to_delete = Product.query.get_or_404(id)

    try:
        db.session.delete(product_to_delete)
        db.session.commit()
        return redirect(request.referrer)
    except:
        return 'Nie udało się usunąć produktu'

if __name__ == "__main__":
    app.run(debug=True)
