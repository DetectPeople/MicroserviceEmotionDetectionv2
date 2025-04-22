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

    def update_conclusion(self, report_id: int, conclusion_text: str) -> EmotionReport:
        report = EmotionReport.query.filter_by(id=report_id).first()
        if not report:
            return None
        report.conclusion = conclusion_text
        db.session.commit()
        return report

    def clear_conclusion(self, report_id: int) -> EmotionReport:
        report = EmotionReport.query.filter_by(id=report_id).first()
        if not report:
            return None
        report.conclusion = None
        db.session.commit()
        return report