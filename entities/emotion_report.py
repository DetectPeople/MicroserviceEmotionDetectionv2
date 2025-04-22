from datetime import datetime
from entities import db

class EmotionReport(db.Model):
    __tablename__ = 'emotion_reports'

    id           = db.Column(db.Integer, primary_key=True)
    video_id     = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'),
                             nullable=False, unique=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    path         = db.Column(db.String(255))
    summary_json = db.Column(db.JSON)
    status       = db.Column(db.Enum('processing','done','error', name='report_status'),
                             default='processing')
    error_msg    = db.Column(db.Text)

    video  = db.relationship('Video', back_populates='reports')
    notes  = db.relationship('EmotionReportNote', back_populates='report',
                             cascade='all, delete-orphan', lazy=True)

    #nuevo
    conclusion = db.Column(db.Text, nullable=True)