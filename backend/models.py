import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ScanRecord(db.Model):
    """One persisted /analyze result, so users can browse past scans."""

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    findings_json = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "findings": json.loads(self.findings_json),
        }
