from entities import db
from entities.emotion_report_notes import EmotionReportNote

class ReportNoteRepository:
    # CRUD básico -----------------------------------------------------------
    def list_by_report(self, report_id: int):
        return (EmotionReportNote.query
                .filter_by(report_id=report_id)
                .order_by(EmotionReportNote.created_at)
                .all())

    def get(self, note_id: int):
        return EmotionReportNote.query.get(note_id)

    def add(self, note: EmotionReportNote):
        db.session.add(note)
        db.session.commit()

    def update(self, note: EmotionReportNote):
        db.session.commit()

    def delete(self, note: EmotionReportNote):
        db.session.delete(note)
        db.session.commit()
