# Brevet RESTful API
# Author: Andrew Werderman

import arrow
import flask
from flask import (
	Flask, redirect, url_for, request, render_template, Response, jsonify 
	)
from flask_restful import Resource, Api
from pymongo import MongoClient
from itsdangerous import (TimedJSONWebSignatureSerializer
							as Serializer, BadSignature,
							SignatureExpired)
from passlib.apps import custom_app_context as pwd_context


# Instantiate the app
app = Flask(__name__)
api = Api(app=app, catch_all_404s=True)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'

# Create Mongo instance
client = MongoClient('mongodb://mongo:27017/')
brevetdb = client['brevetdb'] 
usersdb = client['usersdb']

class Home(Resource):
	def get(self):
		return ''


class Register(Resource):
	def __init__(self):
		self.collection = usersdb['UserInfo']

	def post(self):
		'''
		to verify a user, look up username and hashed password in db, 
		verify the inputted password against the stored hashed password in the db

		curl -d "username=jeffrey&password=admin" localhost:5001/api/register
		'''
		username = request.form.get('username')
		password = request.form.get('password')

		# Handle username is already in use. (True: return appropriate message)
		if (self.collection.find_one({'username': username})):
			# Bad Request is returned
			return {'Error': '{} already in use.'.format(username)}, 400

		if ((username == None) or (username == '')) or ((password == None) or (password == '')):
			return {'Error': 'Please provide a username and password.'}, 400

		# Hash password
		hVal = pwd_context.encrypt(password)

		# Insert: {'username': username, 'password': hVal} into self.collection
		self.collection.insert_one({'username': username, 'password': hVal})

		# get ObjectId()
		user = self.collection.find_one({'username': username})
		info = {'Location': str(user['_id']), 'username': username, 'DateAdded': arrow.now().for_json()}
		
		response = flask.jsonify(info)
		response.status_code = 201
		return response


class Token(Resource):
	def __init__(self):
		self.collection = usersdb['UserInfo']

	def get(self):
		'''
		curl -u "jeffrey:admin" localhost:5001/api/token
		curl -u "<tokenstring>:none" localhost:5001/api/token
		'''

		username = request.form.get('username')
		password = request.form.get('password')

		if not (self.collection.find_one({'username': username})):
			return {'Error': 'User does not exist.'}, 401

		if not (verify_password(username, password))

		return 'token request received'

	def generate_auth_token(self, expiration=600):
		s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
		# pass index of user
		return s.dumps({'id': 1})

	def verify_auth_token(token):
		s = Serializer('test1234@#$')
		try:
			data = s.loads(token)
		except SignatureExpired:
			return None    # valid token, but expired
		except BadSignature:
			return None    # invalid token
		return "Success"

	def verify_password(username, password):
		'''
		inputs: username and password
		output: True for correct password, else False

		Check inputted password against saved hashed password, and 
		return True or False depending on whether the password is correct or not.
		'''
		user = self.collection.find_one({'username': username})
		hashVal = user['password']
		return pwd_context.verify(password, hashVal)


# Can only be accessed with the correct token.
class ListBrevet(Resource):
	def __init__(self):
		#******** Change to be user specific *************
		self.collection = brevetdb['brevet'] 

	def get(self, items='listAll', resultFormat='json'):
		'''
		  Input:
			items - which items to list: 'listAll' (default), 'listOpenOnly', 'listCloseOnly'
			resultFormat - requested format of response
		  Output:
			array of brevet control open and/or close times
			resultFormat='json' gives an array of dictionaries
			resultFormat='csv' gives an array of arrays
		'''
		top = request.args.get('top')

		# Handle empty brevet
		if self.collection.count() == 0:
			return jsonify({'Error': 'Empty Brevet'})

		# Handle unexpected query.
		if (items not in ['listAll', 'listOpenOnly', 'listCloseOnly']) or (resultFormat not in ['json', 'csv']):
			return jsonify({'Error': 'Invalid Query'})

		# Handle whether top is set or not
		if (top == None) or (top == ''):
			controls = self.collection.find()
		else:
			# Handle invalid input for top
			try:
				limit = int(top)
				if(limit <= 0):
					return jsonify({'Error': 'Invalid number of top elements'})
				else:
					controls = self.collection.find(limit=limit) # limits the number of results in find()
			except ValueError:
				return jsonify({'Error': 'Value Error for top'})

		# Populate results with queried output
		if (items == 'listAll'):
			result = ListBrevet.formatResponse(controls, resultFormat, 'open_time', 'close_time')
		elif (items == 'listOpenOnly'):
			result = ListBrevet.formatResponse(controls, resultFormat, 'open_time')
		else: # resultFormat == 'listCloseOnly'
			result = ListBrevet.formatResponse(controls, resultFormat, 'close_time')
		
		if (resultFormat == 'csv'):
			return Response(result, mimetype='text/csv')

		return jsonify(result)

	def formatResponse(brevet, resultFormat, *args):
		'''
		  Input: 
		  	brevet - the db brevet collection instance
		  	resultFormat - the desired output format of the query -- 'json' or 'csv'
		  	*args - the key values of the desired control information -- 'open_time'/'close_time'/etc.
		  Output: 
		  	json - an array of dictionaries of control info
		  	csv - A string formatted to csv
		  Helper function to format the queried resultFormat of controls.
		'''
		json = []
		csv = ''
		if (resultFormat == 'json'):
			for ctrl in brevet:
				jsonDict = {key:ctrl[key] for key in args}
				json.append(jsonDict)
		else:
			csv += str(args[0])
			if (len(args) > 1):
				csv += ', {}\n'.format(args[1])
				for ctrl in brevet:
					csv += '{}, {}\n'.format(ctrl[args[0]], ctrl[args[1]])
			else:
				csv += '\n'
				for ctrl in brevet:
					csv += '{}\n'.format(ctrl[args[0]])

		output = {'json': json, 'csv': csv}
		return output[resultFormat]


# Create routes
api.add_resource(Home, '/')
api.add_resource(Token, '/api/token')
api.add_resource(Register, '/api/register')
api.add_resource(ListBrevet, '/api/<items>/<resultFormat>')

# Run the application
if __name__ == '__main__':
    app.run(
    	host='0.0.0.0', 
    	port=80, 
    	debug=True,
    	extra_files = './templates/response.html')
