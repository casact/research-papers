# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

from flask import Flask, jsonify, send_from_directory, request, send_file, Response, stream_with_context
from flask_cors import CORS
import threading
from datetime import datetime
import subprocess
from pathlib import Path
from pdf_service import list_document_groups, generate_document_pdf
import os, sys
import json
import uuid
import yaml
import queue

# Get the absolute path to the frontend dist folder
BACKEND_DIR = Path(__file__).parent.resolve()
FRONTEND_DIST = BACKEND_DIR.parent / 'frontend' / 'dist'
CONFIG_DIR = BACKEND_DIR.parent.parent / 'config'
PROJECT_ROOT = BACKEND_DIR.parent.parent

app = Flask(__name__, static_folder=str(FRONTEND_DIST))
CORS(app)

# Job tracking
jobs = {}
jobs_lock = threading.Lock()

# Log streaming queues for real-time log delivery
log_queues = {}  # {job_id: [queue.Queue, ...]}

# Helper functions
def get_input_folder_from_config(config_file):
    """Read input folder from config file"""
    try:
        config_path = CONFIG_DIR / config_file
        if not config_path.exists():
            return None
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('processing', {}).get('input_folder', 'input/fhir_bundles')
    except Exception as e:
        print(f"Error reading config: {e}")
        return 'input/fhir_bundles'

def extract_cost_from_logs(stdout):
    """Extract cost information from script output"""
    import re

    cost_info = {
        'total_cost': 0.0,
        'total_tokens': 0,
        'api_calls': 0,
        'encounters_processed': 0
    }

    try:
        # Look for cost patterns in output
        cost_match = re.search(r'Total cost:\s*\$?([\d.]+)', stdout)
        if cost_match:
            cost_info['total_cost'] = float(cost_match.group(1))

        # Look for token count
        tokens_match = re.search(r'Total tokens:\s*([\d,]+)', stdout)
        if tokens_match:
            cost_info['total_tokens'] = int(tokens_match.group(1).replace(',', ''))

        # Look for API calls
        api_match = re.search(r'API calls made:\s*(\d+)', stdout)
        if api_match:
            cost_info['api_calls'] = int(api_match.group(1))

        # Look for encounters processed
        encounters_match = re.search(r'Encounters processed:\s*(\d+)', stdout)
        if encounters_match:
            cost_info['encounters_processed'] = int(encounters_match.group(1))

    except Exception as e:
        print(f"Error extracting cost info: {e}")

    return cost_info


def run_script_process (job_id, script_path, args):
    """Run script in subprocess and stream output in real-time"""
    with jobs_lock:
        job = jobs[job_id]

    try:
        # Use the same Python executable that's running Flask
        # This ensures we use the virtual environment's Python with all installed packages
        python_executable = sys.executable

        # Build command with unbuffered output
        cmd = [python_executable, '-u', str(script_path)] + args

        # Get current environment and set UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        # Start process with proper encoding
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified streaming
            text=True,
            bufsize=1,  # Line buffered
            encoding='utf-8',
            errors='replace',  # Replace undecodable characters instead of crashing
            cwd=PROJECT_ROOT,
            env=env
        )

        with jobs_lock:
            jobs[job_id]['process'] = process

        # Stream output line by line
        full_output = []

        try:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break

                # Store line
                full_output.append(line)

                # Update job logs incrementally
                with jobs_lock:
                    jobs[job_id]['logs'] = ''.join(full_output)

                # Send to all connected streaming clients
                with jobs_lock:
                    if job_id in log_queues:
                        for q in log_queues[job_id]:
                            try:
                                q.put_nowait(line)
                            except queue.Full:
                                pass  # Skip if queue is full

            # Wait for process to complete
            exit_code = process.wait()

            # Send completion sentinel to all connected clients
            with jobs_lock:
                if job_id in log_queues:
                    for q in log_queues[job_id]:
                        try:
                            q.put_nowait(None)  # Signal completion
                        except queue.Full:
                            pass

        except Exception as read_error:
            print(f"Error reading process output: {read_error}")
            exit_code = process.returncode if process.returncode is not None else -1

        combined_text = ''.join(full_output)

        # Extract cost information from output
        cost_info = extract_cost_from_logs(combined_text)

        # Update job with final status
        with jobs_lock:
            jobs[job_id]['status'] = 'completed' if exit_code == 0 else 'failed'
            jobs[job_id]['exit_code'] = exit_code
            jobs[job_id]['end_time'] = datetime.now().isoformat()
            jobs[job_id]['cost_info'] = cost_info
            jobs[job_id]['logs'] = combined_text
            jobs[job_id]['process'] = None

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        with jobs_lock:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['logs'] = (jobs[job_id].get('logs', '') +
                                    f"\n\n=== EXCEPTION ===\n{str(e)}\n\n{error_details}")
            jobs[job_id]['end_time'] = datetime.now().isoformat()
            jobs[job_id]['process'] = None

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'LLM Claims Analysis API is running'})

