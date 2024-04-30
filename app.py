import os
import shutil
import json
from werkzeug.utils import secure_filename
from flask import Flask, flash, request, redirect, url_for, render_template
import plotly.graph_objs as go
import plotly
import requests
from dotenv import load_dotenv
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError
import boto3
from utils.utils import audio_process

# Load environment variables from .env file
load_dotenv()

# Create Flask App
app = Flask(__name__)
UPLOAD_FOLDER = 'static/tmp/'
ALLOWED_EXTENSIONS = {'wav', 'mp3'}
ENDPOINT_URL = os.getenv('API_ENDPOINT')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
app.secret_key = os.environ["FLASK_SESSION_KEY"]
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def allowed_file(filename):
    """
    Check if the filename is allowed based on its extension.

    Args:
    filename (str): The name of the file to check.

    Returns:
    bool: True if the file's extension is within the allowed extensions, False otherwise.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """
    Route to handle file uploads. Deletes existing temporary files, processes uploaded files if they
    are in allowed formats, and redirects to the result classification page.

    Returns:
    Rendered template for the index page or a redirect to the result classification page.
    """
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', "info")
            return redirect(request.url)
        file = request.files['file']
        # If user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            flash('No selected file', "info")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = os.path.join(UPLOAD_FOLDER,
                                    secure_filename(file.filename))
            if not os.path.exists(UPLOAD_FOLDER):
                os.mkdir(UPLOAD_FOLDER)
            file.save(filename)
            final_filename = audio_process(filename)
            return redirect(url_for('classify_and_show_results',
                                    filename=final_filename))
    return render_template("index.html")


# Classify and show results
@app.route('/results', methods=['GET'])
def classify_and_show_results():
    """
    Route to display the classification results of an uploaded audio file. It sends the audio file 
    to an external API for processing, retrieves the classification results, and displays them 
    using a plotly bar chart.

    Returns:
    Rendered template with classification results or a redirect if an error occurs.
    """
    try:
        filename = request.args['filename']
        # filename = "children.wav"
        with open(filename, 'rb') as file:
            # Create a dictionary with the file data
            files = {"audio_file": file}
            response = requests.post(ENDPOINT_URL, files=files)

        prediction_classes = response.json()["classes"]
        prediction_probability = response.json()["probas"]
        predictions_to_render = {prediction_classes[i]: "{}%".format(
            round(prediction_probability[i]*100, 3)) for i in range(3)}
        # Create Plotly bar chart
        data = [
            go.Bar(
                x=list(predictions_to_render.keys()),
                y=list(predictions_to_render.values())
            )
        ]
        first_class = prediction_classes[0]
        choices = []
        choices = sorted(prediction_classes) + ["unknown"]
        # print(choices)
        graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
        # Render results
        return render_template("results.html",
                               filename=filename,
                               predictions_to_render=predictions_to_render,
                               first_class=first_class,
                               classes=choices,
                               graphJSON=graphJSON,
                               )
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('upload_file'))


@app.route('/validate', methods=['POST'])
def validate_result():
    """
    Route to handle validation of classification results by the user. Updates or confirms the label
    of an audio file, uploads the labeled data to AWS S3, and handles any errors related to AWS or
    other exceptions.

    Returns:
    Redirect to the upload page with a success or error message.
    """
    try:
        filename = request.form['filename']
        conform = request.form['confirm']
        label = request.form['prediction']
        if conform == "no":
            label = request.form['label']
        # Setup AWS S3 Client
        s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        bucket_name = bucket_name = AWS_ACCESS_KEY_ID.lower() + '-dump'
        s3_client.create_bucket(Bucket=bucket_name)
        s3_client.upload_file(filename, bucket_name, filename)

        temp_file_path = os.path.join(UPLOAD_FOLDER,
                                      "labels.txt")
        try:
            # Download the text file from the bucket
            s3_client.download_file(
                bucket_name, temp_file_path, temp_file_path)
            with open(temp_file_path, 'a', encoding='utf-8') as file:
                file.write(f"{filename}, {label}, {conform}\n")
        except ClientError:
            # Create the text file from the bucket
            with open(temp_file_path, 'w', encoding='utf-8') as file:
                header = "path, label, isCorrect\n"
                file.write(header)
                file.write(f"{filename}, {label}, {conform}\n")
        # Upload the modified file back to the bucket
        s3_client.upload_file(
            temp_file_path, bucket_name, temp_file_path)
        flash("File and tag sent. Thank you!", "success")
        return redirect(url_for('upload_file'))

    except (BotoCoreError, NoCredentialsError) as e:
        flash(f"An AWS error occurred: {str(e)}", "error")
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")

    return redirect(url_for('upload_file'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(
        os.environ.get("PORT", 5000)), debug=False)
