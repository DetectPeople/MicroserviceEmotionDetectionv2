# repository/person_repository.py

from entities.person import Person
from entities import db

class PersonRepository:
    def get_by_video_and_identity(self, video_id, identity):
        """Fetch person by video ID and unique identity."""
        return Person.query.filter_by(video_id=video_id, identity=identity).first()

    def create(self, video_id, identity):
        """Create a new person entry."""
        person = Person(video_id=video_id, identity=identity)
        db.session.add(person)
        db.session.commit()
        return person

    def get_or_create(self, video_id, identity):
        """Fetch existing person or create a new one if unique."""
        person = self.get_by_video_and_identity(video_id, identity)
        if not person:
            person = self.create(video_id, identity)
        return person
