"""Integration tests for Flask endpoints."""
import base64
import json
import os
import sys
import tempfile

import cv2
import numpy as np
import pytest

# Add backend to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Must precede the app import (see app.py): the fixture's drop_all() runs against this
# temp database, never the real nailiq.db.
_TEST_DB = os.path.join(tempfile.mkdtemp(), 'nailiq_test.db')
os.environ['NAILIQ_DATABASE_URI'] = f'sqlite:///{_TEST_DB}'

import app as app_module  # noqa: E402


def _make_tiny_jpeg():
    """Create a minimal valid JPEG (solid color) and return base64-encoded."""
    # Create a tiny 10x10 solid gray image
    img = np.full((10, 10, 3), 128, dtype=np.uint8)
    # Encode to JPEG
    _, buf = cv2.imencode('.jpg', img)
    # Return base64 string (no data: prefix)
    return base64.b64encode(buf).decode('utf-8')


@pytest.fixture
def client():
    """Fixture: Flask test client with a fresh temporary database."""
    app_module.app.config['TESTING'] = True
    app_module._rate_hits.clear()
    with app_module.app.app_context():
        assert app_module.db.engine.url.database == _TEST_DB  # never the real DB
        app_module.db.drop_all()
        app_module.db.create_all()

    with app_module.app.test_client() as test_client:
        yield test_client


