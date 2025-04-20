# api/notes_api.py
from flask import Blueprint, request, jsonify, abort
from entities.emotion_report import EmotionReport
from entities.emotion_report_notes import EmotionReportNote
from repository.emotion_report_repository import EmotionReportRepository
from repository.report_note_repository import ReportNoteRepository

notes_api    = Blueprint('notes_api', __name__, url_prefix='/api')
report_repo  = EmotionReportRepository()
note_repo    = ReportNoteRepository()

# ------------------- helpers -------------------
def _get_report_or_404(report_id: int):
    rep = report_repo.get_by_id(report_id)
    if not rep:
        abort(404, description='Report not found')
    return rep

def _get_note_or_404(note_id: int):
    note = note_repo.get(note_id)
    if not note:
        abort(404, description='Note not found')
    return note

# ------------------- endpoints -----------------
@notes_api.get('/reports/<int:report_id>/notes')
def list_notes(report_id):
    _get_report_or_404(report_id)
    notes = note_repo.list_by_report(report_id)
    return jsonify([{
        "id": n.id,
        "text": n.text,
        "username": n.username,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat() if n.updated_at else None
    } for n in notes])

@notes_api.post('/reports/<int:report_id>/notes')
def add_note(report_id):
    _get_report_or_404(report_id)
    data = request.get_json(force=True)
    text = data.get('text', '').strip()
    if not text:
        abort(400, description='Note text is empty')
    note = EmotionReportNote(report_id=report_id,
                             text=text,
                             user_id=0,       # ← cambiar cuando implementes login
                             username='Anon')
    note_repo.add(note)
    return jsonify({'status': 'created', 'id': note.id}), 201

@notes_api.patch('/notes/<int:note_id>')
def edit_note(note_id):
    note = _get_note_or_404(note_id)
    data = request.get_json(force=True)
    text = data.get('text', '').strip()
    if not text:
        abort(400, description='Note text is empty')
    note.text = text
    note_repo.update(note)
    return jsonify({'status': 'updated'})

@notes_api.delete('/notes/<int:note_id>')
def delete_note(note_id):
    note = _get_note_or_404(note_id)
    note_repo.delete(note)
    return jsonify({'status': 'deleted'})
