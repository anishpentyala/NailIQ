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


class Feedback(db.Model):
    """A user's "was this finding right?" response. The thresholds in the color and
    geometry tracks are uncalibrated rough estimates; this is the honest data path
    for eventually calibrating them against real photos -- captured per finding so a
    later calibration run can weigh confirmed vs. disputed verdicts. Stores no image
    and no PII, only the label, the verdict shown, and whether the user agreed."""

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey("scan_record.id"), nullable=True)
    label = db.Column(db.String(64), nullable=False)
    shown_verdict = db.Column(db.String(16), nullable=False)
    agreed = db.Column(db.Boolean, nullable=False)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "scan_id": self.scan_id,
            "label": self.label,
            "shown_verdict": self.shown_verdict,
            "agreed": self.agreed,
            "note": self.note,
        }