class TestAnalyzeEndpoint:
    """Tests for POST /analyze."""

    def test_analyze_valid_base64_both_fields(self, client):
        """Valid base64 in both fields returns 200 with findings list."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/analyze',
            json={'side_image': b64_img, 'top_image': b64_img},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'findings' in data
        assert isinstance(data['findings'], list)

    def test_analyze_missing_side_image(self, client):
        """Missing side_image field returns 400."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/analyze',
            json={'top_image': b64_img},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_analyze_missing_top_image(self, client):
        """Missing top_image field returns 400."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/analyze',
            json={'side_image': b64_img},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_analyze_invalid_base64_side(self, client):
        """Invalid base64 in side_image returns 400."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/analyze',
            json={'side_image': '!!!notbase64!!!', 'top_image': b64_img},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_analyze_invalid_base64_top(self, client):
        """Invalid base64 in top_image returns 400."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/analyze',
            json={'side_image': b64_img, 'top_image': '!!!notbase64!!!'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_analyze_both_invalid_base64(self, client):
        """Invalid base64 in both fields returns 400."""
        response = client.post(
            '/analyze',
            json={'side_image': '!!!', 'top_image': '!!!'},
            content_type='application/json'
        )
        assert response.status_code == 400


class TestValidatePhotoEndpoint:
    """Tests for POST /validate_photo."""

    @pytest.mark.parametrize('box', [None, [0.2, 0.2, 0.1, 0.9], [0, 0, 2, 1], [False, 0, 1, 1]])
    def test_invalid_nail_box_rejected_by_both_endpoints(self, client, box):
        image = _make_tiny_jpeg()
        assert client.post('/validate_photo', json={'image': image, 'view': 'top', 'top_nail_bbox': box}).status_code == 400
        assert client.post('/analyze', json={'side_image': image, 'top_image': image, 'top_nail_bbox': box}).status_code == 400

    def test_box_coordinates_forwarded_without_recropping_image(self, client, monkeypatch):
        image = _make_tiny_jpeg()
        box = [0.1, 0.2, 0.7, 0.9]
        received = {}
        def analyze(side, top, top_nail_bbox=None):
            received.update(side=side, top=top, box=top_nail_bbox)
            return {'findings': []}
        monkeypatch.setattr(app_module, 'run_analysis', analyze)
        assert client.post('/analyze', json={'side_image': image, 'top_image': image, 'top_nail_bbox': box}).status_code == 200
        assert received == {'side': image, 'top': image, 'box': box}

    def test_validate_photo_top_view_valid(self, client):
        """Valid image + view='top' returns 200 with ok and failure_reason keys."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/validate_photo',
            json={'image': b64_img, 'view': 'top'},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'ok' in data
        assert 'failure_reason' in data
        assert isinstance(data['ok'], bool)

    def test_validate_photo_side_view_valid(self, client):
        """Valid image + view='side' returns 200 with ok and failure_reason keys."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/validate_photo',
            json={'image': b64_img, 'view': 'side'},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'ok' in data
        assert 'failure_reason' in data

    def test_validate_photo_invalid_view(self, client):
        """Invalid view value returns 400."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/validate_photo',
            json={'image': b64_img, 'view': 'invalid'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_validate_photo_missing_image(self, client):
        """Missing image field returns 400."""
        response = client.post(
            '/validate_photo',
            json={'view': 'top'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_validate_photo_missing_view(self, client):
        """Missing view field returns 400."""
        b64_img = _make_tiny_jpeg()
        response = client.post(
            '/validate_photo',
            json={'image': b64_img},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_validate_photo_invalid_base64(self, client):
        """Invalid base64 image returns 400."""
        response = client.post(
            '/validate_photo',
            json={'image': '!!!notbase64!!!', 'view': 'top'},
            content_type='application/json'
        )
        assert response.status_code == 400


class TestFeedbackEndpoint:
    """Tests for POST /feedback."""

    def test_feedback_valid(self, client):
        """Valid feedback returns 200 with ok=True."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'shown_verdict': 'within',
                'agreed': True
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'id' in data

    def test_feedback_with_note(self, client):
        """Valid feedback with note returns 200."""
        response = client.post(
            '/feedback',
            json={
                'label': 'koilonychia',
                'shown_verdict': 'outside',
                'agreed': False,
                'note': 'Test note'
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

    def test_feedback_with_scan_id(self, client):
        """Valid feedback with scan_id returns 200."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'shown_verdict': 'inconclusive',
                'agreed': True,
                'scan_id': 123
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

    def test_feedback_agreed_not_bool(self, client):
        """agreed as string instead of bool returns 400."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'shown_verdict': 'within',
                'agreed': 'yes'
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_feedback_missing_label(self, client):
        """Missing label returns 400."""
        response = client.post(
            '/feedback',
            json={
                'shown_verdict': 'within',
                'agreed': True
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_feedback_missing_shown_verdict(self, client):
        """Missing shown_verdict returns 400."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'agreed': True
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_feedback_missing_agreed(self, client):
        """Missing agreed returns 400."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'shown_verdict': 'within'
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_feedback_invalid_verdict(self, client):
        """Invalid shown_verdict returns 400."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'shown_verdict': 'invalid_verdict',
                'agreed': True
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_feedback_invalid_scan_id(self, client):
        """Non-integer scan_id returns 400."""
        response = client.post(
            '/feedback',
            json={
                'label': 'clubbing',
                'shown_verdict': 'within',
                'agreed': True,
                'scan_id': 'not_an_int'
            },
            content_type='application/json'
        )
        assert response.status_code == 400


class TestHistoryEndpoint:
    """Tests for GET /history."""

    def test_history_empty(self, client):
        """GET /history returns 200 with empty scans list initially."""
        response = client.get('/history')
        assert response.status_code == 200
        data = response.get_json()
        assert 'scans' in data
        assert isinstance(data['scans'], list)
        assert len(data['scans']) == 0

    def test_history_after_analyze(self, client):
        """GET /history returns 200 with scans after /analyze is called."""
        b64_img = _make_tiny_jpeg()
        # Call analyze to create a scan record
        client.post(
            '/analyze',
            json={'side_image': b64_img, 'top_image': b64_img},
            content_type='application/json'
        )

        # Now get history
        response = client.get('/history')
        assert response.status_code == 200
        data = response.get_json()
        assert 'scans' in data
        assert len(data['scans']) >= 1
        # Each scan should have the expected fields
        scan = data['scans'][0]
        assert 'id' in scan
        assert 'created_at' in scan
        assert 'findings' in scan


class TestPerClientHistory:
    """A shared server must show each browser only its own scans."""

    ALICE = {'X-Client-Id': 'alice-browser-0123456789'}
    BOB = {'X-Client-Id': 'bob-browser-9876543210'}

    def _scan(self, client, headers):
        b64_img = _make_tiny_jpeg()
        return client.post('/analyze', json={'side_image': b64_img, 'top_image': b64_img}, headers=headers)

    def test_each_client_sees_only_its_own_scans(self, client):
        self._scan(client, self.ALICE)
        self._scan(client, self.ALICE)
        self._scan(client, self.BOB)
        assert len(client.get('/history', headers=self.ALICE).get_json()['scans']) == 2
        assert len(client.get('/history', headers=self.BOB).get_json()['scans']) == 1
        # a stranger's id sees nothing
        assert client.get('/history', headers={'X-Client-Id': 'stranger-browser-000000'}).get_json()['scans'] == []

    def test_malformed_client_id_is_ignored(self, client):
        self._scan(client, self.ALICE)
        bad = {'X-Client-Id': 'short'}
        # falls back to the legacy "no id" behaviour (all scans) when not required
        assert len(client.get('/history', headers=bad).get_json()['scans']) == 1

    def test_require_client_id_hides_everything_without_one(self, client, monkeypatch):
        self._scan(client, self.ALICE)
        monkeypatch.setattr(app_module, '_REQUIRE_CLIENT_ID', True)
        assert client.get('/history').get_json()['scans'] == []
        assert len(client.get('/history', headers=self.ALICE).get_json()['scans']) == 1
