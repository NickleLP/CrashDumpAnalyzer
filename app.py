import os
from flask import Flask, request, redirect, url_for, render_template, flash, send_from_directory, session
import subprocess
import markdown
import re
from datetime import datetime
from flask_babel import Babel, gettext as _
from config import VERSION
import sys
from urllib.parse import urlparse
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
app.secret_key = '578493092754320oio6547a32653402tzu174321045d414d5g4d5g314d5644315¨ü6448¨$34ö14$üöäiä643*914*64*op416*43146*443*i1*643i*16*443*146*4431*464*31464i4315p453145oi6443165464531'
app.jinja_env.add_extension('jinja2.ext.i18n')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ANALYSIS_FOLDER'] = 'analyses'
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'de', "nl"]

# Konfiguration der Datenbank
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

VALID_REDIRECTS = [
    '/', 
    '/changelog', 
    '/analysis'
]

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exception_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    application_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    analysis = db.relationship('Analysis', backref='ticket', uselist=False)

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)


def validate_url(url):
    parsed_url = urlparse(url.replace('\\', ''))
    if parsed_url.path in VALID_REDIRECTS and not parsed_url.query and not parsed_url.fragment:
        return parsed_url.path
    return '/'

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def get_locale():
    # Überprüfen, ob eine Sprache in der Session gespeichert ist
    lang = session.get('lang', 'en')
    #print(f"Aktuelle Sprache: {lang}")
    return lang

babel = Babel(app, locale_selector=get_locale)

@app.route('/set_language/<language>')
def set_language(language):
    session['lang'] = language
    referrer = request.referrer
    if not referrer or not is_safe_url(referrer):
        referrer = url_for('upload_file')
    return redirect(referrer)

# Erstellen der Verzeichnisse, falls sie nicht existieren
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANALYSIS_FOLDER'], exist_ok=True)

# Globale Variablen für Tickets
ticket_number = 1
tickets = {}

# Erlaubte Dateierweiterungen
ALLOWED_EXTENSIONS = {'dmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_cdb_executable():
    possible_paths = [
        r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe',
        r'C:\Program Files\Windows Kits\10\Debuggers\x64\cdb.exe',
        # Weitere mögliche Pfade hinzufügen
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def get_exception_description(code):
    exception_codes = {
        '0xC0000005': 'Access Violation',
        '0x80000003': 'Breakpoint',
        '0x80000004': 'Single Step',
        '0xC0000094': 'Integer division by zero',
        '0xC0000095': 'Integer overflow',
        '0xC00000FD': 'Stack Overflow',
        '0xC0000135': 'DLL not found',
        '0xC0000139': 'Entry point not found',
        '0xC0000142': 'DLL initialization failed',
        '0xE0434352': '.NET exception',
        '0xC0000409': 'Stack buffer overflow',
        # Weitere Exception-Codes können hier hinzugefügt werden
    }
    code = code.strip()
    if code.lower().startswith('0x'):
        code = '0x' + code[2:].upper()
    else:
        code = '0x' + code.upper()
    return exception_codes.get(code, _('Unknown error'))

def analyze_dump(dump_file_path, ticket_number):
    debugger_path = find_cdb_executable()
    if debugger_path is None:
        flash(_('cdb.exe could not be found. Please install the Windows debugging tools.'))
        return _("Debugger not found", "Please install the Windows Debugging Tools.")

    command = f'"{debugger_path}" -z "{dump_file_path}" -c "!analyze -v; q"'

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, errors = process.communicate(timeout=60)
        output = output.decode('utf-8', errors='ignore')
        errors = errors.decode('utf-8', errors='ignore')

        # Speichern der Analyseausgabe in einer Datei
        analysis_filename = f"analysis_{ticket_number}.txt"
        analysis_path = os.path.join(app.config['ANALYSIS_FOLDER'], analysis_filename)
        with open(analysis_path, 'w', encoding='utf-8') as f:
            f.write(output)

        # Extrahieren des Anwendungsnamens
        process_name_match = re.search(r'PROCESS_NAME:\s+(\S+)', output)
        if process_name_match:
            exe_name = process_name_match.group(1)
        else:
            # Fallback auf IMAGE_NAME
            image_name_match = re.search(r'IMAGE_NAME:\s+(\S+)', output)
            exe_name = image_name_match.group(1) if image_name_match else "Unknown application"

        # Extrahieren des Exception-Codes
        exception_code_match = re.search(r'ExceptionCode:\s+(\S+)', output)
        if exception_code_match:
            exception_code = exception_code_match.group(1)
        else:
            exception_code = "Unknown error"

        # Debugging-Ausgabe
        # print("Extrahierter Exception-Code:", exception_code)

        # Beschreibung erhalten
        exception_description = get_exception_description(exception_code)

        # Kombinieren von Code und Beschreibung
        if exception_description != 'Unknown error':
            crash_reason = f"{exception_code} - {exception_description}"
        else:
            crash_reason = exception_code

    except subprocess.TimeoutExpired:
        exe_name = _("Analysis canceled") 
        crash_reason = _("The debugger did not respond within the expected time.") 
    except Exception as e:
        exe_name = _("Errors in the analysis") 
        crash_reason = str(e)

    return exe_name, crash_reason

@app.context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'dump_file' not in request.files:
            flash(_('Keine Datei ausgewählt'))
            return redirect(request.url)
        file = request.files['dump_file']
        if file.filename == '':
            flash(_('Keine Datei ausgewählt'))
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow()
            unique_filename = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)

            # Führen Sie die Analyse durch (Ihre bestehende Analysefunktion)
            analysis_content, exception_code, description, application_name = analyze_dump(file_path)

            # Speichern Sie das Ticket und die Analyse in der Datenbank
            ticket = Ticket(
                exception_code=exception_code,
                description=description,
                application_name=application_name,
                timestamp=timestamp
            )
            db.session.add(ticket)
            db.session.commit()

            analysis = Analysis(
                ticket_id=ticket.id,
                content=analysis_content
            )
            db.session.add(analysis)
            db.session.commit()

            flash(_('Datei hochgeladen und analysiert. Ticketnummer: ') + str(ticket.id))
            return redirect(url_for('upload_file'))
        else:
            flash(_('Bitte eine gültige .dmp-Datei hochladen'))
            return redirect(request.url)
    else:
        # Laden Sie die Tickets aus der Datenbank
        tickets = Ticket.query.order_by(Ticket.timestamp.desc()).all()
        return render_template('index.html', tickets=tickets)


@app.route('/changelog')
def changelog():
    # Bestimmen des Basisverzeichnisses
    if getattr(sys, 'frozen', False):
        # Anwendung ist als ausführbare Datei gebündelt
        application_path = sys._MEIPASS
    else:
        # Anwendung wird normal ausgeführt
        application_path = os.path.dirname(os.path.abspath(__file__))

    changelog_path = os.path.join(application_path, 'changelog.md')

    if not os.path.exists(changelog_path):
        return _("Changelog file not found."), 404

    with open(changelog_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Konvertieren von Markdown zu HTML
    changelog_html = markdown.markdown(content)
    return render_template('changelog.html', changelog=changelog_html, version=VERSION)

@app.route('/analysis/<int:ticket_id>')
def view_analysis(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    analysis_content = ticket.analysis.content
    return render_template('analysis.html',
                           ticket=ticket,
                           analysis_content=analysis_content)

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
