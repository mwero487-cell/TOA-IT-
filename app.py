import os
from datetime import datetime, timezone

from flask import Flask, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__, template_folder='.')
mongo_client = MongoClient(
    os.getenv('MONGODB_URI', 'mongodb://127.0.0.1:27017'),
    serverSelectionTimeoutMS=2000,
)
tickets = mongo_client[os.getenv('MONGODB_DATABASE', 'helpdesk')]['tickets']

STATUSES = ('Request', 'Uphold', 'Done')
CATEGORIES = {'Hardware', 'Software', 'Network', 'Other'}


def render_dashboard(
    message=None,
    message_type='error',
    form_data=None,
    status=200,
    template='IT Helpdesk/IT Helpdesk Demo.html',
):
    try:
        ticket_counts = {
            ticket_status: tickets.count_documents({'status': ticket_status})
            for ticket_status in STATUSES
        }
    except PyMongoError:
        ticket_counts = {ticket_status: 0 for ticket_status in STATUSES}
        if message is None:
            message = 'MongoDB is unavailable. Start MongoDB or configure MONGODB_URI.'
            message_type = 'error'

    return render_template(
        template,
        current_time=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        ticket_counts=ticket_counts,
        message=message,
        message_type=message_type,
        form_data=form_data or {},
    ), status


@app.get('/')
def home():
    message = None
    if request.args.get('saved') == '1':
        message = 'Ticket logged successfully.'
    return render_dashboard(message=message, message_type='success')


@app.get('/demo')
def demo():
    message = None
    if request.args.get('saved') == '1':
        message = 'Ticket logged successfully.'
    return render_dashboard(
        message=message,
        message_type='success',
        template='IT Helpdesk/IT Helpdesk Demo.html',
    )


@app.post('/tickets')
def log_ticket():
    is_demo = request.args.get('view') == 'demo'
    template = 'IT Helpdesk/IT Helpdesk Demo.html'
    form_data = {
        'username': request.form.get('username', '').strip(),
        'issue': request.form.get('issue', '').strip(),
        'category': request.form.get('category', '').strip(),
    }
    if (
        not form_data['username']
        or len(form_data['username']) > 120
        or not form_data['issue']
        or len(form_data['issue']) > 2000
        or form_data['category'] not in CATEGORIES
    ):
        return render_dashboard(
            message='Enter a requester, issue, and valid category.',
            form_data=form_data,
            status=400,
            template=template,
        )

    try:
        tickets.insert_one({
            'requester': form_data['username'],
            'issue': form_data['issue'],
            'category': form_data['category'],
            'status': 'Request',
            'created_at': datetime.now(timezone.utc),
        })
    except PyMongoError:
        return render_dashboard(
            message='MongoDB is unavailable. The ticket was not saved.',
            form_data=form_data,
            status=503,
            template=template,
        )

    if is_demo:
        return redirect(url_for('demo', saved='1'))
    return redirect(url_for('home', saved='1'))

if __name__ == '__main__':
    app.run(debug=True)
