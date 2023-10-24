from flask import Flask, request, render_template
import redis

app = Flask(__name__)

# postgresql://username:password@host:port/database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hello_flask:hello_flask@db:5432/hello_flask_dev'

from models import db, UserFavs

db.init_app(app)
with app.app_context():
    # Щоб створити/використати базу даних, згадану в URL
    db.create_all()
    db.session.commit()

red = redis.Redis(host='redis', port=6379, db=0)

@app.route("/")
def main():
    return render_template('index.html')

@app.route("/save", methods=['POST'])
def save():
    username = str(request.form['username']).lower()
    place = str(request.form['place']).lower()
    food = str(request.form['food']).lower()

    # перевірка, чи дані імені користувача вже існують у redis
    if red.hgetall(username).keys():
        print("hget username:", red.hgetall(username))
        # повернути повідомлення до шаблону, повідомляючи, що користувач уже існує (з redis)
        return render_template('index.html', user_exists=1, msg='(From Redis)', username=username, place=red.hget(username,"place").decode('utf-8'), food=red.hget(username,"food").decode('utf-8'))

    # якщо не в redis, перевірити в базі даних
    elif len(list(red.hgetall(username)))==0:
        record =  UserFavs.query.filter_by(username=username).first()
        print("Records fecthed from db:", record)
        
        if record:
            red.hset(username, "place", place)
            red.hset(username, "food", food)
            # повернути повідомлення до шаблону, повідомляючи, що користувач уже існує (з бази даних)
            return render_template('index.html', user_exists=1, msg='(From DataBase)', username=username, place=record.place, food=record.food)

    # якщо дані імені користувача ніде не існують, створити новий запис у базі даних і також зберегти його в Redis
    # створити новий запис у базі даних
    new_record = UserFavs(username=username, place=place, food=food)
    db.session.add(new_record)
    db.session.commit()

    # зберегти у Redis також
    red.hset(username, "place", place)
    red.hset(username, "food", food)

    # перехресна перевірка успішності вставки запису в базу даних
    record =  UserFavs.query.filter_by(username=username).first()
    print("Records fetched from db after insert:", record)

    # перехресна перевірка успішності вставки в redis
    print("key-values from redis after insert:", red.hgetall(username))

    # повернути повідомлення про успішне збереження
    return render_template('index.html', saved=1, username=username, place=red.hget(username, "place").decode('utf-8'), food=red.hget(username, "food").decode('utf-8'))

@app.route("/keys", methods=['GET'])
def keys():
	records = UserFavs.query.all()
	names = []
	for record in records:
		names.append(record.username)
	return render_template('index.html', keys=1, usernames=names)


@app.route("/get", methods=['POST'])
def get():
	username = request.form['username']
	print("Username:", username)
	user_data = red.hgetall(username)
	print("GET Redis:", user_data)

	if not user_data:
		record = UserFavs.query.filter_by(username=username).first()
		print("GET Record:", record)
		if not record:
			print("No data in redis or db")
			return render_template('index.html', no_record=1, msg=f"Record not yet defined for {username}")
		red.hset(username, "place", record.place)
		red.hset(username, "food", record.food)
		return render_template('index.html', get=1, msg="(From DataBase)",username=username, place=record.place, food=record.food)
	return render_template('index.html',get=1, msg="(From Redis)", username=username, place=user_data[b'place'].decode('utf-8'), food=user_data[b'food'].decode('utf-8'))