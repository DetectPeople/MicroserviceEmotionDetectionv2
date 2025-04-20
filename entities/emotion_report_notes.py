from datetime import datetime
from entities import db

class EmotionReportNote(db.Model):
    __tablename__ = 'emotion_report_notes'

    id        = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('emotion_reports.id', ondelete='CASCADE'),
                          nullable=False)
    user_id   = db.Column(db.Integer, nullable=False, default=0)
    username  = db.Column(db.String(80), default='Anon')
    text      = db.Column(db.Text, nullable=False)
    created_at= db.Column(db.DateTime, default=datetime.utcnow)
    updated_at= db.Column(db.DateTime, onupdate=datetime.utcnow)

    report = db.relationship('EmotionReport', back_populates='notes')