@app.route('/api/info')
def info():
    return jsonify({
        'title': 'LLM Claims Analysis Pipeline',
        'version': '1.0.0',
        'description': 'AI-powered medical claims analysis system'
    })

@app.route('/api/config/<path:config_file>', methods=['GET'])
def get_config(config_file):
    """Get configuration file contents"""
    try:
        config_path = CONFIG_DIR / config_file

        # Security check: ensure the file is within CONFIG_DIR
        if not str(config_path.resolve()).startswith(str(CONFIG_DIR.resolve())):
            return jsonify({'error': 'Invalid config path'}), 403

        if not config_path.exists():
            return jsonify({'error': 'Config file not found'}), 404

        with open(config_path, 'r') as f:
            content = f.read()

        return content, 200, {'Content-Type': 'text/plain'}

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/<path:config_file>', methods=['POST'])
def update_config(config_file):
    """Update configuration file"""
    try:
        config_path = CONFIG_DIR / config_file

        # Security check: ensure the file is within CONFIG_DIR
        if not str(config_path.resolve()).startswith(str(CONFIG_DIR.resolve())):
            return jsonify({'error': 'Invalid config path'}), 403

        if not config_path.exists():
            return jsonify({'error': 'Config file not found'}), 404

        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content field'}), 400

        # Validate YAML syntax before saving
        try:
            yaml.safe_load(data['content'])
        except yaml.YAMLError as e:
            return jsonify({'error': f'Invalid YAML syntax: {str(e)}'}), 400

        # Write new content
        with open(config_path, 'w') as f:
            f.write(data['content'])

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/input-files', methods=['GET'])
def get_input_files():
    """Get list of input files from configured input folder"""
    try:
        config_file = request.args.get('config', '1_data-process_fhir_bundle.yaml')
        input_folder = get_input_folder_from_config(config_file)

        if not input_folder:
            return jsonify({'error': 'Could not read input folder from config'}), 500

        input_path = PROJECT_ROOT / input_folder

        if not input_path.exists():
            return jsonify({'error': f'Input folder not found: {input_folder}'}), 404

        # List all JSON files
        files = []
        for file_path in input_path.glob('*.json'):
            try:
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                continue

        # Sort by modified date (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({
            'files': files,
            'input_folder': input_folder
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview-file', methods=['GET'])
def preview_file():
    """Preview contents of an input file"""
    try:
        config_file = request.args.get('config', '1_data-process_fhir_bundle.yaml')
        filename = request.args.get('filename')

        if not filename:
            return jsonify({'error': 'Missing filename parameter'}), 400

        input_folder = get_input_folder_from_config(config_file)
        if not input_folder:
            return jsonify({'error': 'Could not read input folder from config'}), 500

        file_path = PROJECT_ROOT / input_folder / filename

        # Security check
        if not str(file_path.resolve()).startswith(str((PROJECT_ROOT / input_folder).resolve())):
            return jsonify({'error': 'Invalid file path'}), 403

        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        # Read file with size limit
        max_size = 1024 * 1024  # 1MB
        file_size = file_path.stat().st_size

        with open(file_path, 'r') as f:
            if file_size > max_size:
                content = f.read(max_size)
                truncated = True
            else:
                content = f.read()
                truncated = False

        # Parse JSON
        try:
            json_content = json.loads(content)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON file'}), 400

        return jsonify({
            'content': json_content,
            'truncated': truncated,
            'size': file_size
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """Return available document directories and files for the frontend grid."""
    try:
        groups = list_document_groups()
        total_directories = sum(len(group['directories']) for group in groups)
        total_files = sum(len(directory.get('files', [])) for group in groups for directory in group['directories'])

        return jsonify({
            'groups': groups,
            'summary': {
                'total_groups': len(groups),
                'total_directories': total_directories,
                'total_files': total_files,
                'generated_at': datetime.utcnow().isoformat() + 'Z'
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/pdf', methods=['GET'])
def download_document_pdf():
    """Generate a human-friendly PDF for the requested document."""
    try:
        relative_path = request.args.get('path')
        if not relative_path:
            return jsonify({'error': 'Missing path parameter'}), 400

        absolute_path = None
        try:
            pdf_buffer, absolute_path = generate_document_pdf(relative_path)
        except FileNotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except Exception as exc:
            error_subject = absolute_path or relative_path
            error_message = f"PDF generation failed for {error_subject}: {exc}"
            print(error_message)
            return jsonify({'error': error_message}), 500

        download_name = f"{absolute_path.stem}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute-script', methods=['POST'])
def execute_script():
    """Execute a script with given arguments"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        script_type = data.get('scriptType', 'process_bundle')
        input_file = data.get('inputFile')
        args_dict = data.get('args', {})

        if not input_file:
            return jsonify({'error': 'Missing inputFile'}), 400

        # Map script type to script file
        script_map = {
            'process_bundle': '1_data-process_fhir_bundle.py'
        }

        script_name = script_map.get(script_type)
        if not script_name:
            return jsonify({'error': f'Unknown script type: {script_type}'}), 400

        script_path = PROJECT_ROOT / script_name

        if not script_path.exists():
            return jsonify({'error': f'Script not found: {script_name}'}), 404

        # Build command arguments
        config_file = data.get('config', '1_data-process_fhir_bundle.yaml')
        input_folder = get_input_folder_from_config(config_file)
        full_input_path = PROJECT_ROOT / input_folder / input_file

        args = ['-b', str(full_input_path)]

        # Add optional arguments
        if args_dict.get('outputDir'):
            args.extend(['--output-dir', args_dict['outputDir']])
        if args_dict.get('limit'):
            args.extend(['--limit', str(args_dict['limit'])])
        if args_dict.get('verbose'):
            args.append('--verbose')
        if args_dict.get('dryRun'):
            args.append('--dry-run')
        if args_dict.get('skipValidation'):
            args.append('--skip-validation')

        # Create job
        job_id = str(uuid.uuid4())
        job = {
            'id': job_id,
            'input_file': input_file,
            'script_type': script_type,
            'args': args_dict,
            'status': 'running',
            'logs': '',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'exit_code': None,
            'process': None,
            'cost_info': {
                'total_cost': 0.0,
                'total_tokens': 0,
                'api_calls': 0,
                'encounters_processed': 0
            }
        }

        with jobs_lock:
            jobs[job_id] = job

        # Start script in background thread
        thread = threading.Thread(target=run_script_process, args=(job_id, script_path, args))
        thread.daemon = True
        thread.start()

        return jsonify({
            'job_id': job_id,
            'status': 'running'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get list of all jobs"""
    try:
        with jobs_lock:
            job_list = []
            for job_id, job in jobs.items():
                job_list.append({
                    'id': job['id'],
                    'input_file': job['input_file'],
                    'script_type': job['script_type'],
                    'status': job['status'],
                    'start_time': job['start_time'],
                    'end_time': job['end_time'],
                    'exit_code': job['exit_code'],
                    'cost_info': job.get('cost_info', {
                        'total_cost': 0.0,
                        'total_tokens': 0,
                        'api_calls': 0,
                        'encounters_processed': 0
                    })
                })

        # Sort by start time (newest first)
        job_list.sort(key=lambda x: x['start_time'], reverse=True)

        return jsonify({'jobs': job_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get details of a specific job including logs"""
    try:
        with jobs_lock:
            job = jobs.get(job_id)

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        # Return job details with combined logs
        return jsonify({
            'id': job['id'],
            'input_file': job['input_file'],
            'script_type': job['script_type'],
            'args': job['args'],
            'status': job['status'],
            'logs': job.get('logs', ''),
            'start_time': job['start_time'],
            'end_time': job['end_time'],
            'exit_code': job['exit_code'],
            'cost_info': job.get('cost_info', {
                'total_cost': 0.0,
                'total_tokens': 0,
                'api_calls': 0,
                'encounters_processed': 0
            })
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job from tracking"""
    try:
        with jobs_lock:
            if job_id not in jobs:
                return jsonify({'error': 'Job not found'}), 404

            del jobs[job_id]

        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/logs/stream')
def stream_job_logs(job_id):
    """Stream job logs in real-time using Server-Sent Events (SSE)"""

    def generate():
        # Create queue for this connection
        q = queue.Queue(maxsize=1000)  # Limit queue size to prevent memory issues

        with jobs_lock:
            if job_id not in jobs:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            # Register queue for this job
            if job_id not in log_queues:
                log_queues[job_id] = []
            log_queues[job_id].append(q)

            # Send initial logs if any exist
            existing_logs = jobs[job_id].get('logs', '')
            if existing_logs:
                yield f"data: {json.dumps({'log': existing_logs, 'type': 'initial'})}\n\n"

        try:
            while True:
                # Wait for new log line (with timeout for heartbeat)
                try:
                    line = q.get(timeout=15)

                    if line is None:  # Sentinel value for job completion
                        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                        break

                    # Send log line to frontend
                    yield f"data: {json.dumps({'log': line, 'type': 'line'})}\n\n"

                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"

                    # Check if job is still running
                    with jobs_lock:
                        if job_id in jobs and jobs[job_id]['status'] != 'running':
                            break
        finally:
            # Cleanup: remove queue when connection closes
            with jobs_lock:
                if job_id in log_queues and q in log_queues[job_id]:
                    log_queues[job_id].remove(q)
                    if not log_queues[job_id]:
                        del log_queues[job_id]

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

# Serve React frontend in production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Check if frontend dist folder exists
    if not FRONTEND_DIST.exists():
        return jsonify({
            'error': 'Frontend not built',
            'message': 'Please run "npm run build" in the app/frontend directory',
            'api_status': 'running',
            'endpoints': {
                'health': '/api/health',
                'info': '/api/info'
            }
        }), 503

    # Serve static files
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Serve index.html for all other routes (SPA routing)
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Check if frontend is built
    if FRONTEND_DIST.exists():
        print(f"✅ Frontend found at: {FRONTEND_DIST}")
    else:
        print(f"⚠️  Frontend not built. Run 'cd app/frontend && npm run build'")

    print("🚀 Starting Flask server on http://localhost:5000")
    print("📡 API endpoints:")
    print("   - http://localhost:5000/api/health")
    print("   - http://localhost:5000/api/info")
    print("   - http://localhost:5000/api/config/<config_file> (GET/POST)")

    app.run(debug=True, port=5000, host='0.0.0.0')
