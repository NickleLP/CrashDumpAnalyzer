import os
from flask import Flask, request, redirect, url_for, render_template, flash, send_from_directory
import subprocess
import markdown
import re
from datetime import datetime
from config import VERSION
import sys


app = Flask(__name__)
app.secret_key = 'IhrGeheimerSchlüssel'  # Bitte ändern Sie dies zu einem sicheren Wert
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ANALYSIS_FOLDER'] = 'analyses'

# Erstellen der Verzeichnisse, falls sie nicht existieren
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANALYSIS_FOLDER'], exist_ok=True)

# Globale Variablen für Tickets
ticket_number = 1
tickets = {}

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
        '0xC0000005': 'Zugriffsverletzung (Access Violation)',
        '0x80000003': 'Breakpoint',
        '0x80000004': 'Single Step',
        '0xC0000094': 'Integer Division durch Null',
        '0xC0000095': 'Integerüberlauf',
        '0xC00000FD': 'Stack Overflow',
        '0xC0000135': 'DLL nicht gefunden',
        '0xC0000139': 'Einstiegspunkt nicht gefunden',
        '0xC0000142': 'DLL-Initialisierung fehlgeschlagen',
        '0xE0434352': '.NET-Ausnahme',
        '0xC0000409': 'Stack-Pufferüberlauf',
        # Weitere Exception-Codes können hier hinzugefügt werden
    }
    code = code.strip()
    if code.lower().startswith('0x'):
        code = '0x' + code[2:].upper()
    else:
        code = '0x' + code.upper()
    return exception_codes.get(code, 'Unbekannter Fehler')

def analyze_dump(dump_file_path, ticket_number):
    debugger_path = find_cdb_executable()
    if debugger_path is None:
        flash('cdb.exe wurde nicht gefunden. Bitte installieren Sie die Windows Debugging Tools.')
        return "Debugger nicht gefunden", "Bitte installieren Sie die Windows Debugging Tools."

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
            exe_name = image_name_match.group(1) if image_name_match else "Unbekannte Anwendung"

        # Extrahieren des Exception-Codes
        exception_code_match = re.search(r'ExceptionCode:\s+(\S+)', output)
        if exception_code_match:
            exception_code = exception_code_match.group(1)
        else:
            exception_code = "Unbekannter Fehler"

        # Debugging-Ausgabe
        # print("Extrahierter Exception-Code:", exception_code)

        # Beschreibung erhalten
        exception_description = get_exception_description(exception_code)

        # Kombinieren von Code und Beschreibung
        if exception_description != 'Unbekannter Fehler':
            crash_reason = f"{exception_code} - {exception_description}"
        else:
            crash_reason = exception_code

    except subprocess.TimeoutExpired:
        exe_name = "Analyse abgebrochen"
        crash_reason = "Der Debugger hat nicht innerhalb der erwarteten Zeit geantwortet."
    except Exception as e:
        exe_name = "Fehler bei der Analyse"
        crash_reason = str(e)

    return exe_name, crash_reason

# Rest Ihres Codes bleibt unverändert

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    global ticket_number
    if request.method == 'POST':
        # Überprüfen, ob die POST-Anfrage die Datei enthält
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt')
            return redirect(request.url)
        if file and file.filename.endswith('.dmp'):
            # Speichern der Datei
            dump_filename = f"dump_{ticket_number}.dmp"
            dump_path = os.path.join(app.config['UPLOAD_FOLDER'], dump_filename)
            file.save(dump_path)

            # Analysieren der Dump-Datei (Ticketnummer übergeben)
            exe_name, crash_reason = analyze_dump(dump_path, ticket_number)

            # Speichern des Tickets
            tickets[ticket_number] = {
            'exe_name': exe_name,
            'crash_reason': crash_reason,
            'analysis_file': f"analysis_{ticket_number}.txt",
            'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }

            flash(f'Datei hochgeladen und analysiert. Ticketnummer: {ticket_number}')
            ticket_number += 1

            return redirect(url_for('upload_file'))
        else:
            flash('Bitte eine gültige .dmp-Datei hochladen')
            return redirect(url_for('upload_file'))
    return render_template('index.html', tickets=tickets, version=VERSION)

@app.route('/changelog')
def changelog():
    with open('changelog.md', 'r', encoding='utf-8') as f:
        content = f.read()
    # Konvertieren von Markdown zu HTML
    changelog_html = markdown.markdown(content)
    return render_template('changelog.html', changelog=changelog_html, version=VERSION)

@app.route('/analysis/<int:ticket_number>')
def view_analysis(ticket_number):
    analysis_filename = f"analysis_{ticket_number}.txt"
    analysis_path = os.path.join(app.config['ANALYSIS_FOLDER'], analysis_filename)

    if os.path.exists(analysis_path):
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis_content = f.read()
        return render_template('analysis.html', ticket_number=ticket_number, analysis_content=analysis_content)
    else:
        flash('Analysebericht nicht gefunden.')
        return redirect(url_for('upload_file'))

if __name__ == '__main__':
    app.run(debug=True)
