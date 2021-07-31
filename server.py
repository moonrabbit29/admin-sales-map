from typing import Sequence
from flask import Flask,render_template,request,jsonify
from flask_cors import CORS,cross_origin
from datetime import datetime
from ga import GA


app = Flask(__name__, template_folder='public/templates')
cors = CORS(app)

app.config['url'] = ''
app.config['JSON_SORT_KEYS'] = False

@app.route('/',methods=['GET'])
def index():
   if request.method == 'GET' : 
      return render_template("index.html")

@app.route('/getroute',methods=['POST'])
@cross_origin(origin='*')
def getroute():
   data = request.get_json()
   print(data["locations"])
   GAObject = GA(data['locations'])
   bestGuess = GAObject.GetFastestRoad()
   visitingSequence = dict()
   for b in bestGuess : 
      visitingSequence[b] = data['locations'][b]
   print(visitingSequence)
   return visitingSequence