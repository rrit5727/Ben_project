from flask import Flask, request, redirect, url_for, send_from_directory, render_template, flash
import fitz
from collections import defaultdict
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(redirect(request.url))
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        if file: 
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            flash('File successfully uploaded')
            # for now, just redirect back to the form
            return redirect(url_for('upload_file'))
    return render_template('upload.html')

if __name__ == "__main__":
    app.run(debug=True)

