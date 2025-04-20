from entities import db
from entities.emotion_report import EmotionReport

class EmotionReportRepository:
    def get_by_video_id(self, video_id: int) -> EmotionReport | None:
        return EmotionReport.query.filter_by(video_id=video_id).first()

    def get_by_id(self, report_id: int) -> EmotionReport | None:
        return EmotionReport.query.get(report_id)

    def save(self, report: EmotionReport) -> None:
        db.session.add(report)
        db.session.commit()
