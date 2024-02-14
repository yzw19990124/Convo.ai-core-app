"""
Author: Dexter Yanzheng Wu
"""
import meta_data
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import openai
from werkzeug.utils import secure_filename
from flask_cors import CORS
import json
from pathlib import Path
import uuid

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Initialize OpenAI client with your API key
openai.api_key = meta_data.API_KEY


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            
            # Transcribe the audio file
            try:
                transcript_response = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=open(save_path, "rb"),
                    response_format="text"
                )
                transcript_text = transcript_response
                
                # Now send the transcript to GPT-3.5 Turbo
                gpt_response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    max_tokens=150,  # Adjust based on your needs
                    temperature=0.8,  # Adjust for creativity
                    messages= [
                        {'role': 'system','content':meta_data.BEHAVIOR},
                        {'role':'user', 'content':transcript_text}
                    ]
                )
                response_text = gpt_response.choices[0].message.content

            except Exception as e:
                os.remove(save_path)  # Clean up the file
                return jsonify({"error": str(e)})
            
            os.remove(save_path)  # Clean up the file
            return jsonify({"response": response_text})
        
@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    text = request.json.get('text', '')
    try:
        unique_filename = f"speech_{uuid.uuid4()}.mp3"
        speech_file_path = Path(app.config['UPLOAD_FOLDER']) / unique_filename
        response = openai.audio.speech.create(
          model="tts-1",
          voice="nova",
          input=text
        )
        #response.stream_to_file(str(speech_file_path))
        
        response.stream_to_file(str(speech_file_path))
        # Assuming you have a route set up to serve files from UPLOAD_FOLDER
        return jsonify({"speech_url": f"/uploads/{speech_file_path.name}"})
    except Exception as e:
        return jsonify({"error": str(e)})

# Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/delete-speech', methods=['POST'])
def delete_speech():
    data = request.get_json()
    filename = data.get('filename')
    if filename:
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.remove(file_path)
            return jsonify({"message": "File deleted successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Filename not provided"}), 400



# @app.route('/unity-avatar/Build/<path:filename>')
def serve_unity_build(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=8000)
