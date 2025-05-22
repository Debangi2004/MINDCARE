import nltk
nltk.download('popular')
nltk.download('punkt_tab')
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import pickle
import numpy as np
from keras.models import load_model
model = load_model('model.h5')
import json
import random
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('ChatMessage', backref='session', lazy=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import spacy
from spacy.language import Language
from spacy_langdetect import LanguageDetector


# translator pipeline for english to swahili translations

eng_swa_tokenizer = AutoTokenizer.from_pretrained("Rogendo/en-sw")
eng_swa_model = AutoModelForSeq2SeqLM.from_pretrained("Rogendo/en-sw")

eng_swa_translator = pipeline(
    "text2text-generation",
    model = eng_swa_model,
    tokenizer = eng_swa_tokenizer,
)

def translate_text_eng_swa(text):
    translated_text = eng_swa_translator(text, max_length=128, num_beams=5)[0]['generated_text']
    return translated_text


# translator pipeline for swahili to english translations

swa_eng_tokenizer = AutoTokenizer.from_pretrained("Rogendo/sw-en")
swa_eng_model = AutoModelForSeq2SeqLM.from_pretrained("Rogendo/sw-en")

swa_eng_translator = pipeline(
    "text2text-generation",
    model = swa_eng_model,
    tokenizer = swa_eng_tokenizer,
)

def translate_text_swa_eng(text):
  translated_text = swa_eng_translator(text,max_length=128, num_beams=5)[0]['generated_text']
  return translated_text


def get_lang_detector(nlp, name):
    return LanguageDetector()

nlp = spacy.load("en_core_web_sm")

Language.factory("language_detector", func=get_lang_detector)

nlp.add_pipe('language_detector', last=True)





intents = json.loads(open('intents.json').read())
words = pickle.load(open('texts.pkl','rb'))
classes = pickle.load(open('labels.pkl','rb'))
def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def bow(sentence, words, show_details=True):
    sentence_words = clean_up_sentence(sentence)
    bag = [0]*len(words)  
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s: 
                bag[i] = 1
                if show_details:
                    print ("found in bag: %s" % w)
    return(np.array(bag))

def predict_class(sentence, model):
    p = bow(sentence, words,show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list
def getResponse(ints, intents_json):
    if ints: 
        tag = ints[0]['intent']
        list_of_intents = intents_json['intents']
        for i in list_of_intents:
            if i['tag'] == tag:
                result = random.choice(i['responses'])
                break
        return result
    else:
        return "Sorry, I didn't understand that."

def chatbot_response(msg):
    doc = nlp(msg)
    detected_language = doc._.language['language']
    print(f"Detected language chatbot_response:- {detected_language}")
    
    chatbotResponse = "Loading bot response..........."

    if detected_language == "en":
        res = getResponse(predict_class(msg, model), intents)
        chatbotResponse = res
        print("en_sw chatbot_response:- ", res)
    elif detected_language == 'sw':
        translated_msg = translate_text_swa_eng(msg)
        res = getResponse(predict_class(translated_msg, model), intents)
        chatbotResponse = translate_text_eng_swa(res)
        print("sw_en chatbot_response:- ", chatbotResponse)

    return chatbotResponse

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        return jsonify({'message': 'Login successful'})
    
    return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 400
    
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    return jsonify({'message': 'Signup successful'})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Protected route decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Update existing routes to require login
@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/get")
@login_required
def get_bot_response():
    userText = request.args.get('msg')
    session_id = request.args.get('session_id')
    
    if not session_id:
        # Create new session if none exists
        session = ChatSession(user_id=session['user_id'])
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    print("get_bot_response:- " + userText)

    doc = nlp(userText)
    detected_language = doc._.language['language']
    print(f"Detected language get_bot_response:- {detected_language}")

    bot_response_translate = "Loading bot response..........."  

    if detected_language == "en":
        bot_response_translate = userText  
        print("en_sw get_bot_response:-", bot_response_translate)
        
    elif detected_language == 'sw':
        bot_response_translate = translate_text_swa_eng(userText)  
        print("sw_en get_bot_response:-", bot_response_translate)

    chatbot_response_text = chatbot_response(bot_response_translate)

    if detected_language == 'sw':
        chatbot_response_text = translate_text_eng_swa(chatbot_response_text)

    # Save chat message to database
    chat_message = ChatMessage(
        session_id=session_id,
        message=userText,
        response=chatbot_response_text,
        language=detected_language
    )
    db.session.add(chat_message)
    db.session.commit()

    return jsonify({
        'response': chatbot_response_text,
        'session_id': session_id
    })

@app.route("/history/<int:session_id>")
@login_required
def get_chat_history(session_id):
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != session['user_id']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
    
    history = [{
        'message': msg.message,
        'response': msg.response,
        'language': msg.language,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages]
    
    return jsonify(history)

if __name__ == "__main__":
    app.run()
